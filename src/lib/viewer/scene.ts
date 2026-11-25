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
/** The shop shot with someone wearing the tee: the same lens, from chest height, tilted up to take in the whole
 * head with a little room above it, down to the middle of the thighs (the face is seen; the legs mostly aren't).
 * The camera stays where the places' pictures were made from (2.86 m out, 1.1 m up) and only turns, so every place
 * still lines up behind the person. */
export const WEAR_CAMERA: Camera = { pos: [0.2, FLOOR + 1.1, 2.85], target: [0, FLOOR + 1.24, 0], lensMm: 85, sensorMm: 36, fstop: 5.6, focus: 2.8 };
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
  /** how much the picture lights the person as well as standing behind them (1: it is in the lights' own units) */
  envLight?: number;
  /** where the lights point (default LIGHT_AIM) */
  aim?: V3;
  /** what moves in the place: a looping video of the band's top rows (MOTION) */
  motion?: string;
  /** fit mode (a whole body, a camera further back) keeps the paper sweep: the place's picture is made for the shop shot */
  fit?: Scene;
};

export const LIGHT_AIM: V3 = [0, 1.12, 0];

/**
 * What the viewer draws behind the person: the band of the place its camera can see, sharp, beside the whole
 * picture (which lights the person and fills the rest of the sphere). The band is rows 3368..5008 of a 16384 x 8192
 * panorama (about 16 degrees up to 20 down, 45 pixels a degree, as fine as the screen), stored as 4 tiles of 4096
 * stacked top to bottom (pipeline/stage_post.py BAND_ROWS); the -lo copy is half size, for phones.
 */
export const BAND = { v0: 3368 / 8192, v1: 5008 / 8192, tiles: 4 };
/**
 * The show's canopy breathing: the rows of the band it moves in (3368..4096 of 8192, about 16 degrees up down to the
 * horizon: every swag hangs above the camera), a looping video of the same four stacked tiles (pipeline/motion_post.py);
 * everything below them stays the band. How far down it reaches is read from the video's own size (raster.ts).
 */
export const MOTION = { v0: 3368 / 8192, v1: 4096 / 8192, tiles: 4 };
export const motionOf = (url: string, lo: boolean) => (lo ? url.replace(/\.mp4$/, "-lo.mp4") : url);
export const bandOf = (env: string, lo: boolean) => env.replace(/\.webp$/, lo ? "-band-lo.webp" : "-band.webp");

