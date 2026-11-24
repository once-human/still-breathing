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
// Folds and creases are not painted on: the net's own shape is the cloth's shape. Each frame the slope of the
// displacement around every particle (how the cloth around it is tilted, bunched or pulled) is measured, and
// the shading follows it, so a ripple the breeze runs across the back catches the light exactly as the moving
// cloth would, and on still cloth there is nothing at all.
//
// The net and each vertex's skin (its 4 nearest particles) are built in a Worker, so the tee is on screen and
// turning while that runs. Offsets and slopes reach the vertex shader through small float textures, so
// the CPU only ever touches the net. Once everything is still, both snap to exactly zero: the path tracer's
// geometry is the rest pose, so the two always agree.
import * as THREE from "three/webgpu";
import { attribute, textureLoad, ivec2, int, floor, positionLocal, normalLocal, length, max, float, vec4, modelViewMatrix, normalMap, varying } from "three/tsl";

export const TEX_W = 256;
export const TEX_H = 16;        // up to 4096 particles (a 2XL tee is about 2000)

const SUB_DT = 1 / 100;         // longest sub-step; each frame is split into equal steps no longer than this
const MAX_OFF = 0.08;           // m, a safety net the cloth never normally reaches
const SOFT_OFF = 0.04;          // m, where the cloth starts to feel the form and stiffens (smoothly)
const BREEZE = 0.32;            // m/s at the top of a gust: still night air, a draught you'd barely feel
// air on cloth, as it really is: pressure 1/2 rho Cd |u| u, over the cloth's weight per area
// (rho 1.2 kg/m3, Cd about 1 for a sheet face-on, 240 GSM jersey = 0.24 kg/m2) -> 2.5 per (m/s)^2
const AIR = (0.5 * 1.2 * 1.0) / 0.24;
const INERTIA = 0.2;            // share of a slow turn the cloth feels as inertia (less the faster it turns)
const SLOPE_MAX = 0.35;         // the steepest a fold may tilt the shading

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
    // only the collar and the tops of the shoulders sit on the form; everything else hangs from them, the
    // yoke barely, the hem and sleeve ends most
    if (yTop - y < 0.06 * len && Math.abs(x) < 0.2) { pin[c] = 1; mob[c] = 0; inv[c] = 0; continue; }
    const down = ss(0.04 * len, 0.85 * len, yTop - y);
    const out = ss(0.2, 0.38, Math.abs(x));
    const m = Math.max(0.12, down, 0.8 * out);
    mob[c] = m;
    const f = 2.6 * (1 - m) + 1.3 * m;                          // natural sway, Hz: heavy cotton, short swing
    const zeta = 0.95 * (1 - m) + 0.72 * m;                     // well damped: it trails and eases back, no bounce
    const w = 2 * Math.PI * f;
    w2[c] = w * w;
    damp[c] = 2 * zeta * w;                                     // decay rate, 1/s (the step works out each frame's share)
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
  settled = true;
  /** the breeze; off for people who asked their system for less motion */
  wind = true;
  private time = 0;
  private hPrev = SUB_DT;
  private R = new THREE.Matrix3(); private t = new THREE.Vector3(); private s = 1;
  private pR = new THREE.Matrix3(); private pT = new THREE.Vector3(); private pS = 1;
  private started = false;
  private off: Float32Array; private shift: Float32Array;
  private G: Float32Array; private S: Float32Array;

  constructor(net: Net, public tex: THREE.DataTexture, public slopes: THREE.DataTexture[] | null = null) {
    this.n = net.n; this.rest = net.rest; this.nrm = net.nrm;
    this.ea = net.ea; this.eb = net.eb; this.el = net.el;
    this.w2 = net.w2; this.damp = net.damp; this.inv = net.inv; this.mob = net.mob; this.pin = net.pin;
    this.x = new Float32Array(this.rest); this.xp = new Float32Array(this.rest);
    this.off = new Float32Array(3 * this.n); this.shift = new Float32Array(3 * this.n);
    this.G = new Float32Array(9 * this.n); this.S = new Float32Array(this.n);
  }

  /**
   * Where the garment is held this frame: rotation (3x3), translation, uniform scale (pivot -> world), and the
   * frame's length. Most of the move is handed straight to the cloth; the rest is left for inertia to act on,
   * and the faster it's moved the smaller that share (air and the form's grip take the rest), so a slow turn
   * trails softly and a hard flick doesn't whip.
   */
  setPose(R: THREE.Matrix3, t: THREE.Vector3, s = 1, dt = 1 / 60) {
    if (this.started) { this.pR.copy(this.R); this.pT.copy(this.t); this.pS = this.s; }
    this.R.copy(R); this.t.copy(t); this.s = s;
    if (!this.started) { this.snap(); this.started = true; this.pR.copy(R); this.pT.copy(t); this.pS = s; return; }
    const a = [0, 0, 0], b = [0, 0, 0], d = this.shift;
    let vmax = 0;
    for (let c = 0; c < this.n; c++) {
      this.targetWith(this.pR, this.pT, this.pS, c, a); this.targetWith(this.R, this.t, this.s, c, b);
      const dx = b[0] - a[0], dy = b[1] - a[1], dz = b[2] - a[2];
      d[3 * c] = dx; d[3 * c + 1] = dy; d[3 * c + 2] = dz;
      vmax = Math.max(vmax, Math.hypot(dx, dy, dz));
    }
    const v = vmax / Math.max(dt, 1e-3), felt = INERTIA / (1 + (v / 0.6) ** 2), k = 1 - felt;
    for (let c = 0; c < this.n; c++) {
      if (this.pin[c]) continue;
      for (let j = 0; j < 3; j++) { const m = d[3 * c + j] * k; this.x[3 * c + j] += m; this.xp[3 * c + j] += m; }
    }
  }
  private targetWith(R: THREE.Matrix3, t: THREE.Vector3, s: number, c: number, out: number[]) {
    const e = R.elements, rx = this.rest[3 * c] * s, ry = this.rest[3 * c + 1] * s, rz = this.rest[3 * c + 2] * s;
    out[0] = e[0] * rx + e[3] * ry + e[6] * rz + t.x;
    out[1] = e[1] * rx + e[4] * ry + e[7] * rz + t.y;
    out[2] = e[2] * rx + e[5] * ry + e[8] * rz + t.z;
  }
  private target(c: number, out: number[]) { this.targetWith(this.R, this.t, this.s, c, out); }

  /** everything exactly at rest (and the offsets cleared) */
  snap() {
    const p = [0, 0, 0];
    for (let c = 0; c < this.n; c++) { this.target(c, p); for (let k = 0; k < 3; k++) this.x[3 * c + k] = this.xp[3 * c + k] = p[k]; }
    (this.tex.image.data as Float32Array).fill(0); this.tex.needsUpdate = true;
    for (const t of this.slopes ?? []) { (t.image.data as Float32Array).fill(0); t.needsUpdate = true; }
    this.settled = true;
  }

  /** how hard the air is moving right now, 0 (a lull) to 1 (the top of a gust) */
  gust(t = this.time) {
    if (!this.wind) return 0;
    const TAU = 2 * Math.PI;
    const g = 0.5 + 0.22 * Math.sin(TAU * t / 29 + 1) + 0.18 * Math.sin(TAU * t / 17.3) + 0.1 * Math.sin(TAU * t / 7.1 + 2);
    const u = Math.min(1, Math.max(0, (g - 0.22) / 0.5));
    return u * u * (3 - 2 * u);
  }

  /**
   * Advance by this frame's dt. The frame is split into equal steps (one at 120 Hz, two at 60), so the cloth
   * moves exactly once per drawn frame: no frame shows a stale cloth, none jumps two steps. Returns true while
   * anything is still moving.
   */
  step(dt: number) {
    dt = Math.min(dt, 0.05);
    if (dt <= 0) return !this.settled;
    const steps = Math.ceil(dt / SUB_DT - 1e-6), h = dt / steps, h2 = h * h;
    const p = [0, 0, 0], x = this.x, xp = this.xp;
    const e = this.R.elements, TAU = 2 * Math.PI;
    let blowing = false;
    for (let st = 0; st < steps; st++) {
      this.time += h;
      const t = this.time;
      // the breeze: its line drifts slowly, mostly across the view (that's where a hem shows it best)
      const G = this.gust(t), th = 0.3 + 0.45 * Math.sin(TAU * t / 47) + 0.18 * Math.sin(TAU * t / 13.7);
      const dx = Math.cos(th), dz = Math.sin(th) * 0.6, dl = Math.hypot(dx, dz), wx = dx / dl, wz = dz / dl;
      blowing = blowing || G > 0;
      for (let c = 0; c < this.n; c++) {
        this.target(c, p);
        const i = 3 * c;
        if (this.pin[c]) { for (let k = 0; k < 3; k++) { xp[i + k] = x[i + k]; x[i + k] = p[k]; } continue; }
        const vx = (x[i] - xp[i]) / this.hPrev, vy = (x[i + 1] - xp[i + 1]) / this.hPrev, vz = (x[i + 2] - xp[i + 2]) / this.hPrev;
        let ax = 0, ay = 0, az = 0;
        if (G > 0) {
          // gusts arrive as slow waves crossing the garment, a long one and a shorter one at an angle
          const along = x[i] * wx + x[i + 2] * wz, across = x[i + 1] * 0.8 + (x[i + 2] * wx - x[i] * wz) * 0.6;
          const f = 1 + 0.5 * Math.sin(TAU * (along / 0.45 - 0.7 * t)) + 0.25 * Math.sin(TAU * (across / 0.3 - 1.1 * t) + 1.7);
          const W = BREEZE * G * f;
          // the air pushes along the patch's normal, by how fast it moves past the patch (so it also damps)
          const ux = W * wx - vx, uy = W * 0.04 - vy, uz = W * wz - vz;
          const lx = this.nrm[i], ly = this.nrm[i + 1], lz = this.nrm[i + 2];
          const nx = e[0] * lx + e[3] * ly + e[6] * lz, ny = e[1] * lx + e[4] * ly + e[7] * lz, nz = e[2] * lx + e[5] * ly + e[8] * lz;
          const u = ux * nx + uy * ny + uz * nz, push = AIR * Math.abs(u) * u;
          ax = push * nx; ay = push * ny; az = push * nz;
        }
        // the pull home stiffens smoothly as the cloth strays (it meets the form and its own seams): no wall
        const ox = x[i] - p[0], oy = x[i + 1] - p[1], oz = x[i + 2] - p[2];
        const r2 = (ox * ox + oy * oy + oz * oz) / (SOFT_OFF * SOFT_OFF);
        const kk = this.w2[c] * (1 + r2), keep = Math.exp(-this.damp[c] * h);
        xp[i] = x[i]; xp[i + 1] = x[i + 1]; xp[i + 2] = x[i + 2];
        x[i] += vx * h * keep + (ax - kk * ox) * h2;
        x[i + 1] += vy * h * keep + (ay - kk * oy) * h2;
        x[i + 2] += vz * h * keep + (az - kk * oz) * h2;
      }
      // keep the jersey from stretching: two passes over the net
      for (let it = 0; it < 2; it++) {
        for (let j = 0; j < this.ea.length; j++) {
          const A = this.ea[j], B = this.eb[j], wa = this.inv[A], wb = this.inv[B];
          if (wa + wb === 0) continue;
          const a = 3 * A, b = 3 * B;
          const ddx = x[b] - x[a], ddy = x[b + 1] - x[a + 1], ddz = x[b + 2] - x[a + 2];
          const L = Math.hypot(ddx, ddy, ddz) || 1e-9, rest = this.el[j] * this.s;
          // jersey: firm against stretch, soft against squeeze (it buckles instead)
          const k = ((L - rest) / L) * (L < rest ? 0.08 : 0.5) / (wa + wb);
          x[a] += ddx * k * wa; x[a + 1] += ddy * k * wa; x[a + 2] += ddz * k * wa;
          x[b] -= ddx * k * wb; x[b + 1] -= ddy * k * wb; x[b + 2] -= ddz * k * wb;
        }
      }
      this.hPrev = h;
    }

    // offsets back into the garment's own frame
    const off = this.off, is = 1 / this.s;
    let maxOff = 0, maxV = 0;
    for (let c = 0; c < this.n; c++) {
      this.target(c, p);
      const i = 3 * c;
      let ox = x[i] - p[0], oy = x[i + 1] - p[1], oz = x[i + 2] - p[2];
      const L = Math.hypot(ox, oy, oz);
      if (L > MAX_OFF) { const k = MAX_OFF / L; ox *= k; oy *= k; oz *= k; x[i] = p[0] + ox; x[i + 1] = p[1] + oy; x[i + 2] = p[2] + oz; xp[i] = x[i]; xp[i + 1] = x[i + 1]; xp[i + 2] = x[i + 2]; }
      maxOff = Math.max(maxOff, L);
      maxV = Math.max(maxV, Math.abs(x[i] - xp[i]) + Math.abs(x[i + 1] - xp[i + 1]) + Math.abs(x[i + 2] - xp[i + 2]));
      // R is a rotation: its inverse is its transpose
      off[i] = (e[0] * ox + e[1] * oy + e[2] * oz) * is;
      off[i + 1] = (e[3] * ox + e[4] * oy + e[5] * oz) * is;
      off[i + 2] = (e[6] * ox + e[7] * oy + e[8] * oz) * is;
    }
    if (!blowing && maxOff < 2e-4 && maxV < 2e-5) { this.snap(); return false; }
    this.settled = false;
    const out = this.tex.image.data as Float32Array;
    for (let c = 0; c < this.n; c++) { out[4 * c] = off[3 * c]; out[4 * c + 1] = off[3 * c + 1]; out[4 * c + 2] = off[3 * c + 2]; }
    this.tex.needsUpdate = true;

    // the slope of the displacement around each particle (a 3x3 per particle, least squares over its edges):
    // the shader turns any normal by it, so the light follows the cloth's real shape this frame
    if (this.slopes) {
      const G = this.G, S = this.S, r = this.rest;
      G.fill(0); S.fill(0);
      for (let j = 0; j < this.ea.length; j++) {
        const A = this.ea[j], B = this.eb[j], a = 3 * A, b = 3 * B;
        const ex = r[b] - r[a], ey = r[b + 1] - r[a + 1], ez = r[b + 2] - r[a + 2];
        const dox = off[b] - off[a], doy = off[b + 1] - off[a + 1], doz = off[b + 2] - off[a + 2];
        const l2 = ex * ex + ey * ey + ez * ez;
        for (const q of [A, B]) {
          const g = 9 * q;
          G[g] += dox * ex; G[g + 1] += dox * ey; G[g + 2] += dox * ez;
          G[g + 3] += doy * ex; G[g + 4] += doy * ey; G[g + 5] += doy * ez;
          G[g + 6] += doz * ex; G[g + 7] += doz * ey; G[g + 8] += doz * ez;
          S[q] += l2;
        }
      }
      const T = this.slopes.map((t) => t.image.data as Float32Array);
      for (let c = 0; c < this.n; c++) {
        // a surface's edges span two directions: the isotropic least-squares estimate is 2/sum|e|^2 * sum(do e^T)
        const k = S[c] > 0 ? 2 / S[c] : 0, g = 9 * c;
        for (let row = 0; row < 3; row++) {
          T[row][4 * c] = G[g + 3 * row] * k; T[row][4 * c + 1] = G[g + 3 * row + 1] * k; T[row][4 * c + 2] = G[g + 3 * row + 2] * k;
        }
      }
      for (const t of this.slopes) t.needsUpdate = true;
    }
    return true;
  }
}

