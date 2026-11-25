// The air over the table, and what it carries, by real physics played in slow motion.
// The wind comes from the window on the right, never dead straight, and it has moods: it dies away to nothing,
// breezes, builds slowly or bursts in a puff; each puff is a front of faster air crossing the table, so whatever
// lies upwind feels it first. The air is slower right at the boards and the cotton, and faster higher up.
// Everything it carries has weight. A leaf lying still is held by friction: as the air builds its upwind edge
// lifts and shivers; when the push beats its grip it breaks loose, gathers speed (its inertia against the air's
// drag), skids and sticks and skids again as the push comes and goes, and a strong gust under its raised edge
// lifts it off. In the air it falls at its own speed, swinging, gliding toward its low edge, carried by the
// air's rise and fall; it lands, rocks, settles on whichever side came down. Now and then a new one drifts down
// from above the window side or skates in along the surface. One on the tee rests a moment at most (some never
// settle) and the air gets in under it again; only a few are ever about, however long it runs.
// The physics runs at real speeds and real forces (m/s, m/s², a dry leaf's drag and weight), slowed by TIME so
// the eye can follow it. All of it in the table's frame (metres, z up off the table).
import * as THREE from "three/webgpu";
import { texture, uv, vec2, vec3, vec4, attribute, normalMap, mix, uniform, normalWorld, max, dot } from "three/tsl";
import { KINDS, LEAF_CELLS, type Kind } from "./things";
import { picture } from "./pic";

const R = (lo: number, hi: number) => lo + (hi - lo) * Math.random();
const TAU = Math.PI * 2;
const G = 9.81;
const Z = new THREE.Vector3(0, 0, 1);
/** the slow motion everything in the air plays at */
const TIME = 0.3;
/** the wind's direction: from the right-hand edge toward the left */
const FROM_RIGHT = Math.PI;

type Gust = { s: number; amp: number; w: number; lat: number; ph: number };

/** the wind: a mean flow with moods (still, breeze, a slow build, a burst) and puffs crossing the table on it */
export class Wind {
  /** the mean flow, 0 still .. 1 a strong gust */
  level = 0.2;
  /** radians in the table's plane; π blows right to left */
  dir = FROM_RIGHT;
  private goal = 0.2;
  private tau = 2;
  private next = 0;
  private dgoal = FROM_RIGHT;
  private t = 0;
  private gusts: Gust[] = [];
  private nextGust = 0;
  private mood: "still" | "breeze" | "gust" = "breeze";

  /** the air's real speed a few cm above the table for a level, m/s */
  static speed(l: number) { return 0.2 + 2.3 * l; }

  /** dt in seconds as seen; the wind's moods change in that time, its puffs travel in slowed time */
  step(dt: number) {
    this.t += dt;
    if (this.t >= this.next) {
      // the next mood: after a gust it usually drops away; stillness and breeze take turns; a gust either builds
      // slowly (it picks things up gently, then hard) or bursts in
      const r = Math.random();
      this.mood = this.mood === "gust" ? (r < 0.55 ? "still" : "breeze") : r < 0.32 ? "still" : r < 0.72 ? "breeze" : "gust";
      if (this.mood === "still") { this.goal = R(0, 0.06); this.tau = R(1.2, 3.5); this.next = this.t + R(3, 9); }
      else if (this.mood === "breeze") { this.goal = R(0.15, 0.42); this.tau = R(1, 3); this.next = this.t + R(3, 8); }
      else { this.goal = R(0.6, 1); this.tau = Math.random() < 0.45 ? R(1.6, 3.2) : R(0.25, 0.7); this.next = this.t + R(1.5, 4); }
      // from the window on the right, but never dead straight: one slant, then another
      this.dgoal = FROM_RIGHT + (Math.random() < 0.2 ? R(-0.95, 0.95) : R(-0.5, 0.5));
    }
    this.level += (this.goal - this.level) * (1 - Math.exp(-dt / this.tau));
    let dd = this.dgoal - this.dir; dd = Math.atan2(Math.sin(dd), Math.cos(dd));
    this.dir += dd * (1 - Math.exp(-dt / 3));
    // puffs: born upwind, the stronger the wind the more and the stronger, carried across at the air's speed
    if (this.t >= this.nextGust) {
      this.gusts.push({ s: -1, amp: R(0.1, 0.5) * (0.25 + this.level), w: R(0.15, 0.45), lat: R(2, 7), ph: R(0, TAU) });
      this.nextGust = this.t + R(0.8, 3.5) / (0.3 + this.level);
    }
    for (const g of this.gusts) g.s += Wind.speed(this.level + g.amp) * TIME * dt;
    this.gusts = this.gusts.filter((g) => g.s < 1.2);
    return Math.min(1.2, this.at(0, 0));
  }

