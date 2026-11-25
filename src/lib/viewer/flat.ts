// On the table: the tee laid flat on a worn table, shot from straight above, a window's light raking across the cotton.
// The tee is the pattern itself (pipeline/pattern.py, size M): the panel on top shows its print, the other panel
// lies under it (seen through the neck), both cut by their real outline. Every time the view is entered the cotton
// settles differently: new soft creases, a new fold or two from the bag, air caught under it. Nothing moves but
// the loose edges (hem, sleeve openings), lifting a few millimetres when the air in the room moves.
import * as THREE from "three/webgpu";
import {
  texture, vec2, vec3, vec4, float, normalMap, normalize, uniform, attribute, positionLocal, normalLocal, modelViewMatrix,
  varying, smoothstep, sin, cos,
} from "three/tsl";
import { asset } from "@/lib/asset";
import { picture } from "./pic";
import { Air, Wind } from "./air";

/** what the tee's own material is made of, shared so the flat tee is the same cotton and ink */
export type LookNodes = {
  color: THREE.Node<"vec3">; rough: THREE.Node<"float">; sheen: THREE.Node<"vec3">;
  /** the cloth relief (construction + jersey), a tangent-space normal in -1..1 */
  relief: THREE.Node<"vec3">;
  fabric: THREE.Node<"color">;
};
type V4 = ReturnType<typeof vec4>;
/** one channel of a texture node read at another place (it follows the node's texture when that is swapped) */
const at = (n: ReturnType<typeof texture>, p: THREE.Node<"vec2">) => (n.sample(p) as unknown as V4).x;
export type Side = "back" | "front";

// ---------- the pattern (pipeline/pattern.py, size M), in cm: x across from the centre, y up from the hem ----------
const L = 73.66, HC = 27.94, HS = 25.4, NECK_W = 9.8, SLOPE = 3.2, ARMHOLE = 25, SLEEVE_LEN = 22, SLEEVE_OPEN = 20, SLEEVE_ANG = 15;
const DROP: Record<Side, number> = { front: 9.5, back: 2.5 };
// a panel's cell in the texture atlas: 110 x 86 cm, the high shoulder point 82 cm up it. Panel-local cm: X across
// (as seen from the side facing up), Y up, centred on the cell: Y = y - L + 39.
const PW = 110, PH = 86, Y0 = 39 - L;
const HEM_Y = Y0;
const keyPoints = () => {
  const sp: [number, number] = [HS, L - SLOPE];
  const a = (-SLEEVE_ANG * Math.PI) / 180 - Math.atan2(SLOPE, HS - NECK_W);
  const st: [number, number] = [sp[0] + SLEEVE_LEN * Math.cos(a), sp[1] + SLEEVE_LEN * Math.sin(a)];
  const sb: [number, number] = [st[0] + SLEEVE_OPEN * Math.sin(a), st[1] - SLEEVE_OPEN * Math.cos(a)];
  const ua: [number, number] = [HC, sp[1] - ARMHOLE];
  return { sp, st, sb, ua, a };
};
const KP = keyPoints();
/** the panel's outline (closed polygon) in panel-local cm */
function outline(side: Side): [number, number][] {
  const drop = DROP[side], { sp, st, sb, ua } = KP, half: [number, number][] = [];
  const seg = (a: [number, number], b: [number, number]) => {
    const n = Math.max(1, Math.round(Math.hypot(b[0] - a[0], b[1] - a[1])));
    for (let k = 0; k < n; k++) half.push([a[0] + ((b[0] - a[0]) * k) / n, a[1] + ((b[1] - a[1]) * k) / n]);
  };
  for (let k = 0, n = 24; k < n; k++) { const t = (k / n) * (Math.PI / 2); half.push([NECK_W * Math.sin(t), L - drop * Math.cos(t)]); }
  seg([NECK_W, L], sp); seg(sp, st); seg(st, sb); seg(sb, [ua[0] + 3, ua[1]]);
  for (let k = 0; k < 6; k++) { const t = Math.PI / 2 + ((Math.PI / 2) * k) / 6; half.push([ua[0] + 3 + 3 * Math.cos(t), ua[1] - 3 + 3 * Math.sin(t)]); }
  seg([ua[0], ua[1] - 3], [HC, 0]); seg([HC, 0], [0, 0]);
  const right = half.map(([x, y]) => [x, y + Y0] as [number, number]);
  const left = right.slice(1).reverse().map(([x, y]) => [-x, y] as [number, number]);
  return [...right, ...left];
}

