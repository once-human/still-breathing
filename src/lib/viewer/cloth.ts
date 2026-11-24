// Real-time cloth: the tee swings, lags and flares as it turns, then settles back onto the form.
//
// The render mesh (~340k vertices, both shells) is far too heavy to simulate per frame, so a coarse particle
// net is built from it: one particle per 3 cm cell, edges wherever the mesh connects two cells. Each particle
// is a mass on a spring toward where the garment rests (the rest pose already holds gravity and the form's
// support), stiff where the form carries the cloth (shoulders, chest) and loose toward the hem and the sleeve
// ends. Distance constraints along the edges keep the cloth from stretching, so motion travels through it the
// way it does through jersey. The simulation runs in world space while the garment is turned, so inertia is
// real: start turning and the hem lags behind, spin fast and it flares out, stop and it swings past and settles.
//
// Each render vertex follows its 4 nearest particles (smooth weights), applied in the vertex shader from a
// float texture of per-particle offsets, so the CPU only ever touches the small net. Once everything is still,
// the offsets snap to exactly zero: the path tracer's geometry is the rest pose, so the two always agree.
import * as THREE from "three/webgpu";
import { attribute, textureLoad, ivec2, int, floor, positionLocal } from "three/tsl";

export const TEX_W = 256;
export const TEX_H = 64;        // up to 16384 particles

const CELL = 0.03;              // m
const SUB_DT = 1 / 120;         // fixed sub-step
const MAX_OFF = 0.14;           // m, a hard limit however hard it is flung

type Mesh = { pos: Float32Array; idx: ArrayLike<number> };

export class Cloth {
  n: number;
  rest: Float32Array;
  x: Float32Array;
  xp: Float32Array;
  w2: Float32Array;    // spring stiffness (omega^2) per particle
  damp: Float32Array;  // velocity kept per sub-step
  inv: Float32Array;   // inverse mass for the constraints
  ea: Uint32Array; eb: Uint32Array; el: Float32Array;
  settled = true;
  private acc = 0;
  private R = new THREE.Matrix3(); private t = new THREE.Vector3(); private s = 1;
  private started = false;

  /** builds the net and the per-vertex skin (index + weight attributes for each mesh) */
  constructor(meshes: Mesh[], public tex: THREE.DataTexture) {
    // ---- particles: one per occupied cell
    const key = (x: number, y: number, z: number) => `${Math.floor(x / CELL)},${Math.floor(y / CELL)},${Math.floor(z / CELL)}`;
    const cellOf = new Map<string, number>(), sums: number[] = [], counts: number[] = [];
    const vCell: Int32Array[] = [];
    for (const m of meshes) {
      const vc = new Int32Array(m.pos.length / 3);
      for (let i = 0; i < vc.length; i++) {
        const x = m.pos[3 * i], y = m.pos[3 * i + 1], z = m.pos[3 * i + 2], k = key(x, y, z);
        let c = cellOf.get(k);
        if (c === undefined) { c = counts.length; cellOf.set(k, c); counts.push(0); sums.push(0, 0, 0); }
        sums[3 * c] += x; sums[3 * c + 1] += y; sums[3 * c + 2] += z; counts[c]++; vc[i] = c;
      }
      vCell.push(vc);
    }
    const n = Math.min(counts.length, TEX_W * TEX_H);
    this.n = n;
    this.rest = new Float32Array(3 * n);
    for (let c = 0; c < n; c++) for (let k = 0; k < 3; k++) this.rest[3 * c + k] = sums[3 * c + k] / counts[c];

    // ---- edges from the mesh topology
    const seen = new Set<number>(), A: number[] = [], B: number[] = [];
    for (let mi = 0; mi < meshes.length; mi++) {
      const idx = meshes[mi].idx, vc = vCell[mi];
      for (let t = 0; t < idx.length; t += 3) {
        for (let e = 0; e < 3; e++) {
          const a = vc[idx[t + e]], b = vc[idx[t + ((e + 1) % 3)]];
          if (a === b || a >= n || b >= n) continue;
          const lo = Math.min(a, b), hi = Math.max(a, b), h = lo * 16384 + hi;
          if (seen.has(h)) continue;
          seen.add(h); A.push(lo); B.push(hi);
        }
      }
    }
    this.ea = Uint32Array.from(A); this.eb = Uint32Array.from(B);
    this.el = new Float32Array(A.length);
    for (let e = 0; e < A.length; e++) this.el[e] = Math.hypot(...[0, 1, 2].map((k) => this.rest[3 * A[e] + k] - this.rest[3 * B[e] + k]) as [number, number, number]);

    // ---- where the form carries the cloth and where it hangs free
    let yTop = -1e9, yBot = 1e9;
    for (let c = 0; c < n; c++) { yTop = Math.max(yTop, this.rest[3 * c + 1]); yBot = Math.min(yBot, this.rest[3 * c + 1]); }
    const len = yTop - yBot;
    this.w2 = new Float32Array(n); this.damp = new Float32Array(n); this.inv = new Float32Array(n);
    const ss = (a: number, b: number, v: number) => { const t = Math.min(1, Math.max(0, (v - a) / (b - a))); return t * t * (3 - 2 * t); };
    for (let c = 0; c < n; c++) {
      const x = this.rest[3 * c], y = this.rest[3 * c + 1];
      const down = ss(0.16 * len, 0.72 * len, yTop - y);           // free below the chest, freest at the hem
      const out = ss(0.2, 0.36, Math.abs(x));                      // and along the sleeves
      const m = Math.max(down, 0.85 * out);
      const f = 7.5 * (1 - m) + 1.05 * m;                          // natural swing, Hz: hem ~1 Hz, like the real thing
      this.w2[c] = (2 * Math.PI * f) ** 2;
      this.damp[c] = Math.exp(-SUB_DT * (2.2 + 3 * (1 - m)));      // cotton jersey: a swing or two, then still
      this.inv[c] = 0.08 + m;
    }
    this.x = new Float32Array(this.rest); this.xp = new Float32Array(this.rest);
  }