/** the shared offset texture (one per renderer, reused for every tee) */
export function offsetTexture() {
  const t = new THREE.DataTexture(new Float32Array(TEX_W * TEX_H * 4), TEX_W, TEX_H, THREE.RGBAFormat, THREE.FloatType);
  t.magFilter = t.minFilter = THREE.NearestFilter; t.generateMipmaps = false; t.needsUpdate = true;
  return t;
}

/** the three rows of each particle's displacement slope (same layout as the offsets) */
export function slopeTextures() { return [offsetTexture(), offsetTexture(), offsetTexture()]; }

/** vertex shader node: rest position + the cloth offset, blended from the 4 particles this vertex follows */
export function clothedPosition(offsets: THREE.DataTexture) {
  return clothNodes(offsets, null).position;
}

/**
 * The full cloth for a material: `position` for positionNode, and `bend(n)` to turn a view-space shading
 * normal by the cloth's slope at that point. Everything is read in the vertex shader (the particle indices
 * can't be interpolated) and handed to the fragment as one smooth vector.
 */
export function clothNodes(offsets: THREE.DataTexture, slopes: THREE.DataTexture[] | null) {
  const I = attribute("sbI", "vec4"), Wt = attribute("sbW", "vec4");
  const at = (tex: THREE.DataTexture, f: typeof I.x) => {
    const row = floor(f.div(TEX_W));
    return textureLoad(tex, ivec2(int(f.sub(row.mul(TEX_W))), int(row))).xyz;
  };
  const blend = (tex: THREE.DataTexture) => at(tex, I.x).mul(Wt.x).add(at(tex, I.y).mul(Wt.y)).add(at(tex, I.z).mul(Wt.z)).add(at(tex, I.w).mul(Wt.w));
  const position = positionLocal.add(blend(offsets));
  if (!slopes) return { position, bend: <T,>(n: T) => n };
  // a surface whose points move by o(x) turns its normal n by -(do/dx)^T n. Built from the vertex's own normal,
  // it's right for both shells whichever way each faces; zero (exactly) wherever the cloth is at rest.
  const n = normalLocal, r0 = blend(slopes[0]), r1 = blend(slopes[1]), r2 = blend(slopes[2]);
  const raw = r0.mul(n.x).add(r1.mul(n.y)).add(r2.mul(n.z)).negate();
  const tang = raw.sub(n.mul(n.dot(raw)));
  const tilt = tang.mul(float(SLOPE_MAX).div(max(length(tang), float(SLOPE_MAX))));
  const tiltView = varying(modelViewMatrix.mul(vec4(tilt, 0)).xyz, "vClothTilt");
  return { position, bend: (nv: ReturnType<typeof normalMap>) => nv.add(tiltView).normalize() };
}
