// WebGPU path tracer: the same cotton + ink material, sweep and softboxes as the Cycles renders.
// One sample per pixel per dispatch, accumulated in a float buffer, shown through Khronos PBR Neutral.

export const TRACE_WGSL = /* wgsl */ `
struct Light { pos: vec3f, cdf: f32, ex: vec3f, area: f32, ey: vec3f, psel: f32, L: vec3f, _p: f32, n: vec3f, _q: f32 };
struct U {
  camPos: vec3f, aperture: f32,
  camR: vec3f, tanHalf: f32,
  camU: vec3f, aspect: f32,
  camF: vec3f, focus: f32,
  crop: vec4f,
  yaw: vec4f,
  world: vec3f, knit: f32,
  paper: vec3f, showPaper: f32,
  fabric: vec3f, grain: f32,
  size: vec4u,
  lights: array<Light, 4>,
};

@group(0) @binding(0) var<uniform> u: U;
@group(0) @binding(1) var<storage, read> nodes: array<vec4f>;
@group(0) @binding(2) var<storage, read> tris: array<vec4f>;
@group(0) @binding(3) var<storage, read> triv: array<vec4u>;
@group(0) @binding(4) var<storage, read> verts: array<vec4f>;
@group(0) @binding(5) var<storage, read_write> accum: array<vec4f>;
@group(0) @binding(6) var samp: sampler;
@group(0) @binding(7) var texColor: texture_2d<f32>;
@group(0) @binding(8) var texOrm: texture_2d<f32>;
@group(0) @binding(9) var texNormal: texture_2d<f32>;
@group(0) @binding(10) var texKnit: texture_2d<f32>;

const PI = 3.14159265359;
const INF = 1e30;
const KNIT_REPEAT = vec2f(175.43859649, 68.46846847);   // atlas 200 x 76 cm over an 11.4 x 11.1 mm loop tile

var<private> seed: u32;
fn pcg(v: u32) -> u32 { let s = v * 747796405u + 2891336453u; let w = ((s >> ((s >> 28u) + 4u)) ^ s) * 277803737u; return (w >> 22u) ^ w; }
fn rnd() -> f32 { seed = pcg(seed); return f32(seed) / 4294967296.0; }

fn rotY(p: vec3f, c: f32, s: f32) -> vec3f { return vec3f(c * p.x + s * p.z, p.y, -s * p.x + c * p.z); }

struct Hit { t: f32, kind: u32, tri: u32, b: vec2f };   // kind 0 none, 1 tee, 2 sweep

fn aabb(ro: vec3f, inv: vec3f, mn: vec3f, mx: vec3f, tmax: f32) -> f32 {
  let t0 = (mn - ro) * inv; let t1 = (mx - ro) * inv;
  let a = min(t0, t1); let b = max(t0, t1);
  let tn = max(max(a.x, a.y), max(a.z, 0.0)); let tf = min(min(b.x, b.y), min(b.z, tmax));
  return select(INF, tn, tn <= tf);
}

// tee in object space (the turntable turns the tee, not the studio)
fn traceTee(ro: vec3f, rd: vec3f, tmaxIn: f32, any: bool) -> Hit {
  var h = Hit(tmaxIn, 0u, 0u, vec2f(0.0));
  let inv = 1.0 / rd;
  var stack: array<u32, 48>; var sp = 0u; var node = 0u;
  loop {
    let a = nodes[node * 2u]; let b = nodes[node * 2u + 1u];
    let count = bitcast<u32>(b.w);
    if (count > 0u) {
      let first = bitcast<u32>(a.w);
      for (var i = first; i < first + count; i++) {
        let v0 = tris[i * 3u].xyz; let e1 = tris[i * 3u + 1u].xyz; let e2 = tris[i * 3u + 2u].xyz;
        let pv = cross(rd, e2); let det = dot(e1, pv);
        if (abs(det) < 1e-12) { continue; }
        let id = 1.0 / det; let tv = ro - v0; let bu = dot(tv, pv) * id;
        if (bu < 0.0 || bu > 1.0) { continue; }
        let qv = cross(tv, e1); let bv = dot(rd, qv) * id;
        if (bv < 0.0 || bu + bv > 1.0) { continue; }
        let t = dot(e2, qv) * id;
        if (t > 1e-5 && t < h.t) { h = Hit(t, 1u, i, vec2f(bu, bv)); if (any) { return h; } }
      }
      if (sp == 0u) { break; }
      sp--; node = stack[sp]; continue;
    }
    let l = bitcast<u32>(a.w); let r = l + 1u;
    let dl = aabb(ro, inv, nodes[l * 2u].xyz, nodes[l * 2u + 1u].xyz, h.t);
    let dr = aabb(ro, inv, nodes[r * 2u].xyz, nodes[r * 2u + 1u].xyz, h.t);
    if (dl < INF && dr < INF) {
      if (dl <= dr) { stack[sp] = r; node = l; } else { stack[sp] = l; node = r; }
      sp++;
    } else if (dl < INF) { node = l; } else if (dr < INF) { node = r; }
    else { if (sp == 0u) { break; } sp--; node = stack[sp]; }
  }
  return h;
}

// seamless paper sweep: floor, quarter-cylinder cove, wall (analytic, so it is perfectly smooth)
const FLOOR_Y = 0.35; const COVE_Y = 0.95; const COVE_Z = -0.9; const COVE_R = 0.6; const WALL_Z = -1.5;
fn traceSweep(ro: vec3f, rd: vec3f, tmax: f32) -> f32 {
  var best = tmax;
  if (abs(rd.y) > 1e-8) {
    let t = (FLOOR_Y - ro.y) / rd.y; let p = ro + rd * t;
    if (t > 1e-4 && t < best && p.z >= COVE_Z && p.z < 5.4 && abs(p.x) < 6.0) { best = t; }
  }
  if (abs(rd.z) > 1e-8) {
    let t = (WALL_Z - ro.z) / rd.z; let p = ro + rd * t;
    if (t > 1e-4 && t < best && p.y >= COVE_Y && p.y < 4.35 && abs(p.x) < 6.0) { best = t; }
  }
  // cylinder along x: (y - COVE_Y)^2 + (z - COVE_Z)^2 = R^2, inside quadrant y < COVE_Y, z < COVE_Z
  let oy = ro.y - COVE_Y; let oz = ro.z - COVE_Z;
  let A = rd.y * rd.y + rd.z * rd.z; let B = oy * rd.y + oz * rd.z; let C = oy * oy + oz * oz - COVE_R * COVE_R;
  let D = B * B - A * C;
  if (A > 1e-10 && D > 0.0) {
    let sq = sqrt(D);
    for (var k = 0; k < 2; k++) {
      let t = select((-B + sq) / A, (-B - sq) / A, k == 0);
      let p = ro + rd * t;
      if (t > 1e-4 && t < best && p.y <= COVE_Y && p.z <= COVE_Z && abs(p.x) < 6.0) { best = t; }
    }
  }
  return best;
}
fn sweepNormal(p: vec3f) -> vec3f {
  if (p.z > COVE_Z + 1e-3) { return vec3f(0.0, 1.0, 0.0); }
  if (p.y > COVE_Y - 1e-3) { return vec3f(0.0, 0.0, 1.0); }
  return normalize(vec3f(0.0, COVE_Y - p.y, COVE_Z - p.z));
}

fn trace(ro: vec3f, rd: vec3f, tmax: f32, any: bool) -> Hit {
  let c = u.yaw.x; let s = u.yaw.y;
  // world -> object: rotate by -yaw
  var h = traceTee(rotY(ro, c, -s), rotY(rd, c, -s), tmax, any);
  if (any && h.kind == 1u) { return h; }
  if (u.showPaper > 0.5) {
    let ts = traceSweep(ro, rd, h.t);
    if (ts < h.t) { h = Hit(ts, 2u, 0u, vec2f(0.0)); }
  }
  return h;
}

// ---------- material ----------
struct Surf { p: vec3f, n: vec3f, ng: vec3f, base: vec3f, rough: f32, sheen: f32, spec: f32 };

fn hash3(p: vec3f) -> f32 { let q = fract(p * vec3f(0.1031, 0.1030, 0.0973)); let r = q + dot(q, q.yxz + 33.33); return fract((r.x + r.y) * r.z); }
fn vnoise(x: vec3f) -> f32 {
  let i = floor(x); let f = fract(x); let w = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(hash3(i), hash3(i + vec3f(1, 0, 0)), w.x), mix(hash3(i + vec3f(0, 1, 0)), hash3(i + vec3f(1, 1, 0)), w.x), w.y),
             mix(mix(hash3(i + vec3f(0, 0, 1)), hash3(i + vec3f(1, 0, 1)), w.x), mix(hash3(i + vec3f(0, 1, 1)), hash3(i + vec3f(1, 1, 1)), w.x), w.y), w.z);
}

fn teeSurf(h: Hit, ro: vec3f, rd: vec3f) -> Surf {
  let c = u.yaw.x; let s = u.yaw.y;
  let iv = triv[h.tri];
  let e1 = tris[h.tri * 3u + 1u].xyz; let e2 = tris[h.tri * 3u + 2u].xyz;
  let w = 1.0 - h.b.x - h.b.y;
  let a0 = verts[iv.x * 2u]; let a1 = verts[iv.y * 2u]; let a2 = verts[iv.z * 2u];
  let c0 = verts[iv.x * 2u + 1u].x; let c1 = verts[iv.y * 2u + 1u].x; let c2 = verts[iv.z * 2u + 1u].x;
  let uv0 = vec2f(a0.w, c0); let uv1 = vec2f(a1.w, c1); let uv2 = vec2f(a2.w, c2);
  let uv = uv0 * w + uv1 * h.b.x + uv2 * h.b.y;
  var ng = normalize(cross(e1, e2));
  var n = normalize(a0.xyz * w + a1.xyz * h.b.x + a2.xyz * h.b.y);
  let rdo = rotY(rd, c, -s);
  if (dot(ng, rdo) > 0.0) { ng = -ng; }
  if (dot(n, ng) < 0.0) { n = -n; }
  var S: Surf;
  S.p = ro + rd * h.t;
  let pObj = rotY(S.p, c, -s);
  if (iv.w == 0u) {
    // tangent frame from the UVs, the same way three builds it (T = dP/du, B = dP/dv)
    let d1 = uv1 - uv0; let d2 = uv2 - uv0;
    let r = 1.0 / (d1.x * d2.y - d1.y * d2.x + 1e-20);
    var T = (e1 * d2.y - e2 * d1.y) * r; var B = (e2 * d1.x - e1 * d2.x) * r;
    T = normalize(T - n * dot(n, T)); B = normalize(B - n * dot(n, B) - T * dot(T, B));
    var mn = textureSampleLevel(texNormal, samp, uv, 0.0).xyz * 2.0 - 1.0;
    var kn = textureSampleLevel(texKnit, samp, uv * KNIT_REPEAT, 0.0).xyz * 2.0 - 1.0;
    kn = vec3f(kn.xy * u.knit, kn.z);
    mn = normalize(vec3f(mn.xy + kn.xy, mn.z * kn.z));
    let np = normalize(T * mn.x + B * mn.y + n * mn.z);
    n = select(n, np, dot(np, ng) > 0.02);
    let orm = textureSampleLevel(texOrm, samp, uv, 0.0);
    let g = mix(0.93, 1.06, vnoise(pObj * 900.0)) * u.grain + (1.0 - u.grain);
    S.base = textureSampleLevel(texColor, samp, uv, 0.0).rgb * g;
    S.rough = orm.g; S.sheen = 0.35 * (1.0 - orm.b); S.spec = 0.02;
  } else {
    S.base = u.fabric; S.rough = 0.95; S.sheen = 0.35; S.spec = 0.02;
  }
  S.n = rotY(n, c, s); S.ng = rotY(ng, c, s);
  return S;
}

fn sweepSurf(h: Hit, ro: vec3f, rd: vec3f) -> Surf {
  var S: Surf; S.p = ro + rd * h.t; S.n = sweepNormal(S.p); S.ng = S.n;
  S.base = u.paper; S.rough = 0.95; S.sheen = 0.0; S.spec = 0.02;
  return S;
}

fn ggxD(nh: f32, a: f32) -> f32 { let a2 = a * a; let d = nh * nh * (a2 - 1.0) + 1.0; return a2 / (PI * d * d); }
fn smithG1(nx: f32, a: f32) -> f32 { let a2 = a * a; return 2.0 * nx / (nx + sqrt(a2 + (1.0 - a2) * nx * nx)); }

// Principled-style: diffuse + dielectric GGX (F0 from IOR 1.5 at specular level 0.25) + cotton sheen layer
fn bsdf(S: Surf, wo: vec3f, wi: vec3f) -> vec3f {
  let nl = dot(S.n, wi); let nv = dot(S.n, wo);
  if (nl <= 0.0 || nv <= 0.0 || dot(S.ng, wi) <= 0.0) { return vec3f(0.0); }
  let hv = normalize(wo + wi); let nh = max(dot(S.n, hv), 0.0); let vh = max(dot(wo, hv), 0.0);
  let F = S.spec + (1.0 - S.spec) * pow(1.0 - vh, 5.0);
  let a = max(S.rough * S.rough, 0.002);
  let spec = ggxD(nh, a) * smithG1(nl, a) * smithG1(nv, a) * F / (4.0 * nl * nv);
  let diff = S.base * (1.0 - S.spec) / PI;
  // Charlie sheen, roughness 0.3, Neubelt visibility
  let ia = 1.0 / 0.3; let sh = sqrt(max(1.0 - nh * nh, 0.0));
  let Dc = (2.0 + ia) * pow(sh, ia) / (2.0 * PI);
  let Vc = 1.0 / (4.0 * (nl + nv - nl * nv));
  let k = u.crop.w;   // sheen strength, fitted to Cycles' microfiber sheen
  let sheen = S.sheen * k * Dc * Vc;
  return (diff + vec3f(spec)) * (1.0 - S.sheen * k * 0.3) + vec3f(sheen);
}

fn onb(n: vec3f) -> mat3x3f {
  let s = select(-1.0, 1.0, n.z >= 0.0); let a = -1.0 / (s + n.z); let b = n.x * n.y * a;
  return mat3x3f(vec3f(1.0 + s * n.x * n.x * a, s * b, -s * n.x), vec3f(b, s + n.y * n.y * a, -n.y), n);
}

struct Bounce { wi: vec3f, w: vec3f, ok: bool };
fn sampleBsdf(S: Surf, wo: vec3f) -> Bounce {
  let pSpec = select(0.0, 0.12, S.sheen > 0.0 || S.rough < 0.9);
  let M = onb(S.n);
  var wi: vec3f;
  let a = max(S.rough * S.rough, 0.002);
  if (rnd() < pSpec) {
    let u1 = rnd(); let u2 = rnd();
    let ct = sqrt((1.0 - u1) / (1.0 + (a * a - 1.0) * u1)); let st = sqrt(1.0 - ct * ct); let ph = 2.0 * PI * u2;
    let hv = M * vec3f(st * cos(ph), st * sin(ph), ct);
    wi = reflect(-wo, hv);
  } else {
    let u1 = rnd(); let u2 = rnd(); let r = sqrt(u1); let ph = 2.0 * PI * u2;
    wi = M * vec3f(r * cos(ph), r * sin(ph), sqrt(max(0.0, 1.0 - u1)));
  }
  let nl = dot(S.n, wi);
  if (nl <= 0.0 || dot(S.ng, wi) <= 0.0) { return Bounce(wi, vec3f(0.0), false); }
  let hv = normalize(wo + wi); let nh = max(dot(S.n, hv), 0.0); let vh = max(dot(wo, hv), 1e-4);
  let pdf = (1.0 - pSpec) * nl / PI + pSpec * ggxD(nh, a) * nh / (4.0 * vh);
  return Bounce(wi, bsdf(S, wo, wi) * nl / max(pdf, 1e-6), true);
}

fn directLight(S: Surf, wo: vec3f) -> vec3f {
  let n = u.size.w; if (n == 0u) { return vec3f(0.0); }
  let x = rnd(); var k = 0u;
  for (var i = 0u; i < n; i++) { if (x <= u.lights[i].cdf) { k = i; break; } k = i; }
  let l = u.lights[k];
  let p = l.pos + l.ex * (2.0 * rnd() - 1.0) + l.ey * (2.0 * rnd() - 1.0);
  let d = p - S.p; let dist2 = dot(d, d); let dist = sqrt(dist2); let wi = d / dist;
  let cl = dot(l.n, -wi); if (cl <= 0.0) { return vec3f(0.0); }
  let f = bsdf(S, wo, wi); if (f.x + f.y + f.z <= 0.0) { return vec3f(0.0); }
  let o = S.p + S.ng * 2e-4;
  let sh = trace(o, wi, dist - 1e-3, true);
  if (sh.kind != 0u) { return vec3f(0.0); }
  return f * dot(S.n, wi) * l.L * cl * l.area / (dist2 * l.psel);
}

@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) gid: vec3u) {
  let W = u.size.x; let H = u.size.y;
  if (gid.x >= W || gid.y >= H) { return; }
  let pix = gid.y * W + gid.x;
  seed = pcg(pix ^ pcg(u.size.z * 9781u + 17u));
  // tent-filtered sub-pixel jitter (close to Cycles' 1.5 px Blackman-Harris)
  let j = vec2f(rnd(), rnd()) * 2.0 - 1.0;
  let jt = sign(j) * (1.0 - sqrt(1.0 - abs(j))) * 0.75 + 0.5;
  let ndc = vec2f((f32(gid.x) + jt.x) / f32(W) * 2.0 - 1.0, 1.0 - (f32(gid.y) + jt.y) / f32(H) * 2.0);
  let q = u.crop.xy + ndc / u.crop.z;
  var dir = normalize(u.camF + u.camR * q.x * u.tanHalf * u.aspect + u.camU * q.y * u.tanHalf);
  // thin lens: f/5.6 focused on the tee
  let fp = u.camPos + dir * (u.focus / dot(dir, u.camF));
  let lr = sqrt(rnd()) * u.aperture; let la = 2.0 * PI * rnd();
  var ro = u.camPos + u.camR * (lr * cos(la)) + u.camU * (lr * sin(la));
  var rd = normalize(fp - ro);
  var L = vec3f(0.0); var tp = vec3f(1.0);
  for (var bounce = 0; bounce < 6; bounce++) {
    let h = trace(ro, rd, INF, false);
    if (h.kind == 0u) { L += tp * u.world; break; }
    var S: Surf;
    if (h.kind == 1u) { S = teeSurf(h, ro, rd); } else { S = sweepSurf(h, ro, rd); }
    let wo = -rd;
    L += tp * directLight(S, wo);
    let b = sampleBsdf(S, wo);
    if (!b.ok) { break; }
    tp *= b.w;
    if (bounce >= 2) { let pr = clamp(max(tp.x, max(tp.y, tp.z)), 0.05, 0.95); if (rnd() > pr) { break; } tp /= pr; }
    ro = S.p + S.ng * 2e-4; rd = b.wi;
  }
  L = min(L, vec3f(20.0));   // firefly clamp
  let prev = select(vec4f(0.0), accum[pix], u.size.z > 0u);
  accum[pix] = prev + vec4f(L, 1.0);
}
`;

