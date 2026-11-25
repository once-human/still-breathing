// The wind over the table, and what it carries. It blows in from the right, hard: a strong flow that never quite
// settles, and gusts on top of it. Each gust is a front of faster air that sweeps across the table at the air's
// own speed, so whatever lies upwind moves first and the rest follow as it passes. The air is slower right at the
// boards and the cotton, faster a few cm up.
// Things move only because of it, by real physics: drag from the air rushing past them (as the square of that
// speed), gravity against their own falling speed, lift that comes and goes as they flutter and tumble, and
// friction holding them on the surface until the air beats it. A leaf slides, hops, lifts off in a gust, flutters
// and turns over and lands somewhere downwind. One that lands on the tee rests a moment at most (some never settle)
// and the next gust moves it on; nothing stays long, so the table never fills up however long it runs.
// All of it in the table's frame (metres, z up off the table).
import * as THREE from "three/webgpu";
import { texture, uv, vec2, vec4, attribute, normalMap } from "three/tsl";
import { KINDS, LEAF_CELLS, type Kind } from "./things";
import { bitmap } from "./grab";

const R = (lo: number, hi: number) => lo + (hi - lo) * Math.random();
const TAU = Math.PI * 2;
const G = 9.81;
const Z = new THREE.Vector3(0, 0, 1);
/** the wind's direction: from the right-hand edge toward the left */
const FROM_RIGHT = Math.PI;

type Gust = { s: number; amp: number; w: number; lat: number; ph: number };

/** the wind: a strong mean flow that wanders, and gust fronts travelling across the table on it */
export class Wind {
  /** the mean flow, 0 a lull .. 1 a hard wind */
  level = 0.6;
  /** radians in the table's plane; π blows right to left */
  dir = FROM_RIGHT;
  private goal = 0.6;
  private tau = 1;
  private next = 0;
  private dgoal = FROM_RIGHT;
  private t = 0;
  private gusts: Gust[] = [];
  private nextGust = 0;

  /** the air's speed a few cm above the table for a level, m/s */
  static speed(l: number) { return 0.35 + 1.75 * l; }

  step(dt: number) {
    this.t += dt;
    if (this.t >= this.next) {
      // mostly a steady hard wind, often harder, now and then a short lull
      const r = Math.random();
      this.goal = r < 0.55 ? R(0.45, 0.8) : r < 0.8 ? R(0.8, 1) : R(0.12, 0.3);
      this.tau = R(0.4, 1.4);
      this.next = this.t + (this.goal < 0.3 ? R(0.8, 2.5) : R(1.2, 4));
      // always from the right; only the faintest wander in its line
      this.dgoal = FROM_RIGHT + R(-0.06, 0.06);
    }
    this.level += (this.goal - this.level) * (1 - Math.exp(-dt / this.tau));
    let dd = this.dgoal - this.dir; dd = Math.atan2(Math.sin(dd), Math.cos(dd));
    this.dir += dd * (1 - Math.exp(-dt / 3));
    // gust fronts: born upwind, carried across at a little over the mean speed, gone downwind
    if (this.t >= this.nextGust) {
      this.gusts.push({ s: -1, amp: R(0.25, 0.85), w: R(0.12, 0.4), lat: R(2, 7), ph: R(0, TAU) });
      this.nextGust = this.t + R(0.25, 1.6) / (0.4 + this.level);
    }
    const c = Wind.speed(this.level) * 1.1;
    for (const g of this.gusts) g.s += c * dt;
    this.gusts = this.gusts.filter((g) => g.s < 1.2);
    return Math.min(1.2, this.at(0, 0));
  }

  /** the wind's strength here, the mean flow plus whatever gust is passing (can go a little over 1) */
  at(x: number, y: number) {
    const cd = Math.cos(this.dir), sd = Math.sin(this.dir);
    const s = x * cd + y * sd, n = -x * sd + y * cd;      // along the wind, across it
    let l = this.level * 0.75;
    for (const g of this.gusts) {
      const d = (s - g.s) / g.w;
      if (d * d < 9) l += g.amp * Math.exp(-d * d) * (0.65 + 0.35 * Math.sin(n * g.lat + g.ph));
    }
    return l;
  }
}

