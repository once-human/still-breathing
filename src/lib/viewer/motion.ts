// The person who wears the tee is alive, not a statue: they breathe, their weight drifts from foot to foot, the
// head turns a little now and then, the arms hang loose and swing a touch, the hands ease. Slowly, and small (a
// few degrees at most), the way someone stands at a show between songs.
//
// pipeline/human.py gives every vertex of the person five weights from the rig's own skin weights (how much it
// follows the breath, the head, its arm from the shoulder, its forearm from the elbow, its hand from the wrist;
// left or right is the sign of x) and puts the joints in the GLB. Here the angles are worked out once a frame on
// the CPU and the vertex shader turns each vertex about those joints, child before parent (hand, forearm, arm,
// head), then the breath, then the whole body over the feet. The tee moves with the body under it: each of its
// vertices takes the weights of the nearest point of the body (not of a forearm or hand, so a hand by the hem
// doesn't drag the hem), so it breathes and sways with them and the live cloth moves on top of that.
// For photos (the path tracer's still) and for anyone who asks for less motion, everything eases to the rest
// pose the tee was simulated in.
import * as THREE from "three/webgpu";
import { attribute, uniform, vec3, float, cos, sin, cross, dot, select } from "three/tsl";

export const MOTION_ATTRS = ["_breath", "_head", "_arm", "_fore", "_hand"] as const;
type V = THREE.Node<"vec3">;
type F = THREE.Node<"float">;
type Joints = Record<string, [number, number, number]>;

/** rotate p about the line through c along the unit axis k by angle a (Rodrigues) */
function turn(p: V, c: V, k: V, a: F): V {
  const v = p.sub(c), ca = cos(a), sa = sin(a);
  return c.add(v.mul(ca).add(cross(k, v).mul(sa)).add(k.mul(dot(k, v).mul(float(1).sub(ca)))));
}

export class Motion {
  private j = {
    neck: uniform(new THREE.Vector3()), feet: uniform(new THREE.Vector3()), chest: uniform(new THREE.Vector3()),
    shL: uniform(new THREE.Vector3()), shR: uniform(new THREE.Vector3()), elL: uniform(new THREE.Vector3()),
    elR: uniform(new THREE.Vector3()), wrL: uniform(new THREE.Vector3()), wrR: uniform(new THREE.Vector3()),
  };
  private a = {
    breath: uniform(0), yaw: uniform(0), pitch: uniform(0), side: uniform(0), fb: uniform(0),
    armL: uniform(0), armR: uniform(0), foreL: uniform(0), foreR: uniform(0), handL: uniform(0), handR: uniform(0),
    flexL: uniform(0), flexR: uniform(0),
  };
  private t = Math.random() * 60;
  private amp = 0;
  /** a person who carries the weights is on screen */
  on = false;
  /** wanted: alive (false: at rest, for photos and reduced motion) */
  live = true;

  /** the joints from the person GLB (glTF frame, metres); null: nobody, everything stays put */
  setJoints(m: Joints | null) {
    this.on = !!m;
    if (!m) { this.amp = 0; this.apply(); return; }
    const s = (u: { value: THREE.Vector3 }, k: string) => u.value.set(...(m[k] ?? [0, 0, 0]));
    s(this.j.neck, "neck"); s(this.j.feet, "feet");
    s(this.j.shL, "shoulder.L"); s(this.j.shR, "shoulder.R"); s(this.j.elL, "elbow.L"); s(this.j.elR, "elbow.R");
    s(this.j.wrL, "wrist.L"); s(this.j.wrR, "wrist.R");
    // the breath pushes out from the middle of the chest (between the shoulders, a hand's depth back)
    this.j.chest.value.set(0, 0, (this.j.shL.value.z + this.j.shR.value.z) / 2 - 0.02);
  }

