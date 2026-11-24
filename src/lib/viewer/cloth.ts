// Real-time cloth: the tee lags and settles as it turns, and a slow breeze moves through it.
//
// The render mesh (~340k vertices, both shells) is far too heavy to simulate per frame, so a coarse particle
// net is built from it: one particle per 3 cm cell, edges wherever the mesh connects two cells. Each particle
// is a mass on a spring toward where the garment rests (the rest pose already holds gravity and the form's
// support). Where the form carries the cloth (shoulders, yoke, chest) it is simply carried: those particles
// move with the form and nothing else. Below the chest and along the sleeves the cloth hangs free, with the
// slow, heavily damped swing of 240 GSM cotton: it trails a turn, eases back, and doesn't bounce.
// Distance constraints along the edges keep the jersey from stretching, so motion travels through it the way it
// does through real knit. The simulation runs in world space while the garment is turned, so inertia is real.
//
// Wind: a slow night breeze moves through it. Gusts travel across the cloth as waves (so a ripple runs from
// one side seam to the other), the direction drifts, and there are real lulls when the air goes still. The
// push is aerodynamic: it acts along each patch's normal and against the patch's own velocity, so a panel
// facing the breeze bellies, one edge-on barely moves, and fast swings are damped by the air.
//
// Jersey resists stretching but gives easily under compression, so the edge constraints are firm one way and
// soft the other. Wherever the net is squeezed (a twist as the hem lags a turn, the windward side wrapping
// in) it records how much and along which axis, and the vertex shader raises folds across that axis: rounded
// ridges a few millimetres high, about 5 cm apart for this cotton, with the shading normal tilted to match.
//
// The net and each vertex's skin (its 4 nearest particles) are built in a Worker, so the tee is on screen and
// turning while that runs. Offsets and squeeze reach the vertex shader through two small float textures, so
// the CPU only ever touches the net. Once everything is still, both snap to exactly zero: the path tracer's
// geometry is the rest pose, so the two always agree.
import * as THREE from "three/webgpu";
import { attribute, textureLoad, ivec2, int, floor, positionLocal, normalLocal, length, max, min, sin, cos, dot, float, transformNormalToView } from "three/tsl";

export const TEX_W = 256;
export const TEX_H = 64;        // up to 16384 particles

const SUB_DT = 1 / 120;         // fixed sub-step
const MAX_OFF = 0.07;           // m, a hard limit however hard it is turned
const SQUEEZE_FULL = 0.045;     // 4.5 % compression = fully formed folds
const FOLD_LEN = 0.05;          // m between fold crests (heavy cotton makes few, soft folds)
const FOLD_H = 0.0045;          // m, crest height at full squeeze
const BREEZE = 0.95;            // m/s at the top of a gust: a slow night breeze, not a storm

type Mesh = { pos: Float32Array; idx: Uint32Array };

/** everything the simulation needs, built off the main thread */
export type Net = {
  n: number; rest: Float32Array; nrm: Float32Array;
  ea: Uint32Array; eb: Uint32Array; el: Float32Array;
  w2: Float32Array; damp: Float32Array; inv: Float32Array; mob: Float32Array; pin: Uint8Array;
  skins: { I: Float32Array; W: Float32Array }[];
};