/** turbulence: smooth, never-repeating, fast enough to read as wind */
const swirl = (x: number, y: number, t: number, ph: number) => [
  Math.sin(y * 9.1 + t * 2.3 + ph) * 0.6 + Math.sin((x + y) * 6.3 - t * 3.7 + ph * 1.7) * 0.4,
  Math.sin(x * 8.3 - t * 2.9 + ph * 2.3) * 0.6 + Math.sin((x - y) * 5.1 + t * 4.1 + ph * 0.6) * 0.4,
  Math.sin(x * 7.7 + y * 5.3 + t * 5.3 + ph * 1.3),
];

export class Air {
  group = new THREE.Group();
  private t = 0;
  private things: Thing[] = [];
  private nextThing = 0;
  private mats: { leaf: THREE.MeshStandardNodeMaterial; solid: THREE.MeshStandardNodeMaterial; soft: THREE.MeshStandardNodeMaterial } | null = null;
  private q = new THREE.Quaternion();
  private q2 = new THREE.Quaternion();
  private v2 = new THREE.Vector3();
  private v = new THREE.Vector3();
  private s = new THREE.Vector3();

  constructor(private aniso: number) {}

  /** the things' pictures: the leaf scans, and the atlas of the rest (lib/viewer/things.ts says which is which) */
  async init() {
    if (this.mats) return;
    const tx = async (name: string, srgb: boolean) => {
      const t = new THREE.Texture(await bitmap(`/tee/table/${name}`));
      t.flipY = false; t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace; t.anisotropy = this.aniso; t.needsUpdate = true;
      return t;
    };
    const [lc, ln, bc] = await Promise.all([tx("leaves.webp", true), tx("leaves-n.webp", false), tx("bits.webp", true)]);
    const cell = attribute("cell", "vec2"), tint = attribute("tint", "vec3");
    // leaves: the scan's colour and relief, cut out by its own edge (the cut casts the shadow)
    const leaf = new THREE.MeshStandardNodeMaterial({ roughness: 0.78, metalness: 0, side: THREE.DoubleSide });
    const luv = uv().mul(vec2(0.25, 0.25)).add(cell), lcol = texture(lc, luv);
    leaf.colorNode = vec4(lcol.rgb, 1); leaf.maskNode = lcol.a.greaterThan(0.5); leaf.normalNode = normalMap(texture(ln, luv).rgb);
    // thread and hair cut out and casting shadows; fluff and a seed's parachute see-through, too fine to throw
    // more than a haze of shadow
    const buv = uv().mul(vec2(0.25, 1 / 3)).add(cell), bcol = texture(bc, buv);
    const solid = new THREE.MeshStandardNodeMaterial({ roughness: 0.85, metalness: 0, side: THREE.DoubleSide });
    solid.colorNode = vec4(bcol.rgb.mul(tint), 1); solid.maskNode = bcol.a.greaterThan(0.45);
    const soft = new THREE.MeshStandardNodeMaterial({ roughness: 0.9, metalness: 0, side: THREE.DoubleSide, transparent: true, depthWrite: false });
    soft.colorNode = vec4(bcol.rgb.mul(tint), bcol.a);
    // drawn a hair toward the lens, so where one lies touching the cotton or the boards it is never cut by them
    for (const m of [leaf, solid, soft]) { m.polygonOffset = true; m.polygonOffsetFactor = -1; m.polygonOffsetUnits = -4; }
    this.mats = { leaf, solid, soft };
  }