// ---------- the outline as a signed distance (cm, negative inside), 3 texels a cm: sharp edges at any zoom ----------
const SD_K = 3, SD_W = PW * SD_K, SD_H = PH * SD_K, SD_MAX = 6;
type Sdf = { d: Float32Array; tex: THREE.DataTexture };
const sdfs: Partial<Record<Side, Sdf>> = {};
function sdf(side: Side): Sdf {
  const got = sdfs[side]; if (got) return got;
  const P = outline(side), n = P.length, d = new Float32Array(SD_W * SD_H);
  // distance: past SD_MAX it's clamped anyway, so each edge only visits the texels within SD_MAX of it
  const best = new Float64Array(SD_W * SD_H).fill(SD_MAX * SD_MAX);
  const ix = (x: number) => (x + PW / 2) * SD_K - 0.5, iy = (y: number) => (y + PH / 2) * SD_K - 0.5;
  for (let k = 0, m = n - 1; k < n; m = k++) {
    const [ax, ay] = P[m], [bx, by] = P[k], ex = bx - ax, ey = by - ay, ll = ex * ex + ey * ey || 1;
    const i0 = Math.max(0, Math.floor(ix(Math.min(ax, bx) - SD_MAX))), i1 = Math.min(SD_W - 1, Math.ceil(ix(Math.max(ax, bx) + SD_MAX)));
    const j0 = Math.max(0, Math.floor(iy(Math.min(ay, by) - SD_MAX))), j1 = Math.min(SD_H - 1, Math.ceil(iy(Math.max(ay, by) + SD_MAX)));
    for (let j = j0; j <= j1; j++) {
      const y = -PH / 2 + (j + 0.5) / SD_K;
      for (let i = i0; i <= i1; i++) {
        const x = -PW / 2 + (i + 0.5) / SD_K, t = Math.max(0, Math.min(1, ((x - ax) * ex + (y - ay) * ey) / ll));
        const dx = x - ax - t * ex, dy = y - ay - t * ey, q = dx * dx + dy * dy;
        if (q < best[j * SD_W + i]) best[j * SD_W + i] = q;
      }
    }
  }
  // inside: the same crossing test, worked out once per row (where each edge crosses it)
  const xs: number[] = [];
  for (let j = 0; j < SD_H; j++) {
    const y = -PH / 2 + (j + 0.5) / SD_K;
    xs.length = 0;
    for (let k = 0, m = n - 1; k < n; m = k++) {
      const [ax, ay] = P[m], [bx, by] = P[k];
      if ((ay > y) !== (by > y)) xs.push(((bx - ax) * (y - ay)) / (by - ay) + ax);
    }
    for (let i = 0; i < SD_W; i++) {
      const x = -PW / 2 + (i + 0.5) / SD_K;
      let inside = false;
      for (const c of xs) if (x < c) inside = !inside;
      d[j * SD_W + i] = Math.min(SD_MAX, Math.sqrt(best[j * SD_W + i])) * (inside ? -1 : 1);
    }
  }
  const half = new Uint16Array(d.length);
  for (let i = 0; i < d.length; i++) half[i] = THREE.DataUtils.toHalfFloat(d[i]);
  const tex = new THREE.DataTexture(half, SD_W, SD_H, THREE.RedFormat, THREE.HalfFloatType);
  tex.minFilter = tex.magFilter = THREE.LinearFilter; tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
  tex.generateMipmaps = false; tex.needsUpdate = true;
  return (sdfs[side] = { d, tex });
}
/** the signed distance at a panel-local point, bilinear (as the GPU samples it) */
function sdAt(s: Sdf, x: number, y: number) {
  const fx = Math.min(SD_W - 1.001, Math.max(0, (x + PW / 2) * SD_K - 0.5)), fy = Math.min(SD_H - 1.001, Math.max(0, (y + PH / 2) * SD_K - 0.5));
  const i = Math.floor(fx), j = Math.floor(fy), u = fx - i, v = fy - j, D = s.d, o = j * SD_W + i;
  return (D[o] * (1 - u) + D[o + 1] * u) * (1 - v) + (D[o + SD_W] * (1 - u) + D[o + SD_W + 1] * u) * v;
}