  /** a puff that will reach (x, y) in a moment, whatever the wind is doing */
  puff(x: number, y: number) {
    const s = x * Math.cos(this.dir) + y * Math.sin(this.dir);
    this.gusts.push({ s: s - R(0.15, 0.35), amp: R(0.5, 0.9), w: R(0.2, 0.4), lat: R(2, 5), ph: R(0, TAU) });
  }

  /** the wind's strength here, the mean flow plus whatever puff is passing */
  at(x: number, y: number) {
    const cd = Math.cos(this.dir), sd = Math.sin(this.dir);
    const s = x * cd + y * sd, n = -x * sd + y * cd;      // along the wind, across it
    let l = this.level * 0.8;
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
  private ts = 0;
  private things: Thing[] = [];
  private nextThing = 0;
  private mats: { leaf: THREE.MeshStandardNodeMaterial; solid: THREE.MeshStandardNodeMaterial; soft: THREE.MeshStandardNodeMaterial } | null = null;
  private q = new THREE.Quaternion();
  private q2 = new THREE.Quaternion();
  private v2 = new THREE.Vector3();
  private v = new THREE.Vector3();
  private s = new THREE.Vector3();

  /** where the window's light comes from (world space), for leaves lit from behind */
  sunDir = uniform(new THREE.Vector3(0, 0, 1));

  constructor(private aniso: number, private sun: THREE.Color, private renderer: THREE.WebGPURenderer) {}

  /** the things' pictures: the leaf scans, and the atlas of the rest (lib/viewer/things.ts says which is which) */
  async init() {
    if (this.mats) return;
    const tx = async (name: string, srgb: boolean) => {
      const t = await picture(`/tee/table/${name}`, this.renderer, srgb);
      t.anisotropy = this.aniso;
      return t;
    };
    const [lc, ln, bc] = await Promise.all([tx("leaves.webp", true), tx("leaves-n.webp", false), tx("bits.webp", true)]);
    const cell = attribute("cell", "vec2"), tint = attribute("tint", "vec3");
    // leaves: the scan's colour and relief, cut out by its own edge (the cut casts the shadow)
    // (a dry leaf's waxy skin gives it a soft sheen)
    const leaf = new THREE.MeshStandardNodeMaterial({ roughness: 0.62, metalness: 0, side: THREE.DoubleSide });
    const luv = uv().mul(vec2(0.25, 0.25)).add(cell), lcol = texture(lc, luv);
    // graded to the room as the boards were: a touch less saturated and bright than the scanner's flat light
    const lum = lcol.rgb.dot(vec3(0.2126, 0.7152, 0.0722));
    const albedo = mix(vec3(lum), lcol.rgb, 0.86).mul(0.9);
    leaf.colorNode = vec4(albedo, 1);
    // a leaf is thin: with the window behind it, some of that light comes through, warm and glowing at the veins
    const behind = max(dot(normalWorld, this.sunDir.negate()), 0);
    leaf.emissiveNode = albedo.mul(albedo).mul(vec3(this.sun.r, this.sun.g, this.sun.b)).mul(behind.mul(1.6)); leaf.maskNode = lcol.a.greaterThan(0.5); leaf.normalNode = normalMap(texture(ln, luv).rgb);
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
    // in from upwind: most drift down from above the window side and come down wherever the air takes them;
    // the rest skate in along the surface. Either way they come in from out of view. At the start, one or two
    // already lying in view
    const cd = Math.cos(wind.dir), sd = Math.sin(wind.dir), side = R(-0.45, 0.45);
    const drop = !lying && Math.random() < 0.7;
    let x = lying ? R(-0.32, 0.32) : -cd * 0.6 - sd * side, y = lying ? R(-0.38, 0.38) : -sd * 0.6 + cd * side;
    const H = R(0.3, 0.45);
    if (drop) {
      // back up the wind from somewhere it might come down, by about how far the air carries it as it falls
      // (faster up high, slower near the table); and never starting inside the view
      const lx = R(-0.5, 0.5), ly = R(-0.5, 0.5);
      const carry = Wind.speed(wind.at(lx, ly)) * (1 + H / 0.2) * H / (kind.fall * 0.75);
      x = lx - cd * carry; y = ly - sd * carry;
      const sAlong = x * cd + y * sd;
      if (sAlong > -0.55) { x -= cd * (sAlong + 0.55); y -= sd * (sAlong + 0.55); }
    }
    const u = lying ? 0 : Wind.speed(wind.at(x, y)) * R(0.4, 0.8);
    const T: Thing = {
      kind, mesh, size, x, y, h: lying ? 0 : drop ? H : R(0.002, 0.012),
      vx: cd * u, vy: sd * u, vh: 0, yaw: R(0, TAU), vyaw: R(-2, 2), tip: R(0, TAU),
      pitch: Math.random() < 0.5 ? 0 : Math.PI, pv: 0, auto: 0, zmin, zmax, loose: 0, n1: 0, n2: 0,
      grip: R(kind.grip[0], kind.grip[1]), rest: 0, restMax: -1, ph: R(0, 100),
    };
    this.things.push(T); this.group.add(mesh);
  }

  /** one step of the air (dt in seconds as seen); `over(x, y)` is how high the cotton is there (m) */
  step(dt: number, wind: Wind, over: (x: number, y: number) => number) {
    dt = Math.min(dt, 1 / 30);
    this.t += dt; this.ts += dt * TIME;
    // now and then something new, more often when the wind is up; never more than a few about
    const W = wind.level;
    if (this.t > this.nextThing) {
      if (this.things.length < 3) this.spawn(wind);
      this.nextThing = this.t - Math.log(1 - Math.random()) / (0.032 + 0.1 * W * W);
    }
    for (const T of this.things) this.move(T, dt * TIME, dt, wind, over);
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
    let floor = top + 0.0005 + (top > 0.0004 ? 0.0015 : 0);
    // one that comes down on another already lying there lies on top of it (never through it)
    for (const O of this.things) {
      if (O === T) break;
      if (Math.hypot(O.x - T.x, O.y - T.y) < (O.size + T.size) * 0.26) floor = Math.max(floor, O.h + 0.0025);
    }
    return floor;
  }

  /** ds: slowed (physics) time; dt: time as seen, for how long a thing rests */
  private move(T: Thing, ds: number, dt: number, wind: Wind, over: (x: number, y: number) => number) {
    const K = T.kind, v = this.v, s = this.s;
    const floor = this.floorUnder(T, over), onTee = floor > 0.002;
    const above = Math.max(0, T.h - floor), down = above < 0.0008;
    const cd = Math.cos(wind.dir), sd = Math.sin(wind.dir);
    // its own buffeting: smoothed noise, never a frame-to-frame jitter
    const nk = 1 - Math.exp(-ds * 12);
    T.n1 += (R(-1, 1) * 1.7 - T.n1) * nk; T.n2 += (R(-1, 1) * 1.7 - T.n2) * nk;
    // the air right here: the wind and whatever puff is passing, torn up by turbulence, slow at the surface and
    // faster higher up; rising and sinking at a fraction of its speed (it can't blow down through the surface)
    const sw = swirl(T.x, T.y, this.ts, T.ph);
    const l = wind.at(T.x, T.y);
    const dir = wind.dir + 0.22 * sw[0];
    const U = Wind.speed(l) * (1 + 0.25 * sw[1]) * (0.6 + 0.4 * Math.min(1, above / 0.04)) * Math.min(3, 1 + above / 0.1);
    const w = U * 0.3 * sw[2] * Math.min(1, 0.3 + above / 0.03) * Math.max(0, 1 - above / 0.2);
    const rx = Math.cos(dir) * U - T.vx, ry = Math.sin(dir) * U - T.vy, rel = Math.hypot(rx, ry);
    // how it sits to the air: lying flat the air mostly slips over it; tilted, it catches far more (drag), and
    // the air under a raised upwind edge lifts it (tilting further about the cross-wind line raises that edge
    // whichever side it lies on)
    const base = Math.round(T.pitch / Math.PI) * Math.PI;
    const tilt = Math.abs(Math.sin(T.pitch)), up = Math.max(0, Math.sin(T.pitch - base));
    const kd = K.drag * K.catch * (0.25 + 0.75 * tilt);
    let ax = kd * rel * rx, ay = kd * rel * ry;
    const ground = 1 / (1 + above / 0.025);       // lift is strongest skimming the surface (the air squeezed under it)
    const lift = K.lift * rel * rel * (0.2 + 1.6 * up) * ground + K.lift * Math.max(0, w) * Math.abs(w) * 0.8;
    // a puff coming in under it after a rest: its grip loosens over a moment or two (it still takes the air to move it)
    T.loose = Math.max(0, T.loose - dt * 0.5);
    const grip = T.grip * (1 - 0.75 * T.loose);
    let target: number;
    if (down) {
      // on the surface: static friction holds it until the push beats it; sliding, friction is a little less
      // (so it skids, sticks, skids as the push comes and goes); its upwind edge lifts and shivers as the push
      // builds; a strong gust under that edge lifts it off
      // on a slope (the side of a crease, the tee's edge) its weight pulls it down toward the trough
      // (the slope across the whole leaf, not the crease under its middle)
      const e = Math.max(0.01, T.size * 0.4), gx = (over(T.x + e, T.y) - over(T.x - e, T.y)) / (2 * e), gy = (over(T.x, T.y + e) - over(T.x, T.y - e)) / (2 * e);
      ax -= G * gx; ay -= G * gy;
      const fx = Math.hypot(ax, ay), mu = grip * G * (1 / Math.sqrt(1 + gx * gx + gy * gy)), vs = Math.hypot(T.vx, T.vy);
      const strain = Math.min(1, fx / mu);
      target = base + strain * strain * (0.14 + 0.02 * Math.sin(this.ts * 40 + T.ph * 7) + 0.02 * T.n1) * K.tumble;
      if (vs < 0.008 && fx < mu) { ax = 0; ay = 0; T.vx = 0; T.vy = 0; }
      else if (vs > 0) { ax -= (T.vx / vs) * mu * 0.75; ay -= (T.vy / vs) * mu * 0.75; }
      if (lift > G * (1 + grip)) {
        T.vh = (lift - G) * 0.03;
      } else T.vh = 0;
    } else {
      // in the air: it swings like a falling leaf, gliding toward its low edge on each swing (only once clear of
      // the surface); or, in a strong flow, turns over and over. It falls through the air at its own speed, so
      // the air's rising lifts it and its sinking brings it down
      const clear = Math.min(1, above / (T.size * 0.5));
      target = base + (Math.sin(T.tip) * 0.55 + 0.12 * T.n2) * K.tumble * clear;
      const glide = Math.sin(T.pitch) * Math.cos(T.pitch) * G * 0.5 * K.tumble * clear;
      ax += cd * glide; ay += sd * glide;
      const own = Math.min(K.lift * rel * rel * (0.2 + 1.6 * up) * ground + Math.abs(Math.cos(T.tip)) * rel * K.lift * 0.4 * ground, G * 0.7);
      const wr = w - T.vh;
      T.vh += (own - G + (G / (K.fall * K.fall)) * Math.abs(wr) * wr) * ds;
      // only well up in a strong flow, and rarely, does one start turning over and over; it stops as it nears
      // the surface again (and lands on whichever side it comes down)
      if (!T.auto && above > T.size && rel > 2 && Math.random() < 0.06 * K.tumble * ds) T.auto = Math.random() < 0.5 ? -1 : 1;
      if (rel < 1 || above < T.size * 0.8) T.auto = 0;
    }
    if (T.auto && !down) T.pv += (T.auto * rel * K.tumble * 6 - T.pv) * 3 * ds;
    else T.pv += (160 * (target - T.pitch) - 22 * T.pv) * ds;
    T.pitch += T.pv * ds;
    // short of really tumbling it never tips past where it would fall over: lying, its edge lifts a little at
    // most; in the air it rocks but stays the side up it is
    if (!T.auto) {
      const lim = down ? 0.45 : 1.2, d = T.pitch - base;
      if (d > lim) { T.pitch = base + lim; T.pv = Math.min(T.pv, 0); }
      else if (d < -lim) { T.pitch = base - lim; T.pv = Math.max(T.pv, 0); }
    }
    // its weight against the push: it gathers speed and loses it, it doesn't follow the air outright
    T.vx += ax * ds; T.vy += ay * ds;
    // resting: a moment on the tee at most (some never settle there), longer on the boards (in time as seen)
    const speed = Math.hypot(T.vx, T.vy);
    if (down && speed < 0.008) {
      if (T.restMax < 0) T.restMax = onTee ? (Math.random() < 0.35 ? R(0.05, 0.3) : R(0.6, 5)) : R(2, 10);
      T.rest += dt;
      // its time up on the tee, the next puff comes through and gets in under it; on the boards it waits for one
      if (T.rest > T.restMax) { T.loose = R(1, 1.6); if (onTee) wind.puff(T.x, T.y); T.rest = 0; T.restMax = -1; }
    } else if (!down || speed > 0.03) { T.rest = 0; T.restMax = -1; }
    T.x += T.vx * ds; T.y += T.vy * ds; T.h += T.vh * ds;
    if (T.h <= floor) {
      // touching down: a small bounce if it came in fast, then it rocks and settles on whichever side landed
      T.h = floor; T.vh = T.vh < -0.5 ? -T.vh * 0.12 : 0;
      if (T.auto) { T.auto = 0; T.pv *= 0.3; }
    }
    if (T.h > 0.5) { T.h = 0.5; T.vh = Math.min(T.vh, 0); }
    // turning: sliding, it swings round to trail its broad end (the stem leads; turned over, the stem points the
    // other way) and its edges catch; in the air the flow buffets it round, more the harder the air rushes past
    let dy = wind.dir + (Math.cos(T.pitch) < 0 ? Math.PI : 0) - T.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy));
    const vane = down ? dy * Math.min(1, speed * 3) * 20 : 0;
    T.vyaw += ((T.n1 * 4 + sw[1] * 3) * rel * K.spin * (down ? 0.35 : 1) + vane - T.vyaw * 4) * ds; T.yaw += T.vyaw * ds;
    T.tip += ds * (7 + rel * 5) * (down ? 0.2 : 1);
    // its pose: the tilt about the line across the wind, then its own turn; lifted so the lowest point of its curl
    // and its tilted edge clear the surface (it pivots on the edge still touching)
    const ax2 = this.v2.set(-sd, cd, 0);
    this.q.setFromAxisAngle(ax2, T.pitch).multiply(this.q2.setFromAxisAngle(Z, T.yaw));
    const cp = Math.cos(T.pitch);
    const low = (cp >= 0 ? T.zmin : -T.zmax) * Math.abs(cp) - Math.abs(Math.sin(T.pitch)) * 0.42;
    v.set(T.x, T.y, T.h - low * T.size); s.set(T.size, T.size, T.size);
    T.mesh.matrix.compose(v, this.q, s); T.mesh.matrixWorldNeedsUpdate = true;
  }

  /** a fresh table: a thing or two already lying about, more on the way */
  reset(wind: Wind) {
    for (const T of this.things) { this.group.remove(T.mesh); T.mesh.geometry.dispose(); }
    this.things = [];
    for (let i = Math.random() < 0.6 ? 1 : 2; i > 0; i--) this.spawn(wind, true);
    this.nextThing = this.t + R(6, 16);
  }
}

type Thing = {
  kind: Kind; mesh: THREE.Mesh; size: number; x: number; y: number; h: number; vx: number; vy: number; vh: number;
  yaw: number; vyaw: number; tip: number; grip: number; rest: number; restMax: number; ph: number;
  /** its tilt about the line across the wind (0 or π lying flat on one side or the other), how fast that turns,
   *  whether it's autorotating (spinning over and over in a strong flow: -1, 0, 1), and how far its curl reaches
   *  below and above its middle (in its own size) */
  pitch: number; pv: number; auto: number; zmin: number; zmax: number;
  /** how far the air has got in under it after a rest (0..1.6, fading), and its own smoothed buffeting */
  loose: number; n1: number; n2: number;
};
const pick = () => {
  let r = Math.random() * KINDS.reduce((a, k) => a + k.weight, 0);
  for (const k of KINDS) { r -= k.weight; if (r <= 0) return k; }
  return KINDS[0];
};