export const SHOW_WGSL = /* wgsl */ `
@group(0) @binding(0) var<storage, read> accum: array<vec4f>;
@group(0) @binding(1) var<uniform> dims: vec4u;   // w, h

@vertex fn vs(@builtin(vertex_index) i: u32) -> @builtin(position) vec4f {
  let p = array<vec2f, 3>(vec2f(-1.0, -1.0), vec2f(3.0, -1.0), vec2f(-1.0, 3.0));
  return vec4f(p[i], 0.0, 1.0);
}

// Khronos PBR Neutral, the view transform the Cycles stills use
fn neutral(c0: vec3f) -> vec3f {
  var c = c0;
  let start = 0.8 - 0.04; let desat = 0.15;
  let x = min(c.r, min(c.g, c.b));
  let off = select(0.04, x - 6.25 * x * x, x < 0.08);
  c -= off;
  let peak = max(c.r, max(c.g, c.b));
  if (peak < start) { return c; }
  let d = 1.0 - start; let np = 1.0 - d * d / (peak + d - start);
  c *= np / peak;
  let g = 1.0 - 1.0 / (desat * (peak - np) + 1.0);
  return mix(c, vec3f(np), g);
}
fn srgb(c: vec3f) -> vec3f { return select(1.055 * pow(c, vec3f(1.0 / 2.4)) - 0.055, c * 12.92, c <= vec3f(0.0031308)); }

@fragment fn fs(@builtin(position) pos: vec4f) -> @location(0) vec4f {
  let x = min(u32(pos.x), dims.x - 1u); let y = min(u32(pos.y), dims.y - 1u);
  let a = accum[y * dims.x + x];
  let c = a.rgb / max(a.w, 1.0);
  return vec4f(srgb(clamp(neutral(max(c, vec3f(0.0))), vec3f(0.0), vec3f(1.0))), 1.0);
}
`;