  /** something comes in on the wind (or, at the start, is already lying about) */
  private spawn(wind: Wind, lying = false) {
    if (!this.mats) return;
    const kind = pick();
    const g = new THREE.PlaneGeometry(1, 1, kind.curl ? 14 : 1, kind.curl ? 8 : 1), p = g.attributes.position;
    let zmin = 0, zmax = 0;
    if (kind.curl) {
      // cupped across, the ends lifting: nothing that has dried flat stays flat
      const cup = R(0.03, kind.curl), arch = R(-0.04, kind.curl * 0.7);
      for (let i = 0; i < p.count; i++) {
        const x = p.getX(i), y = p.getY(i), z = cup * (y * 2) ** 2 * 0.5 + arch * (x * 2) ** 2 * 0.5;
        p.setZ(i, z); zmin = Math.min(zmin, z); zmax = Math.max(zmax, z);
      }
      g.computeVertexNormals();
    }
    const cellIx = kind.cells[Math.floor(Math.random() * kind.cells.length)];
    const cx = (cellIx % 4) * 0.25, cy = kind.atlas === "leaf" ? Math.floor(cellIx / 4) * 0.25 : Math.floor(cellIx / 4) / 3;
    const tint = kind.tints ? kind.tints[Math.floor(Math.random() * kind.tints.length)] : [1, 1, 1];
    const cell = new Float32Array(p.count * 2), tn = new Float32Array(p.count * 3);
    for (let i = 0; i < p.count; i++) { cell[2 * i] = cx; cell[2 * i + 1] = cy; tn.set(tint, 3 * i); }
    g.setAttribute("cell", new THREE.BufferAttribute(cell, 2)); g.setAttribute("tint", new THREE.BufferAttribute(tn, 3));
    const mat = kind.atlas === "leaf" ? this.mats.leaf : kind.soft ? this.mats.soft : this.mats.solid;
    const mesh = new THREE.Mesh(g, mat);
    mesh.castShadow = !kind.soft; mesh.receiveShadow = true; mesh.frustumCulled = false; mesh.matrixAutoUpdate = false;
    mesh.renderOrder = kind.soft ? 4 : 0;
    const size = (kind.atlas === "leaf" ? LEAF_CELLS[cellIx] / 100 : R(kind.size[0], kind.size[1])) * R(0.88, 1.12);
    // in from upwind, just out of the widest view, anywhere along that edge, already moving with the air;
    // at the start, a few lying in view
    const cd = Math.cos(wind.dir), sd = Math.sin(wind.dir), side = R(-0.45, 0.45);
    const x = lying ? R(-0.32, 0.32) : -cd * 0.6 - sd * side;
    const y = lying ? R(-0.38, 0.38) : -sd * 0.6 + cd * side;
    const u = lying ? 0 : Wind.speed(wind.at(x, y)) * R(0.4, 0.8);
    const T: Thing = {
      kind, mesh, size, x, y, h: lying ? 0 : R(0.004, kind.move === "float" ? 0.08 : 0.05),
      vx: cd * u, vy: sd * u, vh: 0, yaw: R(0, TAU), vyaw: R(-2, 2), tip: R(0, TAU),
      pitch: Math.random() < 0.5 ? 0 : Math.PI, pv: 0, auto: 0, zmin, zmax,
      grip: R(kind.grip[0], kind.grip[1]), rest: 0, restMax: -1, ph: R(0, 100),
    };
    this.things.push(T); this.group.add(mesh);
  }

  /** one step of the air; `over(x, y)` is how high the cotton is there (m), for what lands on the tee */
  step(dt: number, wind: Wind, over: (x: number, y: number) => number) {
    dt = Math.min(dt, 1 / 30);
    this.t += dt;
    // things: in on the wind, more in a gust, never a crowd
    const W = wind.level;
    if (this.t > this.nextThing) {
      if (this.things.length < 10) this.spawn(wind);
      this.nextThing = this.t - Math.log(1 - Math.random()) / (0.25 + 1.3 * W * W);
    }
    for (const T of this.things) this.move(T, dt, wind, over);
    this.things = this.things.filter((T) => {
      if (Math.abs(T.x) < 0.75 && Math.abs(T.y) < 0.8) return true;
      this.group.remove(T.mesh); T.mesh.geometry.dispose();
      return false;
    });
  }

