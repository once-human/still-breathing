// The studio, shared by the real-time renderer and the path tracer so the two can never drift apart.
// Everything is the render.py rig converted from Blender (Z up) to three (Y up): (x, y, z) -> (x, z, -y).

export type V3 = [number, number, number];

export const ASPECT = 880 / 1120;
/** One fixed product camera: 85 mm on a 36 mm sensor (fit to the tall side), f/5.6, chest height. */
export type Camera = { pos: V3; target: V3; lensMm: number; sensorMm: number; fstop: number; focus: number };
export const CAMERA: Camera = {
  pos: [0.2, 1.21, 2.85],
  target: [0, 1.09, 0],
  lensMm: 85,
  sensorMm: 36,
  fstop: 5.6,
  focus: 2.75,
};
/** Fit mode stands the body on the studio floor (lifted by FLOOR so its feet touch the sweep). Same 85 mm lens,
 * stepped back to take in the whole person: a different shot, never a different lens on the same shot. */
export const FLOOR = 0.35;
/** jersey loop tile repeats over the texture atlas: 2 x 110 cm by 86 cm, over an 11.4 x 11.1 mm tile */
export const KNIT_REPEAT: [number, number] = [220 / 1.14, 86 / 1.11];
export const BODY_CAMERA: Record<"stand" | "up" | "sit", Camera> = {
  stand: { pos: [0.33, FLOOR + 1.02, 4.85], target: [0, FLOOR + 0.92, 0], lensMm: 85, sensorMm: 36, fstop: 8, focus: 4.8 },
  up: { pos: [0.33, FLOOR + 1.12, 5.15], target: [0, FLOOR + 1.02, 0], lensMm: 85, sensorMm: 36, fstop: 8, focus: 5.1 },
  sit: { pos: [0.33, FLOOR + 0.8, 4.4], target: [0, FLOOR + 0.66, 0], lensMm: 85, sensorMm: 36, fstop: 8, focus: 4.3 },
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
  /** no backdrop: the tee hangs in open space (a show has no paper sweep, just the dark) */
  open?: boolean;
  /** the lights belong to the place, not to the photographer: they stay put while the camera walks round */
  venue?: boolean;
  /** the place itself, all round: a 360 degree picture (equirectangular, the stage at +z in the middle) */
  env?: string;
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

/**
 * Real places, not slider positions. Powers are Blender watts (radiance = P / (pi A)); the exposure is fixed,
 * so each place is lit to read well at the same camera settings, the way a photographer would set it.
 */
export const SCENES: Scene[] = [
  STUDIO,
  {
    id: "window", label: "window light",
    lights: [
      // a big north window to the left, a white wall bouncing back on the right
      { name: "window", pos: [-2.6, 1.7, 0.9], size: [2.0, 2.4], power: 420, tint: [1, 0.99, 0.97] },
      { name: "wall", pos: [2.4, 1.4, 1.2], size: [2.2, 2.4], power: 60, tint: [1, 0.97, 0.92] },
    ],
    paper: [0.62, 0.6, 0.56], world: [0.09, 0.1, 0.12], creamK: 0.45,
  },
  {
    id: "show", label: "the show",
    // in the crowd, facing the stage (+z, ahead of the person, so behind the camera in the front view): the
    // stage's lamps, light bars and screen wash the front warm-white, a warm spot from stage left and the truss's
    // cool beams catch the edges; behind the person the front-of-house spots light the back. The hall and its
    // stage are one 360 degree picture rendered in Blender (pipeline/stage.py), loaded after the tee is up.
    lights: [
      { name: "stage", pos: [0.6, 3.1, 3.6], size: [2.6, 0.8], power: 650, tint: [1, 0.9, 0.8] },
      { name: "spot", pos: [-2.6, 3.8, 1.6], size: [0.25, 0.25], power: 260, tint: [1, 0.72, 0.45] },
      { name: "beam", pos: [0.4, 4.2, 0.9], size: [1.4, 0.3], power: 160, tint: [0.86, 0.91, 1] },
      { name: "foh", pos: [-1.4, 3.5, -3.6], size: [0.8, 0.8], power: 480, tint: [1, 0.86, 0.7] },
    ],
    paper: [0, 0, 0], world: [0.0015, 0.0015, 0.002], creamK: 0.6, open: true, venue: true, env: "/tee/stage/show.webp",
  },
];

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

/** turn about the vertical by `deg` (the viewer's turn: x' = x cos + z sin, z' = -x sin + z cos) */
export function turnY(v: V3, deg: number): V3 {
  const a = (deg * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
  return [c * v[0] + s * v[2], v[1], -s * v[0] + c * v[2]];
}

/** Camera basis: right, up, forward. */
export function cameraBasis(cam: Camera = CAMERA) {
  const f = norm(sub(cam.target, cam.pos));
  const r = norm(cross(f, [0, 1, 0]));
  const u = cross(r, f);
  return { f, r, u };
}
