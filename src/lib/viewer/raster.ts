// Real-time view on three.js WebGPURenderer (falls back to WebGL2 by itself where WebGPU is missing).
// It is the preview you drag; the path tracer takes over the moment you let go.
import * as THREE from "three/webgpu";
import { positionLocal, texture, uv, vec2, vec3, float, normalMap, normalize, uniform, mix, vertexColor, step, fwidth, clamp, length, normalWorldGeometry, atan, asin, cos, sin, sqrt, max, log2 } from "three/tsl";
import { PRINT_BACK, PRINT_FRONT, type Rect } from "./print";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { RectAreaLightTexturesLib } from "three/addons/lights/RectAreaLightTexturesLib.js";
import { CAMERA, VFOV, ASPECT, SWEEP, FLOOR, KNIT_REPEAT, SCENES, BAND, MOTION, lightFrame, radiance, type Camera, type Scene, type V3 } from "./scene";
import { ENV_W, projectEnv, turnSH } from "./sh";
import type { TeeGeometry } from "./pathtracer";
import { grab, bitmap, type Pixels } from "./grab";
import { picture, gpuDevice, streamTexture } from "./pic";
import { ClothLink, offsetTexture, slopeTextures, clothNodes } from "./cloth";
import { Motion, MOTION_ATTRS } from "./motion";
import type { FlatLay, LookNodes, Side } from "./flat";

export const ASSET = "/tee/fit/";
export type Pose = "stand" | "up" | "sit";
/**
 * One simulated tee: `dir` is a body + size from the fit pipeline (e.g. m170-M) or the shop tee (form-M).
 * `body` shows fit mode's plain body; `person` is someone wearing it (a GLB from pipeline/human.py: painted skin,
 * jeans, eyes, the same body in the same pose the tee was simulated on).
 */
export type Variant = { dir: string; size: string; pose: Pose; body: boolean; seat?: number; skin?: V3; person?: string };
export const FABRIC: Record<"black" | "cream", V3> = { black: srgbToLinear(0x151515), cream: srgbToLinear(0xfffae7) };

function srgbToLinear(hex: number): V3 {
  const c = new THREE.Color().setHex(hex, THREE.SRGBColorSpace);
  return [c.r, c.g, c.b];
}

/** a loaded tee (and body or person), ready to go back on the stand */
type Worn = {
  roots: THREE.Object3D[];
  parts: { mesh: THREE.Mesh; mw: THREE.Matrix4; id: number; person: boolean }[];
  /** each tee mesh in the garment's frame, and its cloth skin attributes */
  tee: { pos: Float32Array; idx: Uint32Array; skin: [THREE.BufferAttribute, THREE.BufferAttribute] }[];
  /** the skin under the tee, for the cloth to rest on */
  body: { pos: Float32Array; nrm: Float32Array } | null;
  joints: Record<string, [number, number, number]> | null;
  skinMaps: [ImageBitmap, ImageBitmap] | null;
  /** the hair cards' strands, for the path tracer */
  hair?: ImageBitmap;
  lift: number; clothOn: boolean; tris: number; built: TeeGeometry | null;
};
const wornKey = (v: Variant) => JSON.stringify([v.dir, v.pose, v.person ?? "", !!v.body, v.seat ?? 0]);
const concat = (a: Float32Array[]) => { const o = new Float32Array(a.reduce((n, x) => n + x.length, 0)); let k = 0; for (const x of a) { o.set(x, k); k += x.length; } return o; };

/** a place's picture, ready to draw: the full picture, and its 64 x 32 linear version for the light probe */
/** a place's whole picture, and the sharp band of it the camera sees (scene.ts BAND), where there is one */
export type Env = { url: string; px: Pixels; band?: Pixels };

/**
 * The most lights any place has. The rig is built once with this many and never changes: a light's identity is part
 * of every lit shader, so new lights (another place, another shirt) would rebuild them all. A place sets as many as
 * it has and leaves the rest dark.
 */
const MAX_LIGHTS = Math.max(...SCENES.flatMap((sc) => [sc, sc.fit]).map((sc) => sc?.lights.length ?? 0));