  /** the highest the surface comes under it: a leaf rests on the ridges of a crease, not in the trough */
  private floorUnder(T: Thing, over: (x: number, y: number) => number) {
    const r = T.size * 0.38, c = Math.cos(T.yaw) * r, s = Math.sin(T.yaw) * r;
    const top = Math.max(over(T.x, T.y), over(T.x + c, T.y + s), over(T.x - c, T.y - s), over(T.x - s, T.y + c), over(T.x + s, T.y - c));
    // on the tee the cotton itself rises and settles in the wind: keep clear of the highest it goes
    return top + 0.0012 + (top > 0.0004 ? 0.004 : 0);
  }

  private move(T: Thing, dt: number, wind: Wind, over: (x: number, y: number) => number) {
    const K = T.kind, v = this.v, s = this.s;
    const floor = this.floorUnder(T, over), onTee = floor > 0.004;
    const above = Math.max(0, T.h - floor), down = above < 0.0008;
    const cd = Math.cos(wind.dir), sd = Math.sin(wind.dir);
    // the air right here: the gusting wind, a little torn up by turbulence, slower at the surface
    const sw = swirl(T.x, T.y, this.t, T.ph);
    const l = wind.at(T.x, T.y);
    const dir = wind.dir + 0.1 * sw[0];
    const U = Wind.speed(l) * (1 + 0.22 * sw[1]) * (0.5 + 0.5 * Math.min(1, above / 0.04));
    const rx = Math.cos(dir) * U - T.vx, ry = Math.sin(dir) * U - T.vy, rel = Math.hypot(rx, ry);
    // how it sits to the air: tilted, it catches more of it (drag) and the air under its raised edge lifts it
    const base = Math.round(T.pitch / Math.PI) * Math.PI;
    // (turning it further about the cross-wind line raises its upwind edge whichever side it lies on)
    const tilt = Math.abs(Math.sin(T.pitch)), up = Math.max(0, Math.sin(T.pitch - base));
    const kd = K.drag * K.catch * (0.45 + 0.55 * tilt);
    let ax = kd * rel * rx, ay = kd * rel * ry;
    let lift = K.lift * rel * rel * (0.2 + 1.6 * up) + 0.3 * sw[2] * l * K.lift;
    let target: number;
    if (down) {
      // on the surface: friction holds it; as the air builds its upwind edge lifts and trembles, then it slides,
      // and a gust under that raised edge throws it up
      const fx = Math.hypot(ax, ay), mu = T.grip * G, vs = Math.hypot(T.vx, T.vy);
      const strain = Math.min(1, fx / mu);
      target = base + strain * strain * 0.32 * K.tumble;
      if (vs < 0.01 && fx < mu) { ax = 0; ay = 0; T.vx = 0; T.vy = 0; }
      else if (vs > 0) { ax -= (T.vx / vs) * mu * 0.7; ay -= (T.vy / vs) * mu * 0.7; }
      T.pv += (Math.random() - 0.5) * strain * rel * 60 * dt;          // the tremble of an edge in the wind
      if (lift > G * (1 + T.grip)) {
        T.vh = (lift - G) * 0.03;
        // some take off spinning over and over, the rest rock and glide
        T.auto = rel > 0.7 && Math.random() < 0.4 * K.tumble ? (Math.random() < 0.5 ? -1 : 1) : 0;
      } else T.vh = 0;
    } else {
      // in the air: it swings like a falling leaf does, gliding toward its low edge on each swing, lift coming
      // and going with the swing; or, in a strong flow, autorotates; it falls against its own drag
      target = base + Math.sin(T.tip) * 0.6 * K.tumble;
      const glide = Math.sin(T.pitch) * Math.cos(T.pitch) * G * 0.55 * K.tumble;
      ax += cd * glide; ay += sd * glide;
      lift += Math.abs(Math.cos(T.tip)) * rel * K.lift * 0.15;
      T.vh += (lift - G - (G / (K.fall * K.fall)) * Math.abs(T.vh) * T.vh) * dt;
      if (rel < 0.35) T.auto = 0;
    }
    if (T.auto && !down) T.pv += (T.auto * rel * K.tumble * 10 - T.pv) * 4 * dt;
    else T.pv += (140 * (target - T.pitch) - 13 * T.pv) * dt;
    T.pitch += T.pv * dt;
    T.vx += ax * dt; T.vy += ay * dt;
    // resting: a moment on the tee at most (some never settle there), longer on the boards; then the air under it
    // picks it up again
    const speed = Math.hypot(T.vx, T.vy);
    if (down && speed < 0.01) {
      if (T.restMax < 0) T.restMax = onTee ? (Math.random() < 0.35 ? R(0.05, 0.3) : R(0.6, 5)) : R(1.5, 9);
      T.rest += dt;
      if (T.rest > T.restMax) {
        const kick = wind.dir + R(-0.25, 0.25), m = R(0.3, 0.8) * K.catch;
        T.vx += Math.cos(kick) * m; T.vy += Math.sin(kick) * m; T.vh += K.move === "creep" ? 0 : R(0.2, 0.6);
        T.pv += R(4, 10);
        T.rest = 0; T.restMax = -1;
      }
    } else { T.rest = 0; T.restMax = -1; }
    T.x += T.vx * dt; T.y += T.vy * dt; T.h += T.vh * dt;
    if (T.h <= floor) {
      // touching down: a little bounce if it came in fast, and it settles flat on whichever side it landed
      T.h = floor; T.vh = T.vh < -0.4 ? -T.vh * 0.15 : 0;
      if (T.auto) { T.auto = 0; T.pv *= 0.3; }
    }
    if (T.h > 0.14) { T.h = 0.14; T.vh = Math.min(T.vh, 0); }
    // turning: in the air the flow swings it round and the swing quickens with the air rushing past; sliding it
    // turns slowly as its edges catch
    T.vyaw += ((sw[1] * 5 + (Math.random() - 0.5) * 7) * rel * K.spin * (down ? 0.5 : 1) - T.vyaw * 2.4) * dt; T.yaw += T.vyaw * dt;
    T.tip += dt * (3 + rel * 6) * (down ? 0.2 : 1);
    // its pose: the tilt about the line across the wind, then its own turn; lifted so the lowest point of its curl
    // and its tilted edge clear the surface
    const ax2 = this.v2.set(-sd, cd, 0);
    this.q.setFromAxisAngle(ax2, T.pitch).multiply(this.q2.setFromAxisAngle(Z, T.yaw));
    const cp = Math.cos(T.pitch);
    const low = (cp >= 0 ? T.zmin : -T.zmax) * Math.abs(cp) - Math.abs(Math.sin(T.pitch)) * 0.5;
    v.set(T.x, T.y, T.h - low * T.size); s.set(T.size, T.size, T.size);
    T.mesh.matrix.compose(v, this.q, s); T.mesh.matrixWorldNeedsUpdate = true;
  }

  /** a fresh table: a thing or two already lying about, more on the way */
  reset(wind: Wind) {
    for (const T of this.things) { this.group.remove(T.mesh); T.mesh.geometry.dispose(); }
    this.things = [];
    for (let i = Math.floor(R(1, 3.99)); i > 0; i--) this.spawn(wind, true);
    this.nextThing = this.t + R(0.2, 1);
  }
}

type Thing = {
  kind: Kind; mesh: THREE.Mesh; size: number; x: number; y: number; h: number; vx: number; vy: number; vh: number;
  yaw: number; vyaw: number; tip: number; grip: number; rest: number; restMax: number; ph: number;
  /** its tilt about the line across the wind (0 or π lying flat on one side or the other), how fast that turns,
   *  whether it's autorotating (spinning over and over in a strong flow: -1, 0, 1), and how far its curl reaches
   *  below and above its middle (in its own size) */
  pitch: number; pv: number; auto: number; zmin: number; zmax: number;
};
const pick = () => {
  let r = Math.random() * KINDS.reduce((a, k) => a + k.weight, 0);
  for (const k of KINDS) { r -= k.weight; if (r <= 0) return k; }
  return KINDS[0];
};
