// The place's picture as light from all round: projected once onto spherical harmonics (three.js's basis and
// order), then turned with the place each frame by a 3 x 3 and a 5 x 5 matrix instead of a pass over the picture.
// No three.js import: pure numbers, cheap enough to run every frame.

/** three.js SphericalHarmonics3.getBasisAt, into out[0..8] */
function basis(x: number, y: number, z: number, out: Float64Array) {
  out[0] = 0.282095;
  out[1] = 0.488603 * y; out[2] = 0.488603 * z; out[3] = 0.488603 * x;
  out[4] = 1.092548 * x * y; out[5] = 1.092548 * y * z; out[6] = 0.315392 * (3 * z * z - 1);
  out[7] = 1.092548 * x * z; out[8] = 0.546274 * (x * x - y * y);
}

/**
 * Coefficients (9 x rgb, flat) of a W x H equirect of linear radiance, rows from straight up, with the place
 * unturned. Same convention as the viewer: u = 0.5 - atan2(x, z) / 2pi, so texel i looks along
 * a = (0.5 - (i + 0.5) / W) * 2pi, (sin a cos lat, sin lat, cos a cos lat).
 */
export function projectEnv(pix: Float32Array, W: number, H: number) {
  const c = new Float64Array(27), b = new Float64Array(9), dw = (2 * Math.PI / W) * (Math.PI / H);
  for (let j = 0; j < H; j++) {
    const lat = Math.PI / 2 - ((j + 0.5) / H) * Math.PI, cl = Math.cos(lat), y = Math.sin(lat), dO = dw * cl;
    for (let i = 0; i < W; i++) {
      const a = (0.5 - (i + 0.5) / W) * 2 * Math.PI;
      basis(Math.sin(a) * cl, y, Math.cos(a) * cl, b);
      const o = (j * W + i) * 3;
      for (let k = 0; k < 9; k++) {
        const w = b[k] * dO;
        c[3 * k] += pix[o] * w; c[3 * k + 1] += pix[o + 1] * w; c[3 * k + 2] += pix[o + 2] * w;
      }
    }
  }
  return c;
}

// A band of SH is closed under rotation, so its turned coefficients are fixed by the turned function's values at
// as many directions as the band has members: solve once for these directions, then each turn is a small product.
const DIRS = [[1, 0.3, 0.2], [-0.4, 1, 0.5], [0.2, -0.6, 1], [0.7, 0.7, -0.1], [-0.5, -0.3, -0.8]].map(([x, y, z]) => {
  const l = Math.hypot(x, y, z); return [x / l, y / l, z / l];
});
function invert(m: number[][]) {
  const n = m.length, a = m.map((r, i) => [...r, ...Array.from({ length: n }, (_, j) => (i === j ? 1 : 0))]);
  for (let c = 0; c < n; c++) {
    let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(a[r][c]) > Math.abs(a[p][c])) p = r;
    [a[c], a[p]] = [a[p], a[c]];
    const d = a[c][c]; for (let k = 0; k < 2 * n; k++) a[c][k] /= d;
    for (let r = 0; r < n; r++) if (r !== c) { const f = a[r][c]; for (let k = 0; k < 2 * n; k++) a[r][k] -= f * a[c][k]; }
  }
  return a.map((r) => r.slice(n));
}
const BANDS = [{ k0: 1, n: 3 }, { k0: 4, n: 5 }].map(({ k0, n }) => {
  const b = new Float64Array(9);
  const A = DIRS.slice(0, n).map(([x, y, z]) => { basis(x, y, z, b); return Array.from(b.slice(k0, k0 + n)); });
  return { k0, n, inv: invert(A) };
});

/**
 * The coefficients with the place turned by yaw about the vertical (a texel seen along p in the place is seen along
 * (cos p.x + sin p.z, p.y, -sin p.x + cos p.z) in the world), into out (9 x rgb, flat).
 */
export function turnSH(c: Float64Array, yaw: number, out: Float64Array) {
  const co = Math.cos(yaw), si = Math.sin(yaw), b = new Float64Array(9), rhs = new Float64Array(15);
  out[0] = c[0]; out[1] = c[1]; out[2] = c[2];
  for (const { k0, n, inv } of BANDS) {
    for (let i = 0; i < n; i++) {
      // the turned function at DIRS[i] is the unturned one at DIRS[i] turned back
      const [x, y, z] = DIRS[i];
      basis(co * x - si * z, y, si * x + co * z, b);
      let r = 0, g = 0, bl = 0;
      for (let k = 0; k < n; k++) { const w = b[k0 + k]; r += c[3 * (k0 + k)] * w; g += c[3 * (k0 + k) + 1] * w; bl += c[3 * (k0 + k) + 2] * w; }
      rhs[3 * i] = r; rhs[3 * i + 1] = g; rhs[3 * i + 2] = bl;
    }
    for (let k = 0; k < n; k++) {
      let r = 0, g = 0, bl = 0;
      for (let i = 0; i < n; i++) { const w = inv[k][i]; r += w * rhs[3 * i]; g += w * rhs[3 * i + 1]; bl += w * rhs[3 * i + 2]; }
      out[3 * (k0 + k)] = r; out[3 * (k0 + k) + 1] = g; out[3 * (k0 + k) + 2] = bl;
    }
  }
  return out;
}

/** the probe's picture: 64 x 32, linear, rows from straight up (made by the decoder worker, grab.ts) */
export const ENV_W = 64;