// Self-contained (no imports, no closures): shipped to a Worker as source text.
function buildNet(meshes: { pos: Float32Array; idx: Uint32Array }[], CELL: number, MAXN: number, SUB: number) {
  // ---- particles: one per occupied cell (integer cell keys, no strings)
  const H = (x: number, y: number, z: number) => ((x + 512) * 1024 + (y + 512)) * 1024 + (z + 512);
  const cellOf = new Map<number, number>(), sums: number[] = [], counts: number[] = [], vCell: Int32Array[] = [];
  for (const m of meshes) {
    const vc = new Int32Array(m.pos.length / 3);
    for (let i = 0; i < vc.length; i++) {
      const x = m.pos[3 * i], y = m.pos[3 * i + 1], z = m.pos[3 * i + 2];
      const k = H(Math.floor(x / CELL), Math.floor(y / CELL), Math.floor(z / CELL));
      let c = cellOf.get(k);
      if (c === undefined) { c = counts.length; cellOf.set(k, c); counts.push(0); sums.push(0, 0, 0); }
      sums[3 * c] += x; sums[3 * c + 1] += y; sums[3 * c + 2] += z; counts[c]++; vc[i] = c;
    }
    vCell.push(vc);
  }
  const n = Math.min(counts.length, MAXN);
  const rest = new Float32Array(3 * n);
  for (let c = 0; c < n; c++) for (let k = 0; k < 3; k++) rest[3 * c + k] = sums[3 * c + k] / counts[c];

  // ---- edges from the mesh topology, and a normal per particle (area-weighted, sign-aligned across shells)
  const seen = new Set<number>(), A: number[] = [], B: number[] = [], nrm = new Float32Array(3 * n);
  for (let mi = 0; mi < meshes.length; mi++) {
    const { pos, idx } = meshes[mi], vc = vCell[mi];
    for (let t = 0; t < idx.length; t += 3) {
      for (let e = 0; e < 3; e++) {
        const a = vc[idx[t + e]], b = vc[idx[t + ((e + 1) % 3)]];
        if (a === b || a >= n || b >= n) continue;
        const lo = Math.min(a, b), hi = Math.max(a, b), h = lo * 16384 + hi;
        if (seen.has(h)) continue;
        seen.add(h); A.push(lo); B.push(hi);
      }
      const p0 = 3 * idx[t], p1 = 3 * idx[t + 1], p2 = 3 * idx[t + 2];
      const ux = pos[p1] - pos[p0], uy = pos[p1 + 1] - pos[p0 + 1], uz = pos[p1 + 2] - pos[p0 + 2];
      const vx = pos[p2] - pos[p0], vy = pos[p2 + 1] - pos[p0 + 1], vz = pos[p2 + 2] - pos[p0 + 2];
      const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      for (let j = 0; j < 3; j++) {
        const q = vc[idx[t + j]]; if (q >= n) continue;
        const sgn = nrm[3 * q] * nx + nrm[3 * q + 1] * ny + nrm[3 * q + 2] * nz < 0 ? -1 : 1;
        nrm[3 * q] += sgn * nx; nrm[3 * q + 1] += sgn * ny; nrm[3 * q + 2] += sgn * nz;
      }
    }
  }
  for (let c = 0; c < n; c++) {
    const L = Math.hypot(nrm[3 * c], nrm[3 * c + 1], nrm[3 * c + 2]) || 1;
    nrm[3 * c] /= L; nrm[3 * c + 1] /= L; nrm[3 * c + 2] /= L;
  }
  const ea = Uint32Array.from(A), eb = Uint32Array.from(B), el = new Float32Array(A.length);
  for (let e = 0; e < A.length; e++) {
    const a = 3 * A[e], b = 3 * B[e];
    el[e] = Math.hypot(rest[b] - rest[a], rest[b + 1] - rest[a + 1], rest[b + 2] - rest[a + 2]);
  }

  // ---- carried or free: the form holds the cloth down to the chest and out to the shoulder seam
  let yTop = -1e9, yBot = 1e9;
  for (let c = 0; c < n; c++) { yTop = Math.max(yTop, rest[3 * c + 1]); yBot = Math.min(yBot, rest[3 * c + 1]); }
  const len = yTop - yBot;
  const w2 = new Float32Array(n), damp = new Float32Array(n), inv = new Float32Array(n), mob = new Float32Array(n), pin = new Uint8Array(n);
  const ss = (a: number, b: number, v: number) => { const t = Math.min(1, Math.max(0, (v - a) / (b - a))); return t * t * (3 - 2 * t); };
  for (let c = 0; c < n; c++) {
    const x = rest[3 * c], y = rest[3 * c + 1];
    const down = ss(0.24 * len, 0.8 * len, yTop - y);           // free from below the chest, freest at the hem
    const out = ss(0.24, 0.38, Math.abs(x));                    // and toward the sleeve ends
    const m = Math.max(down, 0.8 * out);
    mob[c] = m;
    if (m < 0.06) { pin[c] = 1; inv[c] = 0; continue; }        // carried by the form: no bounce at all
    const f = 3.2 * (1 - m) + 1.5 * m;                          // natural sway, Hz: heavy cotton, short swing
    const w = 2 * Math.PI * f, zeta = 0.85 * (1 - m) + 0.62 * m; // well damped: trails and eases back, one soft return at most
    w2[c] = w * w;
    damp[c] = Math.exp(-SUB * 2 * zeta * w);
    inv[c] = 0.15 + m;
  }

  // ---- per-vertex skin: the 4 nearest particles within reach, smooth weights
  const R = CELL * 1.7, grid = new Map<number, number[]>();
  for (let c = 0; c < n; c++) {
    const k = H(Math.floor(rest[3 * c] / CELL), Math.floor(rest[3 * c + 1] / CELL), Math.floor(rest[3 * c + 2] / CELL));
    let l = grid.get(k); if (!l) { l = []; grid.set(k, l); } l.push(c);
  }
  const skins: { I: Float32Array; W: Float32Array }[] = [];
  const bi = [0, 0, 0, 0], bw = [0, 0, 0, 0];
  for (const m of meshes) {
    const pos = m.pos, nv = pos.length / 3, I = new Float32Array(4 * nv), W = new Float32Array(4 * nv);
    for (let v = 0; v < nv; v++) {
      const x = pos[3 * v], y = pos[3 * v + 1], z = pos[3 * v + 2];
      const gx = Math.floor(x / CELL), gy = Math.floor(y / CELL), gz = Math.floor(z / CELL);
      bw[0] = bw[1] = bw[2] = bw[3] = 0; bi[0] = bi[1] = bi[2] = bi[3] = 0;
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) for (let dz = -1; dz <= 1; dz++) {
        const list = grid.get(H(gx + dx, gy + dy, gz + dz));
        if (!list) continue;
        for (let li = 0; li < list.length; li++) {
          const c = list[li];
          const d = Math.hypot(x - rest[3 * c], y - rest[3 * c + 1], z - rest[3 * c + 2]);
          if (d >= R) continue;
          const w = (1 - d / R) * (1 - d / R);
          let mi = 0; for (let k = 1; k < 4; k++) if (bw[k] < bw[mi]) mi = k;
          if (w > bw[mi]) { bw[mi] = w; bi[mi] = c; }
        }
      }
      const s = bw[0] + bw[1] + bw[2] + bw[3] || 1;
      for (let k = 0; k < 4; k++) { I[4 * v + k] = bi[k]; W[4 * v + k] = bw[k] / s; }
    }
    skins.push({ I, W });
  }
  return { n, rest, nrm, ea, eb, el, w2, damp, inv, mob, pin, skins };
}