  /** position node: p (the rest pose, or the cloth on it) moved as the person is, by this vertex's weights */
  node(p: V): V {
    const [wb, wh, wa, wf, wn] = MOTION_ATTRS.map((n) => attribute(n, "float"));
    const X = vec3(1, 0, 0), Y = vec3(0, 1, 0), Z = vec3(0, 0, 1);
    const left = p.x.greaterThan(0);
    const pick = (l: V, r: V): V => select(left, l, r);
    const pickF = (l: F, r: F): F => select(left, l, r);
    // the hand: it rocks forward and back at the wrist, and the palm eases in toward the thigh and out
    let q: V = turn(p, pick(this.j.wrL, this.j.wrR), Z, pickF(this.a.flexL, this.a.flexR).mul(wn));
    q = turn(q, pick(this.j.wrL, this.j.wrR), X, pickF(this.a.handL, this.a.handR).mul(wn));
    q = turn(q, pick(this.j.elL, this.j.elR), X, pickF(this.a.foreL, this.a.foreR).mul(wf));
    q = turn(q, pick(this.j.shL, this.j.shR), X, pickF(this.a.armL, this.a.armR).mul(wa));
    q = turn(q, this.j.neck, Y, this.a.yaw.mul(wh));
    q = turn(q, this.j.neck, X, this.a.pitch.mul(wh));
    // breath: the chest and belly out from the middle, the shoulders (and all above) a touch up
    const out = vec3(q.x.sub(this.j.chest.x), 0, q.z.sub(this.j.chest.z));
    const r = out.length().max(0.03);
    q = q.add(out.div(r).mul(this.a.breath.mul(wb).mul(0.0034))).add(Y.mul(this.a.breath.mul(wa.mul(0.9).add(wh.mul(0.7))).mul(0.0024)));
    // the whole body sways over the feet: side to side and a little front to back
    q = turn(q, this.j.feet, Z, this.a.side);
    return turn(q, this.j.feet, X, this.a.fb);
  }

  /**
   * The five weights as one vertex buffer (interleaved): WebGPU gives a mesh 8 vertex buffers, and the tee already
   * uses most of them (position, normal, uv, the cloth's two); five more of its own and it can't be drawn at all.
   */
  private static put(g: THREE.BufferGeometry, w: ArrayLike<number>[]) {
    const cnt = g.attributes.position.count, K = MOTION_ATTRS.length, data = new Float32Array(cnt * K);
    for (let i = 0; i < cnt; i++) for (let k = 0; k < K; k++) data[i * K + k] = w[k][i] ?? 0;
    const buf = new THREE.InterleavedBuffer(data, K);
    MOTION_ATTRS.forEach((nm, k) => g.setAttribute(nm, new THREE.InterleavedBufferAttribute(buf, 1, k)));
  }

  /** the weights in one buffer: the person's own (from its GLB, five separate ones), or zero for a mesh that has none */
  static ensure(g: THREE.BufferGeometry) {
    const a = MOTION_ATTRS.map((n) => g.getAttribute(n));
    if (a.every((x) => x && (x as THREE.InterleavedBufferAttribute).isInterleavedBufferAttribute)) return;
    const cnt = g.attributes.position.count;
    Motion.put(g, a.map((x) => {
      const o = new Float32Array(cnt);
      if (x) for (let i = 0; i < cnt; i++) o[i] = x.getX(i);
      return o;
    }));
  }

