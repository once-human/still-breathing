// The studio, shared by the real-time renderer and the path tracer so the two can never drift apart.
// Everything is the render.py rig converted from Blender (Z up) to three (Y up): (x, y, z) -> (x, z, -y).

export type V3 = [number, number, number];

export const ASPECT = 880 / 1120;
/** One fixed product camera: 85 mm on a 36 mm sensor (fit to the tall side), f/5.6, chest height. */
export const CAMERA = {
  pos: [0.18, 1.22, 2.55] as V3,
  target: [0, 1.1, 0] as V3,
  lensMm: 85,
  sensorMm: 36,
  fstop: 5.6,
  focus: 2.45,
};
export const VFOV = 2 * Math.atan(CAMERA.sensorMm / 2 / CAMERA.lensMm); // radians

export type RectLight = { name: string; pos: V3; size: [number, number]; power: number; tint: V3 };
export type Scene = {
  id: string;
  label: string;
  lights: RectLight[];
  /** seamless paper colour (linear) */
  paper: V3;
  /** uniform world light (linear) */
  world: V3;
  /** light-tee power factor: render.py lowers the rig for off white so its folds don't burn out */
  creamK: number;
};

export const LIGHT_AIM: V3 = [0, 1.12, 0];

export const STUDIO: Scene = {
  id: "studio",
  label: "studio",
  lights: [
    { name: "key", pos: [-1.5, 2.1, 1.9], size: [1.4, 1.8], power: 160, tint: [1, 0.98, 0.95] },
    { name: "fill", pos: [1.9, 1.3, 1.4], size: [1.2, 1.6], power: 45, tint: [0.95, 0.97, 1] },
    { name: "rim", pos: [0.6, 2.4, -1.4], size: [1.0, 1.0], power: 90, tint: [1, 1, 1] },
  ],
  paper: [0.52, 0.515, 0.505],
  world: [0.03, 0.03, 0.03],
  creamK: 0.42,
};

/** Seamless sweep from render.py: floor at y 0.35, a 0.6 m cove, wall 1.5 m behind the tee. */
export const SWEEP = { floorY: 0.35, coveR: 0.6, coveY: 0.95, coveZ: -0.9, wallZ: -1.5, top: 4.35, front: 5.4, halfW: 6 };

// ---------- small vector helpers ----------
export const sub = (a: V3, b: V3): V3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
export const add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export const mul = (a: V3, s: number): V3 => [a[0] * s, a[1] * s, a[2] * s];
export const dot = (a: V3, b: V3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const cross = (a: V3, b: V3): V3 => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
export const norm = (a: V3): V3 => mul(a, 1 / Math.hypot(...a));

/** Light frame like Blender's track-to (-Z at the aim, Y up): ex along width, ey along height, n toward the aim. */
export function lightFrame(l: RectLight) {
  const n = norm(sub(LIGHT_AIM, l.pos));
  const ex = norm(cross([0, 1, 0], mul(n, -1)));
  const ey = cross(mul(n, -1), ex);
  const area = l.size[0] * l.size[1];
  return { n, ex: mul(ex, l.size[0] / 2), ey: mul(ey, l.size[1] / 2), area };
}

/** Blender area light power (W) to emitted radiance: one-sided Lambertian emitter, L = P / (pi A). */
export function radiance(l: RectLight, k: number): V3 {
  const L = (l.power * k) / (Math.PI * l.size[0] * l.size[1]);
  return mul(l.tint, L);
}

/** Camera basis: right, up, forward. */
export function cameraBasis() {
  const f = norm(sub(CAMERA.target, CAMERA.pos));
  const r = norm(cross(f, [0, 1, 0]));
  const u = cross(r, f);
  return { f, r, u };
}