/** the old paper-sweep studio and window, kept for fit mode */
const SWEEP_STUDIO: Scene = {
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
const SWEEP_WINDOW: Scene = {
  id: "window", label: "window light",
  lights: [
    // a big north window to the left, a white wall bouncing back on the right
    { name: "window", pos: [-2.6, 1.7, 0.9], size: [2.0, 2.4], power: 420, tint: [1, 0.99, 0.97] },
    { name: "wall", pos: [2.4, 1.4, 1.2], size: [2.2, 2.4], power: 60, tint: [1, 0.97, 0.92] },
  ],
  paper: [0.62, 0.6, 0.56], world: [0.09, 0.1, 0.12], creamK: 0.45,
};

/** the places light the chest, 1.1 m up (pipeline/stage.py AIM) */
const CHEST: V3 = [0, FLOOR + 1.1, 0];

/**
 * The places: the studio and the room are real rooms photographed all round (pipeline/photo_place.py lays the
 * photo onto the room's own floor and walls and finds its lights); the show is built in Blender (pipeline/stage.py)
 * with these same lights at the same powers. Each is pictured as the viewer's camera sees it walking round the
 * person. The picture stands behind the person and lights them too: a white room is mostly light off its own walls.
 */
export const STUDIO: Scene = {
  id: "studio", label: "studio",
  // a real daylight photo studio (a 360 photograph, pipeline/photo_place.py): the tall window and an octabox ahead of
  // the person, a second window beside it, a strip softbox on a C-stand behind; each is where the photo has it, as
  // big and as bright as it is there; the white room lights the rest through the picture
  lights: [
    { name: "window", pos: [0.93, 2.25, 2.1], size: [1.62, 2.31], power: 53.9, tint: [0.808, 0.902, 1] },
    { name: "window2", pos: [-2.07, 2.28, 2.2], size: [0.82, 1.97], power: 19.3, tint: [0.944, 0.985, 1] },
    { name: "octa", pos: [-1.27, 1.93, 2.09], size: [0.95, 0.91], power: 25.4, tint: [1, 0.745, 0.533] },
    { name: "strip", pos: [-1.55, 2.61, -1.16], size: [0.73, 1.08], power: 14.1, tint: [1, 0.853, 0.813] },
  ],
  paper: [0, 0, 0], world: [0.371, 0.347, 0.325], creamK: 0.6, open: true, venue: true, aim: CHEST,
  env: "/tee/stage/studio.webp", envLight: 1, fit: SWEEP_STUDIO,
};

export const SCENES: Scene[] = [
  STUDIO,
  {
    id: "window", label: "window light",
    // a real sunny flat (a 360 photograph, pipeline/photo_place.py): the sheer-curtained corner window ahead of the
    // person, the big clear window to their left, the sun's patch on the floorboards beside them bouncing up;
    // the sofa against a plaster wall behind them in the front view
    lights: [
      { name: "curtain", pos: [-0.74, 1.49, 2.78], size: [2.3, 2.64], power: 59.5, tint: [0.93, 0.956, 1] },
      { name: "window", pos: [2.13, 2.05, 1.35], size: [1.69, 1.67], power: 42.4, tint: [0.621, 0.782, 1] },
      { name: "sunfloor", pos: [1.64, 0.35, 0.66], size: [1.61, 1.26], power: 29.3, tint: [1, 0.961, 0.945] },
    ],
    paper: [0, 0, 0], world: [0.576, 0.551, 0.541], creamK: 0.6, open: true, venue: true, aim: CHEST,
    env: "/tee/stage/window.webp", envLight: 1, fit: SWEEP_WINDOW,
  },
  {
    id: "show", label: "show",
    // the night in the round at Alexandra Palace under its cloth canopy (pipeline/stage.py): the person is in the
    // crowd facing the decks 6.5 m ahead (+z, behind the camera in the front view). Front light at a show is hard
    // and from high up: a warm par and a cool head on the bar over the front of the stage (3 m out, 5.5 m up), a
    // warm follow spot on a stand to the side; behind the person the front-of-house light lights the back. Each
    // hangs in the hall's picture where it lights the person from.
    lights: [
      { name: "stage", pos: [1.4, 5.85, 3.0], size: [0.4, 0.4], power: 760, tint: [1, 0.8, 0.6] },
      { name: "beam", pos: [-1.6, 5.85, 3.2], size: [0.2, 0.2], power: 360, tint: [0.86, 0.91, 1] },
      { name: "spot", pos: [-6.0, 4.6, 2.0], size: [0.3, 0.3], power: 390, tint: [1, 0.72, 0.45] },
      { name: "foh", pos: [-1.4, 3.5, -3.6], size: [0.8, 0.8], power: 480, tint: [1, 0.86, 0.7] },
    ],
    paper: [0, 0, 0], world: [0.0015, 0.0015, 0.002], creamK: 0.6, open: true, venue: true, aim: CHEST,
    env: "/tee/stage/show.webp", envLight: 1, motion: "/tee/stage/show-motion.mp4",
  },
];

/** the scene as a given shot uses it: fit mode keeps a place's paper-sweep version */
export const sceneFor = (s: Scene, body: boolean): Scene => (body && s.fit ? s.fit : s);

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
export function lightFrame(l: RectLight, aim: V3 = LIGHT_AIM) {
  const n = norm(sub(aim, l.pos));
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