// ---------- how the cotton settles: soft ridges, folds from the bag, air caught under it ----------
function rng(seed: number) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
type Ridge = { pts: [number, number][]; w: number; a: number; sharp: boolean };
function settle(seed: number) {
  const r = rng(seed), R = (lo: number, hi: number) => lo + (hi - lo) * r(), deg = Math.PI / 180;
  const gauss = () => (r() + r() + r() - 1.5) / 0.5;
  const ridges: Ridge[] = [];
  const curve = (cx: number, cy: number, ang: number, len: number, w: number, a: number, sharp = false) => {
    const dx = Math.cos(ang) * len / 2, dy = Math.sin(ang) * len / 2, sag = R(-0.18, 0.18) * len;
    const p0 = [cx - dx, cy - dy], p2 = [cx + dx, cy + dy], p1 = [cx - Math.sin(ang) * sag, cy + Math.cos(ang) * sag];
    const pts: [number, number][] = [];
    for (let k = 0; k <= 8; k++) {
      const t = k / 8, s = 1 - t;
      pts.push([s * s * p0[0] + 2 * s * t * p1[0] + t * t * p2[0], s * s * p0[1] + 2 * s * t * p1[1] + t * t * p2[1]]);
    }
    ridges.push({ pts, w, a, sharp });
  };
  const n = Math.round(R(18, 27));
  for (let i = 0; i < n; i++) {
    const kind = r();
    if (kind < 0.5) {
      // across the body, mostly sideways: how a tee relaxes when it's laid down and smoothed by hand
      curve(R(-24, 24), R(HEM_Y + 3, 30), gauss() * 20 * deg, R(10, 34), R(0.7, 1.9), R(0.2, 0.55));
    } else if (kind < 0.72) {
      // from an underarm in towards the middle and down, where the side seam pulls
      const s = r() < 0.5 ? -1 : 1, len = R(10, 26), ang = s > 0 ? Math.PI + R(15, 45) * deg : -R(15, 45) * deg;
      const sx = s * R(HC - 6, HC - 1), sy = KP.ua[1] + Y0 - R(1, 8);
      curve(sx + (Math.cos(ang) * len) / 2, sy + (Math.sin(ang) * len) / 2, ang, len, R(0.6, 1.5), R(0.2, 0.5));
    } else if (kind < 0.9) {
      // on a sleeve: along it, or across
      const s = r() < 0.5 ? -1 : 1, t = R(0.2, 0.8);
      const cx = s * (KP.sp[0] + (KP.st[0] - KP.sp[0]) * t + R(-4, 2)), cy = KP.sp[1] + Y0 + (KP.st[1] - KP.sp[1]) * t - R(3, 12);
      const along = r() < 0.6, base = s > 0 ? KP.a : Math.PI - KP.a;
      curve(cx, cy, base + (along ? R(-12, 12) : 90 + R(-20, 20)) * deg, R(6, 15), R(0.5, 1.3), R(0.15, 0.4));
    } else {
      // little gathers at the hem
      curve(R(-24, 24), HEM_Y + R(2, 8), (90 + R(-25, 25)) * deg, R(4, 9), R(0.45, 0.9), R(0.1, 0.25));
    }
  }
  // folds from the bag: once across, sometimes in thirds down the length; pressed, so sharp but low
  if (r() < 0.65) curve(R(-3, 3), R(-14, 10), R(-2, 2) * deg, 66, 0.35, R(0.1, 0.18), true);
  if (r() < 0.45) { const x = R(12, 16); curve(-x, 1, (90 + R(-1.5, 1.5)) * deg, 80, 0.3, R(0.07, 0.13), true); curve(x, 1, (90 + R(-1.5, 1.5)) * deg, 80, 0.3, R(0.07, 0.13), true); }
  // air caught under it
  const swells = Array.from({ length: Math.round(R(5, 9)) }, () => ({ x: R(-30, 30), y: R(HEM_Y, 34), s: R(5, 13), a: R(0.15, 0.5) }));
  return { ridges, swells, tilt: R(-1.8, 1.8) * deg, table: [R(-0.4, 0.4), R(-0.4, 0.4)] as [number, number] };
}
function heights(X: Float32Array, Y: Float32Array, nx: number, h: number, x0: number, y0: number, st: ReturnType<typeof settle>, ridgesOn: boolean) {
  const H = new Float32Array(X.length), ny = X.length / nx;
  for (const s of st.swells) for (let k = 0; k < X.length; k++) { const dx = X[k] - s.x, dy = Y[k] - s.y; H[k] += s.a * Math.exp(-(dx * dx + dy * dy) / (s.s * s.s)); }
  if (!ridgesOn) return H;
  for (const c of st.ridges) {
    let lx = 1e9, hx = -1e9, ly = 1e9, hy = -1e9;
    for (const [x, y] of c.pts) { lx = Math.min(lx, x); hx = Math.max(hx, x); ly = Math.min(ly, y); hy = Math.max(hy, y); }
    const pad = c.w * (c.sharp ? 6 : 3);
    const i0 = Math.max(0, Math.floor((lx - pad - x0) / h)), i1 = Math.min(nx - 1, Math.ceil((hx + pad - x0) / h));
    const j0 = Math.max(0, Math.floor((ly - pad - y0) / h)), j1 = Math.min(ny - 1, Math.ceil((hy + pad - y0) / h));
    const segs = c.pts.length - 1;
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const k = j * nx + i, x = X[k], y = Y[k];
      let best = 1e9, bt = 0;
      for (let q = 0; q < segs; q++) {
        const [ax, ay] = c.pts[q], [bx, by] = c.pts[q + 1], ex = bx - ax, ey = by - ay;
        const t = Math.max(0, Math.min(1, ((x - ax) * ex + (y - ay) * ey) / (ex * ex + ey * ey)));
        const dx = x - ax - t * ex, dy = y - ay - t * ey, dd = dx * dx + dy * dy;
        if (dd < best) { best = dd; bt = (q + t) / segs; }
      }
      const d = Math.sqrt(best) / c.w;
      const taper = Math.pow(Math.max(0, Math.sin(Math.PI * bt)), c.sharp ? 0.25 : 0.8);
      H[k] += c.a * taper * (c.sharp ? Math.exp(-d) : Math.exp(-d * d));
    }
  }
  return H;
}
/** how loose a point is: 1 right at the hem or a sleeve opening, falling to 0 a few cm in (and its slope) */
function loose(x: number, y: number) {
  const hem = Math.abs(x) < HC + 0.5 ? 1 - smooth(0, 7, y - HEM_Y) : 0;
  const ax = Math.abs(x), { st, sb } = KP, sy = st[1] + Y0, by = sb[1] + Y0;
  const ex = sb[0] - st[0], ey = by - sy, t = Math.max(0, Math.min(1, ((ax - st[0]) * ex + (y - sy) * ey) / (ex * ex + ey * ey)));
  const sl = 1 - smooth(0, 6, Math.hypot(ax - st[0] - t * ex, y - sy - t * ey));
  const f = Math.max(hem, sl);
  return f * f;
}
const fixed = new Map<string, { U: Float32Array; PL: Float32Array; FL: Float32Array }>();
/** where each point of a panel is on the print and the panel, and how loose it is: fixed for a panel, worked out once */
function fixedOf(s: Sdf, h: number, c: number, mirror: boolean, withLoose: boolean) {
  const fk = `${s.tex.id}|${h}|${c}|${mirror}|${withLoose}`;
  let F = fixed.get(fk);
  if (!F) {
    const g = grid(s, h), n = g.X.length;
    const U = new Float32Array(n * 2), PL = new Float32Array(n * 2), FL = new Float32Array(n * 3);
    for (let k = 0; k < n; k++) {
      const x = g.X[k], y = g.Y[k];
      U[2 * k] = c + ((mirror ? -x : x) / PW) * 0.5; U[2 * k + 1] = 0.5 - y / PH;
      PL[2 * k] = (x + PW / 2) / PW; PL[2 * k + 1] = (y + PH / 2) / PH;
      if (withLoose) { const f = loose(x, y), e = 0.25; FL[3 * k] = f; FL[3 * k + 1] = (loose(x + e, y) - loose(x - e, y)) / (2 * e); FL[3 * k + 2] = (loose(x, y + e) - loose(x, y - e)) / (2 * e); }
    }
    fixed.set(fk, (F = { U, PL, FL }));
  }
  return F;
}
const smooth = (a: number, b: number, x: number) => { const t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

/** a panel as a grid (cm spacing h), only the cells near its outline kept; the same every time, so made once */
const grids = new Map<string, ReturnType<typeof makeGrid>>();
function grid(s: Sdf, h: number) {
  const k = `${s.tex.id}|${h}`;
  let g = grids.get(k); if (!g) grids.set(k, (g = makeGrid(s, h)));
  return g;
}
function makeGrid(s: Sdf, h: number) {
  const nx = Math.round(PW / h) + 1, ny = Math.round(PH / h) + 1, x0 = -PW / 2, y0 = -PH / 2;
  const X = new Float32Array(nx * ny), Y = new Float32Array(nx * ny), D = new Float32Array(nx * ny);
  for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) { const k = j * nx + i; X[k] = x0 + i * h; Y[k] = y0 + j * h; D[k] = sdAt(s, X[k], Y[k]); }
  const idx: number[] = [];
  for (let j = 0; j < ny - 1; j++) for (let i = 0; i < nx - 1; i++) {
    const a = j * nx + i, b = a + 1, c = a + nx, d = c + 1;
    if (Math.min(D[a], D[b], D[c], D[d]) > h * 0.75) continue;
    idx.push(a, b, d, a, d, c);
  }
  return { nx, ny, x0, y0, h, X, Y, D, idx: Uint32Array.from(idx) };
}