/** builds the net and the skins in a Worker; the meshes are copied, the page keeps every frame */
export function buildNetAsync(meshes: Mesh[]): Promise<Net> {
  const src = `const buildNet = ${buildNet.toString()};
onmessage = (e) => { const r = buildNet(e.data.meshes, ${0.03}, ${TEX_W * TEX_H}, ${SUB_DT});
  const t = [r.rest.buffer, r.nrm.buffer, r.ea.buffer, r.eb.buffer, r.el.buffer, r.w2.buffer, r.damp.buffer, r.inv.buffer, r.mob.buffer, r.pin.buffer];
  for (const s of r.skins) t.push(s.I.buffer, s.W.buffer);
  postMessage(r, t); };`;
  const url = URL.createObjectURL(new Blob([src], { type: "text/javascript" }));
  const w = new Worker(url);
  const copies = meshes.map((m) => ({ pos: m.pos.slice(), idx: Uint32Array.from(m.idx) }));
  return new Promise((resolve, reject) => {
    w.onmessage = (e) => { resolve(e.data as Net); w.terminate(); URL.revokeObjectURL(url); };
    w.onerror = (e) => { reject(e); w.terminate(); URL.revokeObjectURL(url); };
    w.postMessage({ meshes: copies }, copies.flatMap((c) => [c.pos.buffer, c.idx.buffer]));
  });
}

export class Cloth {
  n: number;
  rest: Float32Array; nrm: Float32Array;
  x: Float32Array; xp: Float32Array;
  w2: Float32Array; damp: Float32Array; inv: Float32Array; mob: Float32Array; pin: Uint8Array;
  ea: Uint32Array; eb: Uint32Array; el: Float32Array;
  sq: Float32Array; sqN: Float32Array;
  settled = true;
  /** the breeze; off for people who asked their system for less motion */
  wind = true;
  private time = 0;
  private acc = 0;
  private R = new THREE.Matrix3(); private t = new THREE.Vector3(); private s = 1;
  private started = false;