/** Seamless sweep mesh, the same shape the path tracer intersects analytically. */
function sweepGeometry() {
  const S = SWEEP, prof: [number, number][] = [];
  prof.push([S.floorY, S.front], [S.floorY, S.coveZ]);
  for (let i = 1; i < 24; i++) {
    const t = (i / 24) * (Math.PI / 2);
    prof.push([S.coveY - S.coveR * Math.cos(t), S.coveZ - S.coveR * Math.sin(t)]);
  }
  prof.push([S.coveY, S.wallZ], [S.top, S.wallZ]);
  const pos: number[] = [], idx: number[] = [];
  prof.forEach(([y, z], i) => {
    pos.push(-S.halfW, y, z, S.halfW, y, z);
    if (i) idx.push(2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i - 2, 2 * i + 1, 2 * i);
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
}

/** the scene as one triangle soup for the path tracer, in typed arrays sized up front */
function soupOf(parts: { mesh: THREE.Mesh; mw: THREE.Matrix4; id: number; person: boolean }[], lift: number, skin: TeeGeometry["skin"]): TeeGeometry {
  let nv = 0, ni = 0;
  for (const { mesh: { geometry: g } } of parts) { nv += g.attributes.position.count; ni += g.index ? g.index.count : g.attributes.position.count; }
  const pos = new Float32Array(3 * nv), nrm = new Float32Array(3 * nv), uv = new Float32Array(2 * nv), col = new Float32Array(3 * nv).fill(1);
  const idx = new Uint32Array(ni), mat = new Uint8Array(ni / 3), vv = new THREE.Vector3();
  let vb = 0, ib = 0;
  for (const { mesh, mw, id, person } of parts) {
    const g = mesh.geometry, pa = g.attributes.position, na = g.attributes.normal, ua = g.attributes.uv, ca = g.attributes.color;
    const nm = new THREE.Matrix3().getNormalMatrix(mw);
    for (let i = 0; i < pa.count; i++) {
      const o = 3 * (vb + i);
      vv.fromBufferAttribute(pa, i).applyMatrix4(mw); pos[o] = vv.x; pos[o + 1] = vv.y + lift; pos[o + 2] = vv.z;
      vv.fromBufferAttribute(na, i).applyMatrix3(nm).normalize(); nrm[o] = vv.x; nrm[o + 1] = vv.y; nrm[o + 2] = vv.z;
      if (ua) { uv[2 * (vb + i)] = ua.getX(i); uv[2 * (vb + i) + 1] = ua.getY(i); }
      if (person && ca) { col[o] = ca.getX(i); col[o + 1] = ca.getY(i); col[o + 2] = ca.getZ(i); }
    }
    const ix = g.index?.array, cnt = ix ? ix.length : pa.count;
    for (let j = 0; j < cnt; j++) idx[ib + j] = (ix ? ix[j] : j) + vb;
    mat.fill(id, ib / 3, (ib + cnt) / 3);
    vb += pa.count; ib += cnt;
  }
  return { pos, nrm, uv, idx, mat, col, skin };
}

export class Raster {
  /** the person's idle motion, and the tee's with them (motion.ts) */
  motion = new Motion();
  renderer: THREE.WebGPURenderer;
  /** multisampled (a screen under 2x): the hair cards' edges go soft by coverage */
  private msaa = false;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera((VFOV * 180) / Math.PI, ASPECT, 0.05, 40);
  pivot = new THREE.Group();
  /** the lights; at a venue they turn with the pivot, so the camera walks round a place that stays put */
  rig = new THREE.Group();
  private venue = false;
  /** the place around the person (a 360 degree picture), drawn behind everything at a venue */
  private env: ReturnType<typeof texture> | null = null;
  /** the band the camera sees, sharp, and the background drawn from it (the whole picture above and below it) */
  private band: ReturnType<typeof texture> | null = null;
  private bg: THREE.Node | null = null;
  private bandOn = false;
  /** the place's moving rows (the show's canopy), a video laid over the band where it moves; off: the band alone */
  private motionNode: ReturnType<typeof texture> | null = null;
  private motionOn = uniform(0);
  private motionVideo: HTMLVideoElement | null = null;
  private motionTex: THREE.VideoTexture | null = null;
  private envYaw = uniform(0);
  private envOn = false;
  lights: THREE.RectAreaLight[] = Array.from({ length: MAX_LIGHTS }, () => new THREE.RectAreaLight(0xffffff, 0, 1, 1));
  hemi = new THREE.HemisphereLight(0xf4f2ee, 0x6d6a64, 0.15);
  /** the place's picture as light on the person (its spherical harmonics, turned with the place) */
  probe = new THREE.LightProbe(undefined, 0);
  /** the picture's light, unturned (9 x rgb spherical harmonics), and the same turned with the place */
  private envSH: Float64Array | null = null;
  private turnedSH = new Float64Array(27);
  /** each place's picture, uploaded once and kept: going back to a place is only a pointer swap */
  private envTex = new Map<string, Promise<{ tex: THREE.Texture; sh: Float64Array }>>();
  private envLight = 0;
  private world: V3 = [0, 0, 0];
  private probeYaw = NaN;
  paperMat = new THREE.MeshStandardMaterial({ roughness: 0.95, metalness: 0 });
  sweep: THREE.Mesh;
  outer: THREE.MeshPhysicalNodeMaterial | null = null;
  inner = new THREE.MeshStandardNodeMaterial({ roughness: 0.95, metalness: 0 });
  /** per-particle cloth offsets, read in the vertex shader */
  offsets = offsetTexture();
  /** per-particle slope of the cloth (how it tilts the light), read in the vertex shader */
  slopes = slopeTextures();
  /** the cloth, simulated in its own Worker (made with the first tee) */
  cloth: ClothLink | null = null;
  maxAniso = 8;
  knit = uniform(0.55);
  backTex: Record<string, THREE.Texture> = {};
  frontTex: Record<string, THREE.Texture> = {};
  /** the fabric's own colour (the prints are laid over it) */
  private fabric = uniform(new THREE.Color());
  tris = 0;
  isWebGPU = false;

  constructor(canvas: HTMLCanvasElement) {
    // on a 2x screen the pixels already supersample the edges; multisampling on top only costs frames
    this.msaa = (globalThis.devicePixelRatio || 1) < 1.5;
    this.renderer = new THREE.WebGPURenderer({ canvas, antialias: this.msaa, alpha: false });
    this.renderer.toneMapping = THREE.NeutralToneMapping;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.scene.add(this.pivot, this.rig, this.hemi, this.probe);
    this.rig.add(...this.lights);
    this.sweep = new THREE.Mesh(sweepGeometry(), this.paperMat); this.scene.add(this.sweep);
    this.camera.position.set(...CAMERA.pos);
    this.camera.lookAt(...CAMERA.target);
  }

  async init() {
    await this.renderer.init();
    THREE.RectAreaLightNode.setLTC(RectAreaLightTexturesLib.init());
    this.isWebGPU = !!(this.renderer.backend as { isWebGPUBackend?: boolean }).isWebGPUBackend;
    this.maxAniso = Math.max(1, this.renderer.getMaxAnisotropy?.() ?? 8);
    this.inner.positionNode = this.motion.node(this.clothed());
  }

  private clothed() { return clothNodes(this.offsets, this.slopes).position; }

  setScene(s: Scene, cream: boolean) {
    this.venue = !!s.venue; this.rig.rotation.y = this.venue ? this.pivot.rotation.y : 0;
    const k = cream ? s.creamK : 1;
    // the same lights every time, moved and set (never new ones: see MAX_LIGHTS)
    this.lights.forEach((rl, i) => {
      const l = s.lights[i];
      if (!l) { rl.intensity = 0; return; }
      const fr = lightFrame(l, s.aim), L = radiance(l, k);
      const peak = Math.max(...L);
      rl.color.setRGB(L[0] / peak, L[1] / peak, L[2] / peak); rl.intensity = peak;
      rl.width = l.size[0]; rl.height = l.size[1];
      rl.position.set(...l.pos);
      rl.lookAt(l.pos[0] + fr.n[0], l.pos[1] + fr.n[1], l.pos[2] + fr.n[2]);
    });
    this.paperMat.color.setRGB(...s.paper, THREE.LinearSRGBColorSpace);
    this.sweepOn = !s.open; this.sweep.visible = this.sweepOn && !this.flat?.side;
    (this.scene.background as THREE.Color | null)?.isColor ? (this.scene.background as THREE.Color).setRGB(...s.world, THREE.LinearSRGBColorSpace)
      : (this.scene.background = new THREE.Color().setRGB(...s.world, THREE.LinearSRGBColorSpace));
    this.envOn = !!s.env; this.envLight = s.envLight ?? 0; this.world = s.world; this.showEnv();
  }

  /**
   * Light from all round: the place's picture where it lights the person (projected on spherical harmonics, which
   * three.js turns into the irradiance a surface facing each way receives), otherwise the uniform world light.
   */
  private ambient() {
    const sh0 = this.envSH, lit = !!(sh0 && this.envOn && this.envLight > 0);
    if (!lit) {
      this.probe.intensity = 0; this.probeYaw = NaN;
      // uniform world light: irradiance pi * W, as the path tracer integrates it
      const w = Math.max(...this.world, 1e-6);
      this.hemi.color.setRGB(this.world[0] / w, this.world[1] / w, this.world[2] / w, THREE.LinearSRGBColorSpace);
      this.hemi.groundColor.copy(this.hemi.color).multiplyScalar(0.6);
      this.hemi.intensity = Math.PI * w;
      return;
    }
    this.hemi.intensity = 0;
    const yaw = this.rig.rotation.y;
    if (yaw === this.probeYaw) return;
    this.probeYaw = yaw;
    // projected once per picture; turning it with the place is two small matrix products (sh.ts)
    const c = turnSH(sh0!, yaw, this.turnedSH), co = this.probe.sh.coefficients;
    for (let k = 0; k < 9; k++) co[k].set(c[3 * k], c[3 * k + 1], c[3 * k + 2]);
    this.probe.intensity = this.envLight;
  }

  /**
   * The 360 degree picture of the place (stage ahead of the person, the hall behind). Looked up by direction the
   * same way the path tracer does: u = 0.5 - atan2(x, z) / 2pi (the stage, +z, in the middle), v = 0 straight up.
   * It turns with the person, as the lights do (a game camera walking round a place that stays put).
   */
  async setEnv(env: Env | null) {
    const turn = ++this.envTurn;
    if (!env) { this.probeYaw = NaN; this.envSH = null; this.env = null; this.envUrl = ""; this.bandOn = false; this.showEnv(); return; }
    const { tex: t, sh } = await this.prepareEnv(env);
    // another place was picked while this one went up: that one is shown instead
    if (turn !== this.envTurn) return;
    this.probeYaw = NaN; this.envUrl = env.url;
    // the sharp band (a big picture, setBand) if it's on the card; until it is, the whole picture stands in
    const bandP = this.bands.get(env.url);
    const band = bandP ? await Promise.race([bandP, Promise.resolve(undefined)]) : null;
    if (band === undefined) void bandP!.then((b) => this.showBand(env.url, b));
    this.envSH = sh; this.bandOn = !!band;
    if (this.env) { this.env.value = t; if (band) this.band!.value = band; this.applyMotion(); this.showEnv(); return; }
    const d = normalize(normalWorldGeometry);
    const c = cos(this.envYaw), sn = sin(this.envYaw);
    const x = c.mul(d.x).sub(sn.mul(d.z)), z = sn.mul(d.x).add(c.mul(d.z));
    const u = float(0.5).sub(atan(x, z).div(2 * Math.PI));
    const v = float(0.5).sub(asin(clamp(d.y, -1, 1)).div(Math.PI));
    const envN = texture(t, vec2(u, v)); this.env = envN;
    // the band: which of its tiles u falls in, and where in that tile; a tile's edge columns are held at its edge
    // (half a texel in) so its neighbour in the file never bleeds in where the tiles meet round the sphere
    const T = BAND.tiles, vb = v.sub(BAND.v0).div(BAND.v1 - BAND.v0);
    const fu = u.mul(T), tile = clamp(fu.floor(), 0, T - 1);
    const bx = clamp(fu.sub(tile), 0.5 / 4096, 1 - 0.5 / 4096), by = tile.add(clamp(vb, 2 / 6560, 1 - 2 / 6560)).div(T);
    const bandN = texture(band ?? t, vec2(bx, by)); this.band = bandN;
    // the moving rows: the same tiling over fewer rows; at their foot they ease into the band over a few rows
    const vm = v.sub(MOTION.v0).div(MOTION.v1 - MOTION.v0);
    const my = tile.add(clamp(vm, 2 / 1792, 1 - 2 / 1792)).div(T);
    const motionN = texture(band ?? t, vec2(bx, my)); this.motionNode = motionN;
    const wm = step(0, vm).mul(clamp(float(1).sub(vm).div(0.04), 0, 1)).mul(this.motionOn);
    this.bg = mix(mix(envN, bandN, step(0, vb).mul(step(vb, 1))), motionN, wm);
    this.applyMotion();
    this.showEnv();
  }
  private envTurn = 0;
  private envUrl = "";
  /** each place's sharp band (scene.ts BAND), once it's been asked for: sent to the card when that place is shown */
  private bands = new Map<string, Promise<THREE.Texture | null>>();
  hasBand(url: string) { return this.bands.has(url); }
  /** the band of a place, sent up and drawn the moment it's in (if that place is still the one shown) */
  setBand(url: string, px: { data: Uint8Array; width: number; height: number }) {
    if (this.bands.has(url)) return;
    // drawn about one texel to a screen pixel, so no mips; every tile row clamps on its own
    const p = this.upEnv(px, THREE.ClampToEdgeWrapping).catch(() => null);
    this.bands.set(url, p);
    void p.then((b) => this.showBand(url, b));
  }
  private showBand(url: string, b: THREE.Texture | null) {
    if (url !== this.envUrl || !b || !this.band || !this.env) return;
    this.band.value = b; this.bandOn = true; this.showEnv(); this.onRedraw?.();
  }
  /** a place's picture (or band) on the card: written a slice at a time (or, off WebGPU, as one plain buffer copy) */
  private async upEnv(px: { data: Uint8Array; width: number; height: number }, wrapS: THREE.Wrapping) {
    const dev = this.device();
    let t: THREE.Texture;
    if (dev) t = await streamTexture(dev, [px], true);
    else { t = new THREE.DataTexture(px.data, px.width, px.height, THREE.RGBAFormat, THREE.UnsignedByteType); t.needsUpdate = true; }
    t.flipY = false; t.colorSpace = THREE.SRGBColorSpace; t.wrapS = wrapS; t.wrapT = THREE.ClampToEdgeWrapping;
    // no mips: the picture is only ever magnified, and mips would draw a seam where u wraps round
    t.generateMipmaps = false; t.minFilter = THREE.LinearFilter; t.magFilter = THREE.LinearFilter;
    if (!dev) this.renderer.initTexture(t);
    return t;
  }
  /** something changed on its own (a picture finished going up): the page draws a frame */
  onRedraw: (() => void) | null = null;
  /**
   * A place's picture on the graphics card, ahead of being shown (done once per place, when the page is idle): the
   * switch to that place then only points the background at it. Written a slice at a time between frames (it's
   * 32 MB: in one go that holds the page for seconds when the graphics card is busy). Same filters for every place,
   * so the background's shader never changes either.
   */
  prepareEnv(env: Env) {
    let e = this.envTex.get(env.url);
    if (!e) {
      e = this.upEnv(env.px, THREE.RepeatWrapping).then((tex) => ({ tex, sh: projectEnv(env.px.texels, ENV_W, ENV_W / 2) }));
      e.catch(() => this.envTex.delete(env.url));
      this.envTex.set(env.url, e);
    }
    return e;
  }
  /** the place's moving rows, playing (null: none here, the band stands still) */
  setMotion(video: HTMLVideoElement | null) {
    if (video !== this.motionVideo) {
      this.motionTex?.dispose(); this.motionTex = null; this.motionVideo = video;
      if (video) {
        const t = new THREE.VideoTexture(video);
        t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
        t.generateMipmaps = false; t.minFilter = THREE.LinearFilter; t.magFilter = THREE.LinearFilter;
        this.motionTex = t;
      }
    }
    this.applyMotion();
  }
  private applyMotion() {
    const on = !!(this.motionTex && this.motionNode && this.bandOn);
    if (on) this.motionNode!.value = this.motionTex!;
    this.motionOn.value = on ? 1 : 0;
  }
  private showEnv() {
    const on = !!(this.env && this.envOn);
    this.scene.backgroundNode = on ? (this.bandOn ? this.bg : this.env) : null;
    this.ambient();
  }

  /** a picture as a texture, exactly as stored and never holding the page (pic.ts) */
  private async picture(url: string, srgb: boolean, mips = true) {
    const t = await picture(url, this.renderer, srgb, mips);
    // the print stays crisp across the cloth as it turns away: full anisotropic filtering
    t.anisotropy = mips ? this.maxAniso : 1;
    return t;
  }
  private device() { return gpuDevice(this.renderer); }
  private async tx(name: string, srgb: boolean) { return this.picture(ASSET + name, srgb); }
  /** the back and chest prints for one design in one colourway, at print resolution, loaded once */
  private async look(design: string, t: "black" | "cream") {
    const key = `${design}-${t}`;
    if (!this.backTex[key]) {
      const [b, f] = await Promise.all([this.tx(`tex/print-back-${key}.webp`, true), this.frontTex[t] ? Promise.resolve(this.frontTex[t]) : this.tx(`tex/print-front-${t}.webp`, true)]);
      this.backTex[key] = b; this.frontTex[t] = f;
    }
    return [this.backTex[key], this.frontTex[t]] as const;
  }

  async setLook(design: string, t: "black" | "cream") {
    const [b, f] = await this.look(design, t);
    this.current = `${design}-${t}`;
    if (this.nodes) { this.nodes.back.value = this.detailOn && this.fullTex[this.current] || b; this.nodes.front.value = f; }
    this.fabric.value.setRGB(...FABRIC[t], THREE.LinearSRGBColorSpace);
    this.inner.color.setRGB(...FABRIC[t], THREE.LinearSRGBColorSpace);
  }

  /**
   * The full source resolution of a back print. Where the machine can hold it, it comes with its mip chain and
   * full anisotropic filtering and is used at every zoom (the artwork is the point: it's never shown softer than
   * its source allows); on a small device it's one plain level, bound only while zoomed in. One design's full
   * print is kept at a time.
   */
  setFullPrint(design: string, t: "black" | "cream", tex: THREE.Texture) {
    const key = `${design}-${t}`;
    for (const [k, old] of Object.entries(this.fullTex)) if (k !== key) { if (this.nodes?.back.value === old) this.nodes.back.value = this.backTex[k] ?? this.nodes.back.value; old.dispose(); delete this.fullTex[k]; }
    this.fullTex[key] = tex;
    this.detail(this.detailOn);
  }
  private fullTex: Record<string, THREE.Texture> = {};
  hasFull(key: string) { return !!this.fullTex[key]; }
  private detailOn = false;
  detail(on: boolean) {
    this.detailOn = on;
    if (!this.nodes) return;
    const want = (on && this.fullTex[this.current]) || this.backTex[this.current];
    if (want && this.nodes.back.value !== want) this.nodes.back.value = want;
  }
  current = "";
  async printTexture(url: string, mips: boolean) { return this.picture(url, true, mips); }

  private nodes: { back: ReturnType<typeof texture>; front: ReturnType<typeof texture>; normal: ReturnType<typeof texture> } | null = null;
  private normals: Record<string, THREE.Texture> = {};
  private gl: GLTFLoader | null = null;
  private loaded: THREE.Object3D[] = [];
  skinMat = new THREE.MeshPhysicalMaterial({ roughness: 0.48, metalness: 0, specularIntensity: 0.7, sheen: 0 });
  /** someone wearing it: the colours are painted per vertex (skin, denim, eyes), the surfaces differ */
  private painted(o: { roughness: number; spec: number; sheen?: number; sheenColor?: V3 }) {
    const m = new THREE.MeshPhysicalNodeMaterial({ roughness: o.roughness, metalness: 0, specularIntensity: o.spec });
    m.colorNode = vec3(vertexColor());
    m.positionNode = this.motion.node(positionLocal);
    if (o.sheen) { m.sheen = o.sheen; m.sheenRoughness = 0.5; m.sheenColor = new THREE.Color().setRGB(...(o.sheenColor ?? [1, 1, 1]), THREE.LinearSRGBColorSpace); }
    return m;
  }
  // skin: a little oil, and a soft warm fuzz at grazing angles where light goes into skin and comes back out
  personSkin: THREE.MeshPhysicalNodeMaterial = this.painted({ roughness: 0.5, spec: 0.7, sheen: 1, sheenColor: [0.16, 0.07, 0.045] });
  personDenim = this.painted({ roughness: 0.85, spec: 0.5, sheen: 1, sheenColor: [0.035, 0.035, 0.04] });
  personEyes = this.painted({ roughness: 0.12, spec: 0.75 });
  // hair (pipeline/hair.py): the skin's maps paint its strands; it shines, with no warm glow through it
  personHair: THREE.MeshPhysicalNodeMaterial = Object.assign(this.painted({ roughness: 0.7, spec: 0.35 }), { side: THREE.DoubleSide });
  /**
   * The person's skin from its two maps (pipeline/skin.py): colour, and relief + roughness (normal in R, G,
   * roughness in B). The vertex colour, white on the skin, tints it.
   */
  private skinFrom(albedo: ImageBitmap, rn: ImageBitmap, hair = false) {
    const mk = (b: ImageBitmap, srgb: boolean) => {
      const t = new THREE.Texture(b);
      t.flipY = false; t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
      t.anisotropy = this.maxAniso; t.needsUpdate = true; return t;
    };
    const a = texture(mk(albedo, true)), r = texture(mk(rn, false));
    const m = new THREE.MeshPhysicalNodeMaterial({ metalness: 0, specularIntensity: hair ? 0.35 : 0.7 });
    m.colorNode = a.rgb.mul(vec3(vertexColor()));
    m.positionNode = this.motion.node(positionLocal);
    m.roughnessNode = r.b;
    const nx = r.r.mul(2).sub(1), ny = r.g.mul(2).sub(1);
    m.normalNode = normalMap(vec3(r.r, r.g, sqrt(max(float(1).sub(nx.mul(nx)).sub(ny.mul(ny)), 0)).mul(0.5).add(0.5)));
    // the hair is seen from inside too (a bob falling beside the face)
    if (hair) { m.side = THREE.DoubleSide; return m; }
    // a soft warm fuzz at grazing angles, where light goes into skin and comes back out
    m.sheen = 1; m.sheenRoughness = 0.5; m.sheenColor = new THREE.Color().setRGB(0.1, 0.05, 0.037, THREE.LinearSRGBColorSpace);
    return m;
  }
  /**
   * Hair cards (pipeline/cards.py) from their strands (hairtex.py: brightness R, coverage A; the strands run down
   * the picture): the hair's colour per vertex times the strand's brightness, cut out where no strand is (soft-edged
   * with multisampling), the shine stretched across the strands as it is on real hair. Only their fronts are drawn
   * (they face away from the head, and carry its normals, so the pile shades as one mass).
   */
  private cardsFrom(strands: ImageBitmap) {
    const t = new THREE.Texture(strands);
    t.flipY = false; t.colorSpace = THREE.NoColorSpace; t.anisotropy = this.maxAniso; t.needsUpdate = true;
    const s = texture(t);
    const m = new THREE.MeshPhysicalNodeMaterial({ metalness: 0, roughness: 0.5, specularIntensity: 0.4 });
    m.colorNode = vec3(vertexColor()).mul(s.r.mul(0.85).add(0.55));
    // smaller on screen, the strands' coverage averages away in the picture's smaller copies: kept up, so the
    // hair doesn't thin out as it gets further away
    const d = fwidth(uv().mul(1024)), lod = max(log2(max(d.x, d.y)), 0);
    m.opacityNode = s.a.mul(lod.mul(0.25).add(1));
    m.alphaTest = 0.5; m.alphaToCoverage = this.msaa;
    m.anisotropy = 0.5;
    m.positionNode = this.motion.node(positionLocal);
    return m;
  }
  private cardMats = new Map<string, { m: THREE.MeshPhysicalNodeMaterial; b: ImageBitmap }>();
  private skinMats = new Map<string, THREE.MeshPhysicalNodeMaterial>();
  private hairMats = new Map<string, THREE.MeshPhysicalNodeMaterial>();
  stoolMat = new THREE.MeshStandardMaterial({ roughness: 0.7, metalness: 0, color: new THREE.Color(0.05, 0.045, 0.04) });

  /**
   * Loads one simulated tee (a body + size + pose from the fit pipeline, or the shop tee on its ghost form),
   * and the body itself in fit mode; hands back the triangle soup for the path tracer.
   */
  async load(design: string, tee: "black" | "cream", v: Variant): Promise<() => TeeGeometry> {
    // everything at once (most of it is already downloading: the viewer started it before this code arrived)
    // a tee (and person) seen before, or got ready while the page was idle, is still here, on the graphics card,
    // cloth net and all: nothing to fetch or build
    const key = wornKey(v);
    const kept = this.worn.get(key) ?? (await this.pending.get(key)?.catch(() => null)) ?? null;
    const [parts, [c0, o0], normalP, knitT] = await Promise.all([
      kept ? Promise.resolve(null) : this.fetchParts(v),
      this.look(design, tee),
      this.normals[v.size] ? Promise.resolve(this.normals[v.size]) : this.tx(`tex/normal-${v.size}.png`, false),
      this.nodes ? Promise.resolve(null) : this.tx("tex/knit-normal.png", false),
    ]);
    this.normals[v.size] = normalP;
    this.current = `${design}-${tee}`;
    this.fabric.value.setRGB(...FABRIC[tee], THREE.LinearSRGBColorSpace);
    if (!this.nodes && knitT) {
      knitT.wrapS = knitT.wrapT = THREE.RepeatWrapping;
      // the prints, each at its own resolution, laid over the fabric (stored premultiplied: fabric*(1-a) + ink)
      const place = (r: Rect) => uv().sub(vec2(r[0], r[1])).div(vec2(r[2], r[3]));
      const inside = (p: ReturnType<typeof place>) => step(0, p.x).mul(step(p.x, 1)).mul(step(0, p.y)).mul(step(p.y, 1));
      const pB = place(PRINT_BACK), pF = place(PRINT_FRONT);
      const backN = texture(c0, pB), frontN = texture(o0, pF), normalN = texture(normalP);
      const kB = inside(pB), kF = inside(pF);
      const aB = backN.a.mul(kB), aF = frontN.a.mul(kF);
      const ink = aB.add(aF.mul(float(1).sub(aB)));
      const inkRGB = backN.rgb.mul(kB).add(frontN.rgb.mul(kF).mul(float(1).sub(aB)));
      const m = new THREE.MeshPhysicalNodeMaterial({ roughness: 1, metalness: 0, specularIntensity: 0.5 });
      m.colorNode = this.fabric.mul(float(1).sub(ink)).add(inkRGB);
      m.roughnessNode = float(0.92).sub(ink.mul(0.32));
      // ambient occlusion is baked into the mesh (it changes with every size and pose)
      m.aoNode = mix(float(1), vertexColor().r, 0.85);
      // cotton fuzz only off the ink: over the print it reads as a white haze
      m.sheenNode = vec3(float(0.35 * 0.06).mul(float(1).sub(ink)));   // same fitted strength as the path tracer
      m.sheenRoughnessNode = float(0.3);
      // construction relief (rib, stitches) + jersey loops, whiteout blend
      const n1 = normalN.xyz.mul(2).sub(1);
      const kuv = uv().mul(vec2(KNIT_REPEAT[0], KNIT_REPEAT[1]));
      const k = texture(knitT, kuv).xyz.mul(2).sub(1);
      // the jersey loops only where a pixel can show them: once a pixel spans a loop or more they average to
      // flat cotton (as the path tracer's many samples do), instead of flickering to grain as the cloth moves
      const fp = length(fwidth(kuv));
      const knitAmt = this.knit.mul(clamp(float(1.1).sub(fp).div(0.6), 0, 1));
      const blended = normalize(vec3(n1.xy.add(k.xy.mul(knitAmt)), n1.z.mul(k.z)));
      const cloth = clothNodes(this.offsets, this.slopes);
      m.normalNode = cloth.bend(normalMap(blended.mul(0.5).add(0.5)));
      m.positionNode = this.motion.node(cloth.position);
      this.outer = m;
      this.lookNodes = { color: m.colorNode as LookNodes["color"], rough: m.roughnessNode as LookNodes["rough"], sheen: m.sheenNode as LookNodes["sheen"], relief: blended as unknown as LookNodes["relief"], fabric: this.fabric as unknown as LookNodes["fabric"] };
      this.nodes = { back: backN, front: frontN, normal: normalN };
    } else if (this.nodes) {
      this.nodes.back.value = c0; this.nodes.front.value = o0; this.nodes.normal.value = normalP;
    }
    this.inner.color.setRGB(...FABRIC[tee], THREE.LinearSRGBColorSpace);
    if (v.skin) this.skinMat.color.setRGB(...v.skin, THREE.LinearSRGBColorSpace);

    // the last tee/body off the stand (kept, for the next time that view is picked)
    for (const o of this.loaded) this.pivot.remove(o);
    this.loaded = [];
    const w = kept ?? this.take(v, parts!.tee, parts!.body, parts!.skinMaps, parts!.hair);
    this.shown = key;
    if (kept && v.person) {
      this.personSkin = this.skinMats.get(v.person) ?? this.personSkin;
      this.personHair = this.hairMats.get(v.person) ?? this.personHair;
    }
    this.worn.delete(key); this.worn.set(key, w); this.trim();
    for (const r of w.roots) this.pivot.add(r);
    this.loaded = w.roots;
    this.pivot.position.y = w.lift;
    this.motion.setJoints(w.joints);
    this.tris = w.tris;
    // the cloth: on the shop form and on a standing body (raised arms and sitting stay as simulated).
    // The tee goes on screen at once, at rest; the net is built in a worker (once per tee) and takes over when it's ready.
    this.cloth?.stop();
    (this.offsets.image.data as Float32Array).fill(0); this.offsets.needsUpdate = true;
    for (const t of this.slopes) { (t.image.data as Float32Array).fill(0); t.needsUpdate = true; }
    if (w.clothOn) {
      this.cloth ??= new ClothLink(this.offsets, this.slopes);
      this.cloth.start(key, () => ({ meshes: w.tee.map((t) => ({ pos: t.pos, idx: t.idx })), body: w.body }), w.lift,
        !matchMedia("(prefers-reduced-motion: reduce)").matches, (sk) => sk.forEach((x, i) => {
          const [I, W] = w.tee[i].skin;
          (I.array as Float32Array).set(x.I); (W.array as Float32Array).set(x.W); I.needsUpdate = true; W.needsUpdate = true;
        }));
    }
    return () => (w.built ??= soupOf(w.parts, w.lift, w.skinMaps ? { albedo: w.skinMaps[0], rn: w.skinMaps[1], hair: w.hair } : undefined));
  }

  /** each tee (and person) loaded, by what it is: kept on the graphics card so going back to a view costs nothing */
  private worn = new Map<string, Worn>();
  private pending = new Map<string, Promise<Worn>>();
  private shown = "";
  /** most recently used last; the oldest goes once more are kept than the machine should hold (never the one shown) */
  private trim() {
    for (const [k, old] of this.worn) {
      if (this.worn.size <= this.keep) break;
      if (k === this.shown) continue;
      this.worn.delete(k); this.cloth?.forget(k);
      for (const r of old.roots) r.traverse((x) => { const mm = x as THREE.Mesh; if (mm.isMesh) mm.geometry.dispose(); });
    }
  }
  /** a tee's GLB (and its body or person, and the person's skin maps), fetched and parsed */
  private async fetchParts(v: Variant) {
    this.gl ??= new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath("/draco/"));
    const gl = this.gl;
    const glb = async (f: string) => gl.parseAsync(await (await grab(ASSET + f)).arrayBuffer(), ASSET + v.dir + "/");
    // the person's skin maps sit beside its GLB: <name>-skin.webp (colour), <name>-skin-n.webp (relief, roughness)
    const [tee, body, skinMaps] = await Promise.all([
      glb(`${v.dir}/${v.pose}.glb`),
      v.person ? grab(v.person).then(async (b) => gl.parseAsync(await b.arrayBuffer(), ASSET)) : v.body ? glb(`${v.dir}/body-${v.pose}.glb`) : Promise.resolve(null),
      v.person ? Promise.all([bitmap(v.person.replace(/\.glb$/, "-skin.webp")), bitmap(v.person.replace(/\.glb$/, "-skin-n.webp"))]).catch(() => null) : Promise.resolve(null),
    ]);
    // the hair cards' strands sit beside the person's GLB too (<name>-hair.webp), only for a person who has cards
    let hair: ImageBitmap | null = null;
    if (body && v.person && !this.cardMats.has(v.person)) {
      let has = false;
      body.scene.traverse((o) => { if ((o as THREE.Mesh).isMesh && /haircard/i.test(((o as THREE.Mesh).material as THREE.Material)?.name || "")) has = true; });
      if (has) hair = await bitmap(v.person.replace(/\.glb$/, "-hair.webp")).catch(() => null);
    }
    return { tee: tee.scene, body: body?.scene ?? null, skinMaps: skinMaps as [ImageBitmap, ImageBitmap] | null, hair };
  }
  /**
   * A view's tee (and person) loaded and its shaders built while the page is idle, kept off the stand: picking
   * that view then only puts it there. Needs the tee's material (made with the first tee).
   */
  async prepare(v: Variant) {
    const key = wornKey(v);
    if (!this.outer || this.worn.has(key) || this.pending.has(key)) return;
    const p = this.fetchParts(v).then((parts) => this.take(v, parts.tee, parts.body, parts.skinMaps, parts.hair));
    this.pending.set(key, p);
    try {
      const w = await p;
      if (!this.worn.has(key)) { this.worn.set(key, w); this.trim(); }
      const g = new THREE.Group(); for (const r of w.roots) g.add(r);
      await this.renderer.compileAsync(g, this.camera, this.scene).catch(() => {});
      for (const r of w.roots) g.remove(r);
    } finally { this.pending.delete(key); }
  }
  /** how many are kept: the shop tee and a person or two on a desktop, less on a small device */
  keep = 3;

  /**
   * A freshly loaded tee (and body or person) made ready to show: materials on, the cloth's skin attributes, the
   * tee's motion weights from the body under it, and what the cloth and the path tracer need from it. Done once per
   * tee; walks every vertex, so it's all typed arrays and no strings.
   */
  private take(v: Variant, teeRoot: THREE.Object3D, bodyRoot: THREE.Object3D | null, skinMaps: [ImageBitmap, ImageBitmap] | null, hair: ImageBitmap | null): Worn {
    const lift = v.body || v.person ? FLOOR : 0;
    // The path tracer wants the whole scene as one triangle soup; it is only built when it asks (a photo), from
    // what each mesh was when taken: a load only walks what the cloth needs (the tee, the skin under it).
    const parts: Worn["parts"] = [];
    const teeMeshes: { mesh: THREE.Mesh; pos: Float32Array; idx: Uint32Array; plain: boolean }[] = [];
    // the body inside the tee, for the cloth to rest on (garment frame: no lift); not the eyes
    const skinP: Float32Array[] = [], skinN: Float32Array[] = [];
    let triCount = 0;
    const motionPos: Float32Array[] = [], motionW: Float32Array[][] = MOTION_ATTRS.map(() => []);
    let joints: Record<string, [number, number, number]> | null = null;
    const roots: THREE.Object3D[] = [];
    const one = (root: THREE.Object3D, kind: "tee" | "body" | "stool" | "person") => {
      root.updateMatrixWorld(true);
      root.traverse((o) => {
        const mesh = o as THREE.Mesh;
        if (!mesh.isMesh) return;
        const mname = (mesh.material as THREE.Material)?.name || "";
        const isInner = kind === "tee" && /inner/i.test(mname);
        // the person: 4 skin, 5 denim, 6 eyes, 7 hair, 8 the hair cards (the path tracer reads their colour per vertex
        // too, and cuts the cards out by their strands as the live view does)
        if (kind === "person" && /haircard/i.test(mname)) {
          if (!cards) { mesh.visible = false; return; }
          mesh.material = cards.m; Motion.ensure(mesh.geometry);
          parts.push({ mesh, mw: mesh.matrixWorld.clone(), id: 8, person: true });
          triCount += (mesh.geometry.index ? mesh.geometry.index.count : mesh.geometry.attributes.position.count) / 3;
          return;
        }
        const pid = /jeans/i.test(mname) ? 5 : /eye/i.test(mname) ? 6 : /hair/i.test(mname) ? 7 : 4;
        mesh.material = kind === "person" ? [this.personSkin, this.personDenim, this.personEyes, this.personHair][pid - 4]
          : kind === "body" ? this.skinMat : kind === "stool" ? this.stoolMat : isInner ? this.inner : this.outer!;
        const g = mesh.geometry, pa = g.attributes.position, na = g.attributes.normal, mw = mesh.matrixWorld.clone();
        const id = kind === "person" ? pid : kind === "body" ? 2 : kind === "stool" ? 3 : isInner ? 1 : 0;
        parts.push({ mesh, mw, id, person: kind === "person" });
        if (kind === "tee" || kind === "person") Motion.ensure(g);
        triCount += (g.index ? g.index.count : pa.count) / 3;
        const skinOf = kind === "body" || (kind === "person" && pid !== 6 && pid !== 7);
        if (kind !== "tee" && !skinOf) return;
        // every vertex in the garment's frame (and for the skin its outward normal)
        const P = new Float32Array(pa.count * 3), e = mw.elements;
        for (let i = 0; i < pa.count; i++) {
          const x = pa.getX(i), y = pa.getY(i), z = pa.getZ(i);
          P[3 * i] = e[0] * x + e[4] * y + e[8] * z + e[12]; P[3 * i + 1] = e[1] * x + e[5] * y + e[9] * z + e[13]; P[3 * i + 2] = e[2] * x + e[6] * y + e[10] * z + e[14];
        }
        if (kind === "tee") {
          // the cloth works in the pivot's frame; it needs the mesh's own frame to be that frame turned by nothing
          const plain = Math.abs(e[0] - 1) + Math.abs(e[5] - 1) + Math.abs(e[10] - 1) + Math.abs(e[1]) + Math.abs(e[2]) + Math.abs(e[4]) + Math.abs(e[6]) + Math.abs(e[8]) + Math.abs(e[9]) < 1e-4;
          const idx = g.index ? Uint32Array.from(g.index.array) : Uint32Array.from({ length: pa.count }, (_, i) => i);
          teeMeshes.push({ mesh, pos: P, idx, plain });
          return;
        }
        const nm = new THREE.Matrix3().getNormalMatrix(mw).elements, N = new Float32Array(pa.count * 3);
        for (let i = 0; i < pa.count; i++) {
          const x = na.getX(i), y = na.getY(i), z = na.getZ(i);
          const a = nm[0] * x + nm[3] * y + nm[6] * z, b = nm[1] * x + nm[4] * y + nm[7] * z, c = nm[2] * x + nm[5] * y + nm[8] * z, l = Math.hypot(a, b, c) || 1;
          N[3 * i] = a / l; N[3 * i + 1] = b / l; N[3 * i + 2] = c / l;
        }
        skinP.push(P); skinN.push(N);
        if (kind === "person") {
          // the body under the tee, with how it moves, for the tee's own weights
          motionPos.push(P);
          MOTION_ATTRS.forEach((nmA, k) => { const at = g.getAttribute(nmA); const W = new Float32Array(pa.count); for (let i = 0; i < pa.count; i++) W[i] = at.getX(i); motionW[k].push(W); });
          if (typeof mesh.userData.motion === "string") joints = JSON.parse(mesh.userData.motion);
        }
      });
      roots.push(root);
    };
    one(teeRoot, "tee");
    // one skin material per person, made once (a new material is a new shader to build)
    if (skinMaps && v.person) {
      this.personSkin = this.skinMats.get(v.person) ?? this.skinMats.set(v.person, this.skinFrom(skinMaps[0], skinMaps[1])).get(v.person)!;
      this.personHair = this.hairMats.get(v.person) ?? this.hairMats.set(v.person, this.skinFrom(skinMaps[0], skinMaps[1], true)).get(v.person)!;
    }
    // the hair cards: their material made once per person, from the strands fetched beside its GLB (fetchParts)
    let cards = v.person ? this.cardMats.get(v.person) ?? null : null;
    if (!cards && v.person && hair) this.cardMats.set(v.person, (cards = { m: this.cardsFrom(hair), b: hair }));
    if (bodyRoot) one(bodyRoot, v.person ? "person" : "body");
    // the person moves (if their GLB says how), and the tee with them
    if (joints) {
      const body = { pos: concat(motionPos), w: motionW.map(concat) };
      for (const t of teeMeshes) Motion.fromBody(t.mesh.geometry, t.pos, body);
    }
    if (v.body && v.pose === "sit" && v.seat) {
      // a plain stool, its top where the simulation's seat was (Blender y forward -> three z back)
      const box = new THREE.Mesh(new THREE.BoxGeometry(0.46, v.seat, 0.42));
      box.position.set(0, v.seat / 2, -0.04);
      const grp = new THREE.Group(); grp.add(box); one(grp, "stool");
    }
    // each tee vertex's 4 particles and weights: zero (at rest) until the cloth's net is built
    const tee = teeMeshes.map((t) => {
      const g = t.mesh.geometry, nv = t.pos.length / 3;
      const I = new THREE.BufferAttribute(new Float32Array(4 * nv), 4), W = new THREE.BufferAttribute(new Float32Array(4 * nv), 4);
      g.setAttribute("sbI", I); g.setAttribute("sbW", W);
      return { pos: t.pos, idx: t.idx, skin: [I, W] as [THREE.BufferAttribute, THREE.BufferAttribute] };
    });
    const clothOn = v.pose === "stand" && teeMeshes.every((t) => t.plain);
    return {
      roots, parts, tee, body: skinP.length ? { pos: concat(skinP), nrm: concat(skinN) } : null,
      joints, skinMaps, hair: (cards as { b: ImageBitmap } | null)?.b, lift, clothOn, tris: triCount, built: null,
    };
  }

  setCamera(c: Camera) {
    this.target.set(...c.target);
    this.camera.position.set(...c.pos);
    this.camera.lookAt(...c.target);
  }

  /**
   * The view is a game camera walking round someone standing still. Drawn as the person turning in front of a
   * fixed camera (the same picture): in a studio the photographer's lights and paper walk round with the camera,
   * at a venue the place stays put, so its lights turn with the person.
   */
  setView(yaw: number, crop: [number, number, number], w: number, h: number) {
    this.pivot.rotation.y = (yaw * Math.PI) / 180;
    this.rig.rotation.y = this.venue ? this.pivot.rotation.y : 0;
    this.envYaw.value = this.rig.rotation.y;
    if (this.probe.intensity > 0) this.ambient();
    const [cx, cy, z] = crop;
    if (z > 1.0001) {
      // magnify = crop the same frame (no camera move, so the perspective never changes)
      const cw = w / z, ch = h / z;
      const x = ((cx + 1) / 2) * w - cw / 2, y = ((1 - cy) / 2) * h - ch / 2;
      this.camera.setViewOffset(w, h, x, y, cw, ch);
    } else this.camera.clearViewOffset();
    this.camera.updateProjectionMatrix();
  }

  /** advance the cloth (the person stands still while the camera goes round: only the air moves it); true while it moves */
  simulate(dt: number) {
    if (this.flat?.side) return this.flat.tick(dt);
    const alive = this.motion.step(dt);
    return (this.cloth ? this.cloth.step(dt) : false) || alive;
  }

  /** the person alive (false: eased to the pose the tee was simulated in, for photos and reduced motion) */
  setLive(on: boolean) { this.motion.live = on; }

  /**
   * Up close: the tee laid flat on the table, `side` up, settled afresh each time (null: back on its form).
   * Only one of the two is in the scene: the form, its paper and its lights are hidden while the table is out.
   */
  private flat: FlatLay | null = null;
  private lookNodes: LookNodes | null = null;
  private sweepOn = true;
  async setFlat(side: Side | null) {
    if (side && this.lookNodes) {
      const flat = await this.flatLay();
      if (!flat.group.parent) {
        this.scene.add(flat.group);
        // only the window over the table casts shadows (the studio's softboxes don't), so this costs nothing elsewhere
        this.renderer.shadowMap.enabled = true; this.renderer.shadowMap.type = THREE.PCFShadowMap;
      }
      await flat.place(side, { pos: this.camera.position, target: this.target }, matchMedia("(prefers-reduced-motion: reduce)").matches);
      flat.group.visible = true;
    } else if (this.flat) { this.flat.side = null; this.flat.group.visible = false; }
    const on = !!this.flat?.side;
    this.pivot.visible = this.rig.visible = this.hemi.visible = !on;
    this.sweep.visible = this.sweepOn && !on;
    if (on) {
      this.held++;
      try { await this.renderer.compileAsync(this.scene, this.camera).catch(() => {}); } finally { this.held--; }
    }
  }
  private target = new THREE.Vector3(...CAMERA.target);
  private async flatLay() {
    if (!this.flat) { const { FlatLay } = await import("./flat"); this.flat ??= new FlatLay(this.lookNodes!, this.maxAniso, this.renderer); }
    return this.flat;
  }
  /** the table got ready while the page is idle (its pictures decoded and sent, the tee's outline worked out) */
  async prepareFlat() { if (this.lookNodes) await (await this.flatLay()).warm(); }

  setKnit(on: boolean) { this.knit.value = on ? 0.55 : 0; }

  resize(w: number, h: number, dpr: number) {
    this.renderer.setPixelRatio(dpr);
    this.renderer.setSize(w, h, false);
  }

  /** while shaders are being built off the page's thread nothing is drawn (a frame then would build them on it) */
  private held = 0;
  render() { if (!this.held) this.renderer.render(this.scene, this.camera); }
}