/** the panels' mesh spacing, cm */
const GRID_H = 0.5;
const TABLE = 4;            // m: the table runs well past any frame
/** the table's distance from the lens, against the form's (Viewer's spots are framed for it) */
export const FAR = 1.25;
const WOOD_CM = 180;        // the scan covers 1.8 m
const IN_SIDE: V2 = [0.74, 0.36];    // the window: to the right (the air comes in through it too), a little ahead
const IN_UP = 0.42;                  // and low: the light rakes across the cotton at about 25 degrees
type V2 = [number, number];

/** the window's light as it falls: the opening's soft-edged patch, crossed by the soft shadows of its frame's bars
 *  (soft because the sky behind them is wide); the frame lands toward the edges of the view, clear of the print */
function windowLight() {
  const N = 256, d = new Uint8Array(N * N * 4);
  const ss = (a: number, b: number, x: number) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
    const u = (i + 0.5) / N, v = (j + 0.5) / N;
    const open = ss(0.06, 0.16, u) * ss(0.94, 0.84, u) * ss(0.04, 0.14, v) * ss(0.96, 0.86, v);
    const bar = (x: number, c: number, w: number) => 1 - 0.5 * Math.exp(-(((x - c) / w) ** 2));
    // (and a little brighter toward the window, falling off across the room)
    const near = 0.86 + 0.28 * Math.min(1, Math.max(0, (u - 0.4) / 0.2));
    const k = Math.min(1, open * near * bar(u, 0.578, 0.011) * bar(v, 0.686, 0.011));
    const o = 4 * (j * N + i), c = Math.round(255 * k);
    d[o] = c; d[o + 1] = c; d[o + 2] = c; d[o + 3] = 255;
  }
  const t = new THREE.DataTexture(d, N, N, THREE.RGBAFormat);
  t.magFilter = THREE.LinearFilter; t.minFilter = THREE.LinearFilter; t.needsUpdate = true;
  return t;
}