  constructor(net: Net, public tex: THREE.DataTexture, public wtex: THREE.DataTexture | null = null) {
    this.n = net.n; this.rest = net.rest; this.nrm = net.nrm;
    this.ea = net.ea; this.eb = net.eb; this.el = net.el;
    this.w2 = net.w2; this.damp = net.damp; this.inv = net.inv; this.mob = net.mob; this.pin = net.pin;
    this.x = new Float32Array(this.rest); this.xp = new Float32Array(this.rest);
    this.sq = new Float32Array(3 * this.n); this.sqN = new Float32Array(this.n);
  }

  /** where the garment is held: rotation (3x3), translation, uniform scale (pivot -> world) */
  setPose(R: THREE.Matrix3, t: THREE.Vector3, s = 1) {
    this.R.copy(R); this.t.copy(t); this.s = s;
    if (!this.started) { this.snap(); this.started = true; }
  }

  private target(c: number, out: number[]) {
    const e = this.R.elements, rx = this.rest[3 * c] * this.s, ry = this.rest[3 * c + 1] * this.s, rz = this.rest[3 * c + 2] * this.s;
    out[0] = e[0] * rx + e[3] * ry + e[6] * rz + this.t.x;
    out[1] = e[1] * rx + e[4] * ry + e[7] * rz + this.t.y;
    out[2] = e[2] * rx + e[5] * ry + e[8] * rz + this.t.z;
  }

  /** everything exactly at rest (and the offsets cleared) */
  snap() {
    const p = [0, 0, 0];
    for (let c = 0; c < this.n; c++) { this.target(c, p); for (let k = 0; k < 3; k++) this.x[3 * c + k] = this.xp[3 * c + k] = p[k]; }
    (this.tex.image.data as Float32Array).fill(0); this.tex.needsUpdate = true;
    if (this.wtex) { (this.wtex.image.data as Float32Array).fill(0); this.wtex.needsUpdate = true; }
    this.settled = true; this.acc = 0;
  }

  /** how hard the air is moving right now, 0 (a lull) to 1 (the top of a gust) */
  gust(t = this.time) {
    if (!this.wind) return 0;
    const TAU = 2 * Math.PI;
    const g = 0.5 + 0.22 * Math.sin(TAU * t / 29 + 1) + 0.18 * Math.sin(TAU * t / 17.3) + 0.1 * Math.sin(TAU * t / 7.1 + 2);
    const u = Math.min(1, Math.max(0, (g - 0.4) / 0.32));
    return u * u * (3 - 2 * u);
  }