  /** per-vertex skin: the 4 nearest particles, smooth weights. Returns attributes for one mesh. */
  async skin(pos: Float32Array) {
    const R = CELL * 1.7, grid = new Map<string, number[]>();
    const g = (x: number) => Math.floor(x / CELL);
    for (let c = 0; c < this.n; c++) {
      const k = `${g(this.rest[3 * c])},${g(this.rest[3 * c + 1])},${g(this.rest[3 * c + 2])}`;
      (grid.get(k) ?? grid.set(k, []).get(k)!).push(c);
    }
    const nv = pos.length / 3, I = new Float32Array(4 * nv), W = new Float32Array(4 * nv);
    const bi = [0, 0, 0, 0], bw = [0, 0, 0, 0];
    let t0 = performance.now();
    for (let v = 0; v < nv; v++) {
      // in slices, so the page keeps its frames while a new tee is being dressed
      if ((v & 4095) === 0 && performance.now() - t0 > 6) { await new Promise((r) => setTimeout(r, 0)); t0 = performance.now(); }
      const x = pos[3 * v], y = pos[3 * v + 1], z = pos[3 * v + 2], gx = g(x), gy = g(y), gz = g(z);
      bw.fill(0); bi.fill(0);
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) for (let dz = -1; dz <= 1; dz++) {
        const list = grid.get(`${gx + dx},${gy + dy},${gz + dz}`);
        if (!list) continue;
        for (const c of list) {
          const d = Math.hypot(x - this.rest[3 * c], y - this.rest[3 * c + 1], z - this.rest[3 * c + 2]);
          if (d >= R) continue;
          const w = (1 - d / R) ** 2;
          let m = 0; for (let k = 1; k < 4; k++) if (bw[k] < bw[m]) m = k;
          if (w > bw[m]) { bw[m] = w; bi[m] = c; }
        }
      }
      const s = bw[0] + bw[1] + bw[2] + bw[3] || 1;
      for (let k = 0; k < 4; k++) { I[4 * v + k] = bi[k]; W[4 * v + k] = bw[k] / s; }
    }
    return { index: new THREE.BufferAttribute(I, 4), weight: new THREE.BufferAttribute(W, 4) };
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
    this.settled = true; this.acc = 0;
  }

  /** advance by dt seconds of real time; returns true while anything is still moving */
  step(dt: number) {
    this.acc = Math.min(this.acc + dt, 4 * SUB_DT);    // after a stall, catch up a little, never spiral
    const p = [0, 0, 0], x = this.x, xp = this.xp;
    let moved = false;
    while (this.acc >= SUB_DT) {
      this.acc -= SUB_DT;
      const h2 = SUB_DT * SUB_DT;
      for (let c = 0; c < this.n; c++) {
        this.target(c, p);
        const i = 3 * c, d = this.damp[c], w2 = this.w2[c];
        for (let k = 0; k < 3; k++) {
          const v = (x[i + k] - xp[i + k]) * d;
          xp[i + k] = x[i + k];
          x[i + k] += v + (p[k] - x[i + k]) * w2 * h2;
        }
      }
      // keep the jersey from stretching: two passes over the net
      for (let it = 0; it < 2; it++) {
        for (let e = 0; e < this.ea.length; e++) {
          const a = 3 * this.ea[e], b = 3 * this.eb[e], wa = this.inv[this.ea[e]], wb = this.inv[this.eb[e]];
          const dx = x[b] - x[a], dy = x[b + 1] - x[a + 1], dz = x[b + 2] - x[a + 2];
          const L = Math.hypot(dx, dy, dz) || 1e-9, rest = this.el[e] * this.s;
          const k = ((L - rest) / L) * 0.5 / (wa + wb);
          x[a] += dx * k * wa; x[a + 1] += dy * k * wa; x[a + 2] += dz * k * wa;
          x[b] -= dx * k * wb; x[b + 1] -= dy * k * wb; x[b + 2] -= dz * k * wb;
        }
      }
      moved = true;
    }
    if (!moved) return !this.settled;
    // offsets back into the garment's own frame, for the vertex shader
    const out = this.tex.image.data as Float32Array, e = this.R.elements, is = 1 / this.s;
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
    if (maxOff < 2e-4 && maxV < 2e-5) { this.snap(); return false; }
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
  const I = attribute("sbI", "vec4"), Wt = attribute("sbW", "vec4");
  const off = (f: typeof I.x) => {
    const row = floor(f.div(TEX_W));
    return textureLoad(offsets, ivec2(int(f.sub(row.mul(TEX_W))), int(row))).xyz;
  };
  return positionLocal.add(off(I.x).mul(Wt.x)).add(off(I.y).mul(Wt.y)).add(off(I.z).mul(Wt.z)).add(off(I.w).mul(Wt.w));
}