export class FlatLay {
  group = new THREE.Group();
  /** the tee and its shadow, turned a hair off square; the table and the light stay put */
  private lay = new THREE.Group();
  private table: THREE.Mesh | null = null;
  private top: THREE.Mesh | null = null;
  private under: THREE.Mesh | null = null;
  private shade: THREE.Mesh | null = null;
  private time = uniform(0);
  private gust = uniform(0);
  private amp = uniform(0);
  private live = uniform(0);
  private t = 0;
  private wind = new Wind();
  private air: Air;
  private sunL: THREE.Vector3;
  private still = false;
  side: Side | null = null;
  private ready: Promise<void> | null = null;
  private mats: { top: THREE.MeshPhysicalNodeMaterial; under: THREE.MeshStandardNodeMaterial; shade: THREE.MeshBasicNodeMaterial } | null = null;
  private sdTopNode = texture(new THREE.DataTexture(new Uint16Array(1), 1, 1, THREE.RedFormat, THREE.HalfFloatType));
  private sdUnderNode = texture(new THREE.DataTexture(new Uint16Array(1), 1, 1, THREE.RedFormat, THREE.HalfFloatType));
  private sdBackNode = texture(new THREE.DataTexture(new Uint16Array(1), 1, 1, THREE.RedFormat, THREE.HalfFloatType));

  constructor(private look: LookNodes, private aniso: number, private renderer: THREE.WebGPURenderer) {
    this.group.add(this.lay);
    // the window: a soft pool of daylight coming in low across the table (low enough to model every crease),
    // falling off away from where the tee lies; and the room's own light from all round, a touch cooler
    const L = new THREE.Vector3(IN_SIDE[0], IN_SIDE[1], IN_UP).normalize();
    const sunColour = new THREE.Color().setRGB(1, 0.955, 0.89, THREE.SRGBColorSpace);
    const sun = new THREE.SpotLight(sunColour, 4.9, 0, 0.36, 1, 0);
    sun.position.copy(L.multiplyScalar(3.2));
    // real shadows: the tee's edge and every crease cast onto the table (and onto the cotton beside them); a
    // window a metre across two metres off softens them by a few millimetres at this height
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.near = 2; sun.shadow.camera.far = 4.6;
    sun.shadow.bias = -0.0002; sun.shadow.normalBias = 0.0012; sun.shadow.radius = 4;
    this.group.add(sun, sun.target);
    const room = new THREE.HemisphereLight(new THREE.Color().setRGB(0.93, 0.95, 1, THREE.SRGBColorSpace), new THREE.Color(0x6b655c), 0.62);
    room.position.set(0, 0, 1);
    this.group.add(room);
    sun.map = windowLight();
    this.air = new Air(aniso, sunColour, renderer);
    this.sunL = new THREE.Vector3(IN_SIDE[0], IN_SIDE[1], IN_UP).normalize();
    this.group.add(this.air.group);
  }

  /** everything that's the same every time, got ready ahead (while the page is idle): the table, the materials,
   *  both panels' outlines and grids */
  async warm() {
    await this.init();
    // each side up (its print as printed) and under (mirrored), as place() lays them; one per idle moment
    for (const side of ["back", "front"] as const) {
      await this.idle(); const s = sdf(side);
      await this.idle(); grid(s, GRID_H);
      await this.idle(); fixedOf(s, GRID_H, side === "front" ? 0.25 : 0.75, false, true);
      await this.idle(); fixedOf(s, GRID_H, side === "front" ? 0.25 : 0.75, true, true);
    }
    // and the first lay of each side
    for (const side of ["back", "front"] as const) this.next[side] ??= this.makeLay(side, true);
  }