  /** advance by dt seconds of real time; returns true while anything is still moving */
  step(dt: number) {
    this.acc = Math.min(this.acc + dt, 4 * SUB_DT);    // after a stall, catch up a little, never spiral
    const p = [0, 0, 0], x = this.x, xp = this.xp;
    let moved = false;
    const e = this.R.elements, TAU = 2 * Math.PI;
    let blowing = false;
    while (this.acc >= SUB_DT) {
      this.acc -= SUB_DT;
      this.time += SUB_DT;
      const h2 = SUB_DT * SUB_DT, t = this.time;
      // the breeze: its line drifts slowly, mostly across the view (that's where a hem shows it best)
      const G = this.gust(t), th = 0.3 + 0.45 * Math.sin(TAU * t / 47) + 0.18 * Math.sin(TAU * t / 13.7);
      const dx = Math.cos(th), dz = Math.sin(th) * 0.6, dl = Math.hypot(dx, dz), wx = dx / dl, wz = dz / dl;
      blowing = blowing || G > 0;
      for (let c = 0; c < this.n; c++) {
        this.target(c, p);
        const i = 3 * c, d = this.damp[c], w2 = this.w2[c];
        if (this.pin[c]) { for (let k = 0; k < 3; k++) { xp[i + k] = x[i + k]; x[i + k] = p[k]; } continue; }
        let ax = 0, ay = 0, az = 0;
        if (G > 0) {
          // gusts arrive as waves crossing the garment, a long one and a short one at an angle
          const along = x[i] * wx + x[i + 2] * wz, across = x[i + 1] * 0.8 + (x[i + 2] * wx - x[i] * wz) * 0.6;
          const f = 1 + 0.45 * Math.sin(TAU * (along / 0.42 - 1.7 * t)) + 0.25 * Math.sin(TAU * (across / 0.27 - 2.6 * t) + 1.7);
          const W = BREEZE * G * f;
          // relative air velocity, along the patch's world normal
          const ux = W * wx - (x[i] - xp[i]) / SUB_DT, uy = W * 0.04 - (x[i + 1] - xp[i + 1]) / SUB_DT, uz = W * wz - (x[i + 2] - xp[i + 2]) / SUB_DT;
          const lx = this.nrm[i], ly = this.nrm[i + 1], lz = this.nrm[i + 2];
          const nx = (e[0] * lx + e[3] * ly + e[6] * lz), ny = (e[1] * lx + e[4] * ly + e[7] * lz), nz = (e[2] * lx + e[5] * ly + e[8] * lz);
          const un = (ux * nx + uy * ny + uz * nz) * (0.25 + 0.75 * this.mob[c]) * 0.75;
          ax = un * nx; ay = un * ny; az = un * nz;
        }
        const a = [ax, ay, az];
        for (let k = 0; k < 3; k++) {
          const v = (x[i + k] - xp[i + k]) * d;
          xp[i + k] = x[i + k];
          x[i + k] += v + (p[k] - x[i + k]) * w2 * h2 + a[k] * h2;
        }
      }
      // keep the jersey from stretching: two passes over the net
      for (let it = 0; it < 2; it++) {
        for (let e = 0; e < this.ea.length; e++) {
          const a = 3 * this.ea[e], b = 3 * this.eb[e], wa = this.inv[this.ea[e]], wb = this.inv[this.eb[e]];
          const dx = x[b] - x[a], dy = x[b + 1] - x[a + 1], dz = x[b + 2] - x[a + 2];
          const L = Math.hypot(dx, dy, dz) || 1e-9, rest = this.el[e] * this.s;
          // jersey: firm against stretch, soft against squeeze (it buckles instead)
          if (wa + wb === 0) continue;
          const k = ((L - rest) / L) * (L < rest ? 0.08 : 0.5) / (wa + wb);
          x[a] += dx * k * wa; x[a + 1] += dy * k * wa; x[a + 2] += dz * k * wa;
          x[b] -= dx * k * wb; x[b + 1] -= dy * k * wb; x[b + 2] -= dz * k * wb;
        }
      }
      moved = true;
    }
    if (!moved) return !this.settled;
    // the squeeze: per particle, how much its edges are compressed and along which axis (garment frame)
    if (this.wtex) {
      this.sq.fill(0); this.sqN.fill(0);
      for (let j = 0; j < this.ea.length; j++) {
        const A = this.ea[j], B = this.eb[j], a = 3 * A, b = 3 * B;
        const dx = x[b] - x[a], dy = x[b + 1] - x[a + 1], dz = x[b + 2] - x[a + 2];
        const L = Math.hypot(dx, dy, dz) || 1e-9, c = Math.max(0, 1 - L / (this.el[j] * this.s));
        this.sqN[A]++; this.sqN[B]++;
        if (c <= 0) continue;
        let lx = (e[0] * dx + e[1] * dy + e[2] * dz) / L, ly = (e[3] * dx + e[4] * dy + e[5] * dz) / L, lz = (e[6] * dx + e[7] * dy + e[8] * dz) / L;
        // an axis has no direction: one sign for all of them, so neighbours add up instead of cancelling
        if (ly < 0 || (ly === 0 && lx < 0)) { lx = -lx; ly = -ly; lz = -lz; }
        for (const q of [a, b]) { this.sq[q] += c * lx; this.sq[q + 1] += c * ly; this.sq[q + 2] += c * lz; }
      }
      const W = this.wtex.image.data as Float32Array;
      for (let c = 0; c < this.n; c++) {
        const k = 1 / (Math.max(1, this.sqN[c]) * SQUEEZE_FULL) * 2;
        let sx = this.sq[3 * c] * k, sy = this.sq[3 * c + 1] * k, sz = this.sq[3 * c + 2] * k;
        const m = Math.hypot(sx, sy, sz); if (m > 1) { sx /= m; sy /= m; sz /= m; }
        // folds grow and fade over a few frames, the way cloth takes a moment to buckle and relax
        W[4 * c] += (sx - W[4 * c]) * 0.35; W[4 * c + 1] += (sy - W[4 * c + 1]) * 0.35; W[4 * c + 2] += (sz - W[4 * c + 2]) * 0.35;
      }
      this.wtex.needsUpdate = true;
    }
    // offsets back into the garment's own frame, for the vertex shader
    const out = this.tex.image.data as Float32Array, is = 1 / this.s;
    let maxOff = 0, maxV = 0;
    for (let c = 0; c < this.n; c++) {
      this.target(c, p);
      const i = 3 * c;
      let ox = x[i] - p[0], oy = x[i + 1] - p[1], oz = x[i + 2] - p[2];
      const L = Math.hypot(ox, oy, oz);
      if (L > MAX_OFF) { const k = MAX_OFF / L; ox *= k; oy *= k; oz *= k; x[i] = p[0] + ox; x[i + 1] = p[1] + oy; x[i + 2] = p[2] + oz; }
      maxOff = Math.max(maxOff, L);
      maxV = Math.max(maxV, Math.abs(x[i] - xp[i]) + Math.abs(x[i + 1] - xp[i + 1]) + Math.abs(x[i + 2] - xp[i + 2]));
      // R is a rotation: its inverse is its transpose
      out[4 * c] = (e[0] * ox + e[1] * oy + e[2] * oz) * is;
      out[4 * c + 1] = (e[3] * ox + e[4] * oy + e[5] * oz) * is;
      out[4 * c + 2] = (e[6] * ox + e[7] * oy + e[8] * oz) * is;
    }
    if (!blowing && maxOff < 2e-4 && maxV < 2e-5) { this.snap(); return false; }
    this.settled = false;
    this.tex.needsUpdate = true;
    return true;
  }
}