  /**
   * The tee's weights from the body under it: each vertex takes those of the nearest point of the body (pos and
   * weights in the same frame, `pos` the tee's vertices in it), never a forearm's or a hand's; the head only half (the
   * collar follows the neck a little).
   */
  static fromBody(g: THREE.BufferGeometry, pos: Float32Array, body: { pos: Float32Array; w: Float32Array[] }) {
    // the body's points (not forearms or hands) sorted into 1.5 cm cells of a box round them: a lookup is index sums
    const C = 0.015, n = body.pos.length / 3, P = body.pos;
    let x0 = Infinity, y0 = Infinity, z0 = Infinity, x1 = -Infinity, y1 = -Infinity, z1 = -Infinity;
    for (let i = 0; i < n; i++) {
      x0 = Math.min(x0, P[3 * i]); y0 = Math.min(y0, P[3 * i + 1]); z0 = Math.min(z0, P[3 * i + 2]);
      x1 = Math.max(x1, P[3 * i]); y1 = Math.max(y1, P[3 * i + 1]); z1 = Math.max(z1, P[3 * i + 2]);
    }
    const cnt = pos.length / 3, out = MOTION_ATTRS.map(() => new Float32Array(cnt));
    if (n) {
      const ox = Math.floor(x0 / C), oy = Math.floor(y0 / C), oz = Math.floor(z0 / C);
      const NX = Math.floor(x1 / C) - ox + 1, NY = Math.floor(y1 / C) - oy + 1, NZ = Math.floor(z1 / C) - oz + 1;
      const cellOf = new Int32Array(n).fill(-1), start = new Int32Array(NX * NY * NZ + 1);
      for (let i = 0; i < n; i++) {
        if (body.w[3][i] > 0.3 || body.w[4][i] > 0.3) continue;
        const c = ((Math.floor(P[3 * i] / C) - ox) * NY + (Math.floor(P[3 * i + 1] / C) - oy)) * NZ + (Math.floor(P[3 * i + 2] / C) - oz);
        cellOf[i] = c; start[c + 1]++;
      }
      for (let c = 0; c < NX * NY * NZ; c++) start[c + 1] += start[c];
      const fill = start.slice(0, -1), items = new Int32Array(start[NX * NY * NZ]);
      for (let i = 0; i < n; i++) if (cellOf[i] >= 0) items[fill[cellOf[i]]++] = i;
      for (let i = 0; i < cnt; i++) {
        const vx = pos[3 * i], vy = pos[3 * i + 1], vz = pos[3 * i + 2];
        const cx = Math.floor(vx / C) - ox, cy = Math.floor(vy / C) - oy, cz = Math.floor(vz / C) - oz;
        let best = -1, bd = Infinity;
        // the cells next to it; only if none of them holds a point, three cells further out
        for (let R = 1; R <= 4 && best < 0; R += 3) {
          for (let ix = Math.max(0, cx - R); ix <= Math.min(NX - 1, cx + R); ix++)
            for (let iy = Math.max(0, cy - R); iy <= Math.min(NY - 1, cy + R); iy++)
              for (let iz = Math.max(0, cz - R); iz <= Math.min(NZ - 1, cz + R); iz++) {
                const c = (ix * NY + iy) * NZ + iz;
                for (let q = start[c]; q < start[c + 1]; q++) {
                  const j = items[q], ex = P[3 * j] - vx, ey = P[3 * j + 1] - vy, ez = P[3 * j + 2] - vz, d = ex * ex + ey * ey + ez * ez;
                  if (d < bd) { bd = d; best = j; }
                }
              }
        }
        if (best < 0) continue;
        out[0][i] = body.w[0][best]; out[1][i] = body.w[1][best] * 0.5; out[2][i] = body.w[2][best];
      }
    }
    Motion.put(g, out);
  }

  /** advance; true while anything moves */
  step(dt: number) {
    const want = this.on && this.live ? 1 : 0;
    this.amp += (want - this.amp) * (1 - Math.exp(-dt / 0.8));
    if (want === 0 && this.amp < 1e-3) this.amp = 0;
    if (want) this.t += Math.min(dt, 0.1);
    this.apply();
    return this.amp > 0;
  }

  private apply() {
    const t = this.t, k = this.amp, TAU = Math.PI * 2, w = (p: number, ph = 0) => Math.sin((TAU * t) / p + ph);
    // breathing in is quicker than breathing out: a rise over 40 % of the 4.3 s cycle, the fall over the rest
    const ph = (t / 4.3) % 1, br = ph < 0.4 ? 0.5 - 0.5 * Math.cos((Math.PI * ph) / 0.4) : 0.5 + 0.5 * Math.cos((Math.PI * (ph - 0.4)) / 0.6);
    const A = this.a;
    A.breath.value = k * br;
    // the weight drifts from foot to foot (about a centimetre and a half at the head) and a little back and forth
    A.side.value = k * (0.0075 * w(11.3, 0.3) + 0.0028 * w(6.7, 1.1));
    A.fb.value = k * 0.0042 * w(8.3, 2.0);
    A.yaw.value = k * (0.034 * w(9.7) + 0.02 * w(15.3, 1.0));
    A.pitch.value = k * (0.012 * w(7.1, 0.5) + 0.006 * w(12.9, 2.2));
    // the arms swing a little against the sway, each its own way; forearms and hands loosely after them
    // (a hand moves about a centimetre; the fingers stay as they hang, curled)
    A.armL.value = k * 0.017 * w(6.1, 0.4) - 0.6 * A.side.value;
    A.armR.value = k * 0.015 * w(5.6, 2.1) + 0.6 * A.side.value;
    A.foreL.value = k * (0.026 * w(5.3, 1.3) + 0.008 * w(2.9, 0.7)); A.foreR.value = k * (0.022 * w(4.9, 3.0) + 0.007 * w(3.1, 1.9));
    A.handL.value = k * (0.04 * w(4.7, 0.2) + 0.012 * w(2.3, 1.4)); A.handR.value = k * (0.034 * w(4.1, 2.6) + 0.01 * w(2.6, 0.3));
    A.flexL.value = k * (0.045 * w(7.9, 1.7) + 0.015 * w(3.3, 0.6)); A.flexR.value = k * (0.04 * w(8.6, 0.1) + 0.014 * w(3.7, 2.4));
  }
}