  /** the table and the materials: once */
  private init() {
    return (this.ready ??= (async () => {
      const tx = async (name: string, srgb: boolean) => {
        const t = await picture(`/tee/table/${name}`, this.renderer, srgb);
        t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set((TABLE * 100) / WOOD_CM, (TABLE * 100) / WOOD_CM);
        t.anisotropy = this.aniso; t.needsUpdate = true; return t;
      };
      const [map, nrm, arm] = await Promise.all([tx("wood.webp", true), tx("wood-n.webp", false), tx("wood-arm.webp", false)]);
      const wood = new THREE.MeshStandardNodeMaterial({ map, normalMap: nrm, roughnessMap: arm, aoMap: arm, roughness: 1, metalness: 0 });
      wood.normalScale.set(1.15, 1.15);
      const table = new THREE.Mesh(new THREE.PlaneGeometry(TABLE, TABLE), wood);
      table.rotation.z = Math.PI / 2;       // the boards run the length of the tee
      table.receiveShadow = true;
      this.group.add(table); this.table = table;
      this.mats = this.materials();
      await this.air.init();
    })());
  }

  private materials() {
    const lk = this.look, pl = attribute("pl", "vec2");
    // the outline, sampled where the pixel is: the edge is exact at any zoom; the same cut makes the shadow
    const edgeOf = (node: ReturnType<typeof texture>) => {
      const sd = at(node, pl);
      // the panel rolls over at its edge (it's a fold, or a hem): the normal turns outward in the last few mm
      const e = vec2(1 / SD_W, 1 / SD_H);
      const gx = at(node, pl.add(vec2(e.x, 0))).sub(at(node, pl.sub(vec2(e.x, 0))));
      const gy = at(node, pl.add(vec2(0, e.y))).sub(at(node, pl.sub(vec2(0, e.y))));
      const ramp = float(1).sub(smoothstep(0, 0.5, sd.negate()));
      const tilt = normalize(vec2(gx, gy).add(vec2(1e-6, 0))).mul(ramp.mul(1.3));
      return { mask: sd.lessThan(0), tilt: modelViewMatrix.mul(vec4(tilt, 0, 0)).xyz };
    };
    // the air in the room. The loose edges (hem, sleeve openings) lift a few millimetres, a swell travelling
    // across the tee; and wherever the cotton is already off the table (a crease, air caught under it) it rises
    // and settles a little, the creases drifting as the air moves under them. Both as strong as the gust.
    const fl = attribute("fl", "vec3"), rise = attribute("rise", "float");
    const xm = positionLocal.x, ym = positionLocal.y;
    const ph = this.time.mul(1.7).add(xm.mul(9));
    const wave = sin(ph).mul(0.35).add(0.65);
    // never quite still (the room's own draught keeps the cotton breathing), and in a real puff a quicker ripple
    // runs through it on top of the slow drift
    const air = this.gust.mul(0.85).add(0.15);
    const k = this.amp.mul(air);
    const lift = fl.x.mul(k).mul(wave);
    const stir = sin(this.time.mul(0.83).add(xm.mul(4.1)).add(ym.mul(2.6))).mul(0.6)
      .add(sin(this.time.mul(1.37).sub(ym.mul(5.3)).add(xm.mul(1.7))).mul(0.4))
      .add(sin(this.time.mul(2.9).sub(xm.mul(11)).add(ym.mul(3.1))).mul(this.gust.mul(this.gust).mul(0.3)))
      .mul(this.live.mul(air).mul(0.38));
    const move = vec3(0, 0, lift.add(rise.mul(stir)));
    // the slopes these add turn the light: the edge lift's d/dx, d/dy (fl.yz: the looseness's slope per cm), and
    // a crease grown by a fraction s tilts its normal by s times as much
    const sx = k.mul(fl.y.mul(100).mul(wave).add(fl.x.mul(cos(ph).mul(0.35 * 9))));
    const sy = k.mul(fl.z.mul(100).mul(wave));
    const tiltL = vec3(sx.negate().add(normalLocal.x.mul(stir)), sy.negate().add(normalLocal.y.mul(stir)), 0);
    const breath = varying(modelViewMatrix.mul(vec4(tiltL, 0)).xyz, "vFlatBreath");

    const top = new THREE.MeshPhysicalNodeMaterial({ roughness: 1, metalness: 0, specularIntensity: 0.5 });
    const et = edgeOf(this.sdTopNode);
    top.colorNode = vec4(lk.color, 1); top.roughnessNode = lk.rough;
    // cotton lying in light that rakes across it: the fuzz on the fibres lights up along every crease (on black
    // this is most of what shows them), less over the ink
    top.sheenNode = lk.sheen.mul(5); top.sheenRoughnessNode = float(0.45);
    top.maskNode = et.mask;
    top.positionNode = positionLocal.add(move);
    top.normalNode = normalize(normalMap(lk.relief.mul(0.5).add(0.5)).add(et.tilt).add(breath));

    // the other panel, inside up: plain cotton
    const under = new THREE.MeshStandardNodeMaterial({ roughness: 0.95, metalness: 0 });
    const eu = edgeOf(this.sdUnderNode);
    under.colorNode = vec4(lk.fabric.mul(0.9), 1);
    under.maskNode = eu.mask;
    under.positionNode = positionLocal.add(move);
    under.normalNode = normalize(normalMap(lk.relief.mul(0.5).add(0.5)).add(eu.tilt).add(breath));

    // where the cotton touches the table the light from the room can't get in: a soft dark line all round it
    const shade = new THREE.MeshBasicNodeMaterial({ transparent: true, depthWrite: false });
    const near = at(this.sdBackNode, pl);
    shade.colorNode = vec3(0.02, 0.018, 0.015);
    shade.opacityNode = float(1).sub(smoothstep(-0.2, 0.6, near)).mul(0.5);
    return { top, under, shade };
  }