/** the shared offset texture (one per renderer, reused for every tee) */
export function offsetTexture() {
  const t = new THREE.DataTexture(new Float32Array(TEX_W * TEX_H * 4), TEX_W, TEX_H, THREE.RGBAFormat, THREE.FloatType);
  t.magFilter = t.minFilter = THREE.NearestFilter; t.generateMipmaps = false; t.needsUpdate = true;
  return t;
}

/** vertex shader node: rest position + the cloth offset, blended from the 4 particles this vertex follows */
export function clothedPosition(offsets: THREE.DataTexture) {
  return clothNodes(offsets, null).position;
}

/**
 * The full cloth for a material: `position` (offset + folds) for positionNode, and `bend(n)` to tilt a
 * view-space shading normal by the folds' slope.
 */
export function clothNodes(offsets: THREE.DataTexture, squeeze: THREE.DataTexture | null) {
  const I = attribute("sbI", "vec4"), Wt = attribute("sbW", "vec4");
  const at = (tex: THREE.DataTexture, f: typeof I.x) => {
    const row = floor(f.div(TEX_W));
    return textureLoad(tex, ivec2(int(f.sub(row.mul(TEX_W))), int(row))).xyz;
  };
  const blend = (tex: THREE.DataTexture) => at(tex, I.x).mul(Wt.x).add(at(tex, I.y).mul(Wt.y)).add(at(tex, I.z).mul(Wt.z)).add(at(tex, I.w).mul(Wt.w));
  const moved = positionLocal.add(blend(offsets));
  if (!squeeze) return { position: moved, bend: <T,>(n: T) => n };
  const sv = blend(squeeze), amt = min(length(sv), float(1)), dir = sv.div(max(length(sv), float(1e-4)));
  // ridges across the squeeze axis; a gentle warp so they wander like real folds instead of ruling straight
  const k = (2 * Math.PI) / FOLD_LEN;
  const ph = dot(positionLocal, dir).mul(k).add(sin(positionLocal.y.mul(31).add(positionLocal.x.mul(17))).mul(0.9));
  const h = amt.mul(amt).mul(FOLD_H);
  const position = moved.add(normalLocal.mul(sin(ph).mul(h)));
  const slope = dir.mul(cos(ph).mul(h).mul(k));
  const tangential = slope.sub(normalLocal.mul(dot(normalLocal, slope)));
  const bendView = transformNormalToView(tangential);
  return { position, bend: (n: ReturnType<typeof transformNormalToView>) => n.sub(bendView).normalize() };
}

/** the squeeze texture (same layout as the offsets) */
export function squeezeTexture() { return offsetTexture(); }
