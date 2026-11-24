// Binned-SAH bounding volume hierarchy for the path tracer, built off the main thread.
// buildBVH is written as one self-contained plain function (no imports, no closures) because it is
// shipped to a Worker as source text.

export type BVH = {
  /** 8 x 32-bit per node: min.xyz, leftOrFirst (u32), max.xyz, count (u32). count > 0 = leaf. */
  nodes: ArrayBuffer;
  nodeCount: number;
  /** triangle indices in leaf order */
  order: Uint32Array;
};

export function buildBVH(pos: Float32Array, idx: Uint32Array) {
  const n = idx.length / 3;
  const cx = new Float32Array(n), cy = new Float32Array(n), cz = new Float32Array(n);
  const b0 = new Float32Array(n * 3), b1 = new Float32Array(n * 3);
  for (let t = 0; t < n; t++) {
    let mnx = Infinity, mny = Infinity, mnz = Infinity, mxx = -Infinity, mxy = -Infinity, mxz = -Infinity;
    for (let k = 0; k < 3; k++) {
      const v = idx[t * 3 + k] * 3, x = pos[v], y = pos[v + 1], z = pos[v + 2];
      if (x < mnx) mnx = x; if (y < mny) mny = y; if (z < mnz) mnz = z;
      if (x > mxx) mxx = x; if (y > mxy) mxy = y; if (z > mxz) mxz = z;
    }
    b0[t * 3] = mnx; b0[t * 3 + 1] = mny; b0[t * 3 + 2] = mnz;
    b1[t * 3] = mxx; b1[t * 3 + 1] = mxy; b1[t * 3 + 2] = mxz;
    cx[t] = (mnx + mxx) * 0.5; cy[t] = (mny + mxy) * 0.5; cz[t] = (mnz + mxz) * 0.5;
  }
  const order = new Uint32Array(n);
  for (let i = 0; i < n; i++) order[i] = i;
  const maxNodes = 2 * n;
  const buf = new ArrayBuffer(maxNodes * 32);
  const f = new Float32Array(buf), u = new Uint32Array(buf);
  let used = 1;
  const BINS = 16;
  const binN = new Uint32Array(BINS), binB = new Float32Array(BINS * 6);
  const leftA = new Float32Array(BINS), leftN = new Uint32Array(BINS);
  const stack = [0], sFirst = [0], sCount = [n];
  while (stack.length) {
    const node = stack.pop() as number, first = sFirst.pop() as number, count = sCount.pop() as number;
    let mnx = Infinity, mny = Infinity, mnz = Infinity, mxx = -Infinity, mxy = -Infinity, mxz = -Infinity;
    let cmnx = Infinity, cmny = Infinity, cmnz = Infinity, cmxx = -Infinity, cmxy = -Infinity, cmxz = -Infinity;
    for (let i = first; i < first + count; i++) {
      const t = order[i], o = t * 3;
      if (b0[o] < mnx) mnx = b0[o]; if (b0[o + 1] < mny) mny = b0[o + 1]; if (b0[o + 2] < mnz) mnz = b0[o + 2];
      if (b1[o] > mxx) mxx = b1[o]; if (b1[o + 1] > mxy) mxy = b1[o + 1]; if (b1[o + 2] > mxz) mxz = b1[o + 2];
      if (cx[t] < cmnx) cmnx = cx[t]; if (cy[t] < cmny) cmny = cy[t]; if (cz[t] < cmnz) cmnz = cz[t];
      if (cx[t] > cmxx) cmxx = cx[t]; if (cy[t] > cmxy) cmxy = cy[t]; if (cz[t] > cmxz) cmxz = cz[t];
    }
    const o8 = node * 8;
    f[o8] = mnx; f[o8 + 1] = mny; f[o8 + 2] = mnz; f[o8 + 4] = mxx; f[o8 + 5] = mxy; f[o8 + 6] = mxz;
    const leaf = () => { u[o8 + 3] = first; u[o8 + 7] = count; };
    if (count <= 2) { leaf(); continue; }
    // best split over all three axes
    let bestCost = Infinity, bestAxis = -1, bestBin = 0;
    const cmin = [cmnx, cmny, cmnz], cmax = [cmxx, cmxy, cmxz], cs = [cx, cy, cz];
    for (let a = 0; a < 3; a++) {
      const lo = cmin[a], ext = cmax[a] - lo;
      if (ext < 1e-9) continue;
      const scale = BINS / ext, c = cs[a];
      binN.fill(0);
      for (let k = 0; k < BINS; k++) { binB[k * 6] = binB[k * 6 + 1] = binB[k * 6 + 2] = Infinity; binB[k * 6 + 3] = binB[k * 6 + 4] = binB[k * 6 + 5] = -Infinity; }
      for (let i = first; i < first + count; i++) {
        const t = order[i], o = t * 3;
        let k = Math.floor((c[t] - lo) * scale); if (k >= BINS) k = BINS - 1;
        binN[k]++; const q = k * 6;
        if (b0[o] < binB[q]) binB[q] = b0[o]; if (b0[o + 1] < binB[q + 1]) binB[q + 1] = b0[o + 1]; if (b0[o + 2] < binB[q + 2]) binB[q + 2] = b0[o + 2];
        if (b1[o] > binB[q + 3]) binB[q + 3] = b1[o]; if (b1[o + 1] > binB[q + 4]) binB[q + 4] = b1[o + 1]; if (b1[o + 2] > binB[q + 5]) binB[q + 5] = b1[o + 2];
      }
      // sweep left to right, then right to left
      let ax = Infinity, ay = Infinity, az = Infinity, bx = -Infinity, by = -Infinity, bz = -Infinity, cnt = 0;
      for (let k = 0; k < BINS - 1; k++) {
        const q = k * 6;
        if (binN[k]) {
          cnt += binN[k];
          if (binB[q] < ax) ax = binB[q]; if (binB[q + 1] < ay) ay = binB[q + 1]; if (binB[q + 2] < az) az = binB[q + 2];
          if (binB[q + 3] > bx) bx = binB[q + 3]; if (binB[q + 4] > by) by = binB[q + 4]; if (binB[q + 5] > bz) bz = binB[q + 5];
        }
        leftN[k] = cnt;
        const dx = bx - ax, dy = by - ay, dz = bz - az;
        leftA[k] = cnt ? dx * dy + dy * dz + dz * dx : 0;
      }
      ax = Infinity; ay = Infinity; az = Infinity; bx = -Infinity; by = -Infinity; bz = -Infinity; cnt = 0;
      for (let k = BINS - 1; k > 0; k--) {
        const q = k * 6;
        if (binN[k]) {
          cnt += binN[k];
          if (binB[q] < ax) ax = binB[q]; if (binB[q + 1] < ay) ay = binB[q + 1]; if (binB[q + 2] < az) az = binB[q + 2];
          if (binB[q + 3] > bx) bx = binB[q + 3]; if (binB[q + 4] > by) by = binB[q + 4]; if (binB[q + 5] > bz) bz = binB[q + 5];
        }
        const dx = bx - ax, dy = by - ay, dz = bz - az;
        const rA = cnt ? dx * dy + dy * dz + dz * dx : 0;
        const cost = leftN[k - 1] * leftA[k - 1] + cnt * rA;
        if (leftN[k - 1] && cnt && cost < bestCost) { bestCost = cost; bestAxis = a; bestBin = k; }
      }
    }
    const dx = mxx - mnx, dy = mxy - mny, dz = mxz - mnz;
    const parentCost = count * (dx * dy + dy * dz + dz * dx);
    if (bestAxis < 0 || (bestCost >= parentCost && count <= 8)) { leaf(); continue; }
    // partition
    const lo = cmin[bestAxis], scale = BINS / (cmax[bestAxis] - lo), c = cs[bestAxis];
    let i = first, j = first + count - 1;
    while (i <= j) {
      let k = Math.floor((c[order[i]] - lo) * scale); if (k >= BINS) k = BINS - 1;
      if (k < bestBin) i++;
      else { const tmp = order[i]; order[i] = order[j]; order[j] = tmp; j--; }
    }
    const nl = i - first;
    if (nl === 0 || nl === count) { leaf(); continue; }
    const left = used; used += 2;
    u[o8 + 3] = left; u[o8 + 7] = 0;
    stack.push(left + 1, left); sFirst.push(i, first); sCount.push(count - nl, nl);
  }
  return { nodes: buf.slice(0, used * 32), nodeCount: used, order };
}

/** Runs buildBVH in a Worker so the page never stalls while a 250k-triangle tee is indexed. */
export function buildBVHAsync(pos: Float32Array, idx: Uint32Array): Promise<BVH> {
  const src = `const buildBVH = ${buildBVH.toString()};
onmessage = (e) => { const r = buildBVH(e.data.pos, e.data.idx); postMessage(r, [r.nodes, r.order.buffer]); };`;
  const url = URL.createObjectURL(new Blob([src], { type: "text/javascript" }));
  const w = new Worker(url);
  return new Promise((resolve, reject) => {
    w.onmessage = (e) => { resolve(e.data as BVH); w.terminate(); URL.revokeObjectURL(url); };
    w.onerror = (e) => { reject(e); w.terminate(); URL.revokeObjectURL(url); };
    w.postMessage({ pos, idx });
  });
}