  /**
   * Lay the tee on the table, `side` up, settled afresh (a new seed every time), framed so that side's print
   * sits where the camera looks. The group faces the camera: the photo is taken from straight above.
   */
  /**
   * One lay of the cotton with `side` up: settled afresh (a new seed every time), as the two panels' meshes. Worked
   * out a step per idle moment when `idle` (the next lay of each side is got ready ahead), at once when it's wanted.
   */
  private async makeLay(side: Side, idle: boolean) {
    const step = () => (idle ? this.idle() : Promise.resolve());
    const st = settle((Math.random() * 2 ** 32) >>> 0);
    const other: Side = side === "back" ? "front" : "back";
    const sTop = sdf(side), sUnder = sdf(other);
    // the atlas: front cell left (u 0..0.5), back cell right; the face up reads as it's printed, the one under is mirrored
    const cTop = side === "front" ? 0.25 : 0.75, cUnder = other === "front" ? 0.25 : 0.75;
    const build = (s: Sdf, h: number, c: number, mirror: boolean, z: (k: number, g: ReturnType<typeof grid>) => number, withLoose: boolean, up: (k: number, g: ReturnType<typeof grid>) => number) => {
      const g = grid(s, h), n = g.X.length;
      const { U, PL, FL } = fixedOf(s, h, c, mirror, withLoose);
      // and how this lay lifts it: new every time
      const P = new Float32Array(n * 3), RI = new Float32Array(n);
      for (let k = 0; k < n; k++) { P[3 * k] = g.X[k] / 100; P[3 * k + 1] = g.Y[k] / 100; P[3 * k + 2] = z(k, g) / 100; RI[k] = up(k, g) / 100; }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.BufferAttribute(P, 3)); geo.setAttribute("uv", new THREE.BufferAttribute(U, 2));
      geo.setAttribute("pl", new THREE.BufferAttribute(PL, 2)); geo.setAttribute("fl", new THREE.BufferAttribute(FL, 3));
      geo.setAttribute("rise", new THREE.BufferAttribute(RI, 1));
      geo.setIndex(new THREE.BufferAttribute(g.idx, 1)); geo.computeVertexNormals();
      return { geo, g };
    };
    // the panel underneath: flat on the table but for the air under it; the one on top: over it, with every crease,
    // rolling down to the table in the last centimetre at its edge
    // (both grids have the same layout, so a vertex index is the same point in each)
    const h = GRID_H;
    await step(); const g0 = grid(sTop, h);
    await step(); const swell = heights(g0.X, g0.Y, g0.nx, h, g0.x0, g0.y0, st, false);
    await step(); const lie = heights(g0.X, g0.Y, g0.nx, h, g0.x0, g0.y0, st, true);
    // (the under panel rises and settles with the air caught under it; the top one with that and its own creases)
    await step(); const under = build(sUnder, h, cUnder, true, (k, g) => 0.03 + swell[k] * 0.6 * smooth(0, 1.5, -g.D[k]), true, (k, g) => swell[k] * 0.6 * smooth(0, 1.5, -g.D[k]));
    await step(); const topMesh = build(sTop, h, cTop, false, (k, g) => 0.05 + (0.1 + lie[k] - swell[k] * 0.4) * smooth(0, 1, -g.D[k]), true, (k, g) => (lie[k] - swell[k] * 0.4) * smooth(0, 1, -g.D[k]));
    return { st, under, topMesh, lie, swell };
  }
  private next: Partial<Record<Side, ReturnType<FlatLay["makeLay"]>>> = {};
  /** an idle moment; at once while a lay is wanted now (place() calls in every one waiting) */
  private rush = false;
  private wake: (() => void)[] = [];
  private idle() {
    if (this.rush) return Promise.resolve();
    return new Promise<void>((r) => {
      this.wake.push(r);
      if ("requestIdleCallback" in globalThis) requestIdleCallback(() => r(), { timeout: 2000 }); else setTimeout(r, 200);
    });
  }

  /**
   * Lay the tee on the table, `side` up, settled afresh (a new seed every time), framed so that side's print
   * sits where the camera looks. The group faces the camera: the photo is taken from straight above.
   */
  async place(side: Side, cam: { pos: THREE.Vector3; target: THREE.Vector3 }, still: boolean) {
    await this.init();
    const other: Side = side === "back" ? "front" : "back";
    const sTop = sdf(side), sUnder = sdf(other), sBack = sdf("back");
    // the lay got ready while the page was idle (hurried along if it isn't finished), or one now
    this.rush = true; for (const f of this.wake.splice(0)) f();
    let lay: Awaited<ReturnType<FlatLay["makeLay"]>>;
    try { lay = await (this.next[side] ?? this.makeLay(side, false)); } finally { this.rush = false; }
    delete this.next[side];
    const { st, under, topMesh, lie, swell } = lay;
    this.sdTopNode.value = sTop.tex; this.sdUnderNode.value = sUnder.tex; this.sdBackNode.value = sBack.tex;
    this.dispose();
    const shadeGeo = new THREE.PlaneGeometry(PW / 100, PH / 100);
    const sp = shadeGeo.attributes.position, spl = new Float32Array(sp.count * 2);
    for (let k = 0; k < sp.count; k++) { spl[2 * k] = sp.getX(k) * 100 / PW + 0.5; spl[2 * k + 1] = sp.getY(k) * 100 / PH + 0.5; }
    shadeGeo.setAttribute("pl", new THREE.BufferAttribute(spl, 2));
    const m = this.mats!;
    this.under = new THREE.Mesh(under.geo, m.under);
    this.top = new THREE.Mesh(topMesh.geo, m.top);
    this.shade = new THREE.Mesh(shadeGeo, m.shade); this.shade.position.z = 0.0001; this.shade.renderOrder = 1;
    for (const o of [this.under, this.top, this.shade]) { o.frustumCulled = false; this.lay.add(o); }
    this.top.castShadow = this.top.receiveShadow = this.under.castShadow = this.under.receiveShadow = true;

    // frame: the middle of the tee sits where the camera looks, turned a hair off square around it; the views
    // open on the print from there (Viewer's spots), and zoomed right out the whole tee lies on the table
    const centre: V2 = [0, 2.2];
    const c = Math.cos(st.tilt), s = Math.sin(st.tilt);
    this.lay.rotation.z = st.tilt;
    this.lay.position.set(-(c * centre[0] - s * centre[1]) / 100, -(s * centre[0] + c * centre[1]) / 100, 0);
    this.table!.position.set(st.table[0], st.table[1], 0);
    // the table a little further off than the form stands, so the lens takes in the whole tee at its widest
    this.group.position.copy(cam.target).sub(cam.pos).multiplyScalar(FAR).add(cam.pos);
    this.group.lookAt(cam.pos);
    this.group.updateMatrixWorld(true);
    this.air.sunDir.value.copy(this.sunL).transformDirection(this.group.matrixWorld);
    this.side = side;
    this.amp.value = still ? 0 : 0.0075; this.live.value = still ? 0 : 1;
    this.still = still; this.air.reset(this.wind); this.air.group.visible = !still;
    this.heightAt = this.makeHeightAt(topMesh.g, lie, swell);
    // the next time this side goes up it settles differently again: that lay is worked out while the page is idle
    this.next[side] = this.makeLay(side, true);
  }

  /** the air in the room: true while anything moves (the view has to be drawn) */
  tick(dt: number) {
    if (this.still) return false;
    this.t += dt;
    this.time.value = this.t;
    this.gust.value = this.wind.step(dt);
    // the air works in the table's frame; the tee lies turned a hair inside it
    const L = this.lay, c = Math.cos(-L.rotation.z), s = Math.sin(-L.rotation.z), ox = L.position.x, oy = L.position.y;
    this.air.step(dt, this.wind, (x, y) => { const px = x - ox, py = y - oy; return this.heightAt(c * px - s * py, s * px + c * py); });
    return true;
  }

  /** how high the cotton lies at a point of the tee's own frame (m), 0 off it */
  private heightAt: (x: number, y: number) => number = () => 0;
  private makeHeightAt(g: ReturnType<typeof grid>, lie: Float32Array, swell: Float32Array) {
    return (xm: number, ym: number) => {
      const x = xm * 100, y = ym * 100, i = Math.round((x - g.x0) / g.h), j = Math.round((y - g.y0) / g.h);
      if (i < 0 || j < 0 || i >= g.nx || j >= g.ny) return 0;
      const k = j * g.nx + i;
      if (g.D[k] > 0) return 0;
      return (0.05 + (0.1 + lie[k] - swell[k] * 0.4) * smooth(0, 1, -g.D[k])) / 100;
    };
  }

  private dispose() {
    for (const o of [this.under, this.top, this.shade]) if (o) { this.lay.remove(o); o.geometry.dispose(); }
    this.under = this.top = this.shade = null;
  }
}
