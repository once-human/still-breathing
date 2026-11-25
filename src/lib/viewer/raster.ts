// Real-time view on three.js WebGPURenderer (falls back to WebGL2 by itself where WebGPU is missing).
// It is the preview you drag; the path tracer takes over the moment you let go.
import * as THREE from "three/webgpu";
import { texture, uv, vec2, vec3, float, normalMap, normalize, uniform, mix, vertexColor, step, fwidth, clamp, length, normalWorldGeometry, atan, asin, cos, sin, sqrt, max } from "three/tsl";
import { PRINT_BACK, PRINT_FRONT, type Rect } from "./print";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { RectAreaLightTexturesLib } from "three/addons/lights/RectAreaLightTexturesLib.js";
import { CAMERA, VFOV, ASPECT, SWEEP, FLOOR, KNIT_REPEAT, SCENES, lightFrame, radiance, type Camera, type Scene, type V3 } from "./scene";
import { ENV_W, projectEnv, turnSH } from "./sh";
import type { TeeGeometry } from "./pathtracer";
import { grab, bitmap, rawImage, type Pixels } from "./grab";
import { ClothLink, offsetTexture, slopeTextures, clothNodes } from "./cloth";
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

/** a place's picture, ready to draw: the full picture, and its 64 x 32 linear version for the light probe */
export type Env = { url: string; px: Pixels };

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
  renderer: THREE.WebGPURenderer;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera((VFOV * 180) / Math.PI, ASPECT, 0.05, 40);
  pivot = new THREE.Group();
  /** the lights; at a venue they turn with the pivot, so the camera walks round a place that stays put */
  rig = new THREE.Group();
  private venue = false;
  /** the place around the person (a 360 degree picture), drawn behind everything at a venue */
  private env: ReturnType<typeof texture> | null = null;
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
  private envTex = new Map<string, { tex: THREE.Texture; sh: Float64Array }>();
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
    this.renderer = new THREE.WebGPURenderer({ canvas, antialias: (globalThis.devicePixelRatio || 1) < 1.5, alpha: false });
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
    this.inner.positionNode = this.clothed();
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
  setEnv(env: Env | null) {
    this.probeYaw = NaN;
    if (!env) { this.envSH = null; this.env = null; this.showEnv(); return; }
    const { tex: t, sh } = this.prepareEnv(env);
    this.envSH = sh;
    if (this.env) { this.env.value = t; this.showEnv(); return; }
    const d = normalize(normalWorldGeometry);
    const c = cos(this.envYaw), sn = sin(this.envYaw);
    const x = c.mul(d.x).sub(sn.mul(d.z)), z = sn.mul(d.x).add(c.mul(d.z));
    const u = float(0.5).sub(atan(x, z).div(2 * Math.PI));
    const v = float(0.5).sub(asin(clamp(d.y, -1, 1)).div(Math.PI));
    this.env = texture(t, vec2(u, v));
    this.showEnv();
  }
  /**
   * A place's picture on the graphics card, ahead of being shown (done once per place, when the page is idle): the
   * switch to that place then only points the background at it. Same filters for every place, so the background's
   * shader never changes either.
   */
  prepareEnv(env: Env) {
    let e = this.envTex.get(env.url);
    if (!e) {
      // raw bytes decoded in a worker: uploaded as a plain buffer copy (an image upload can stall on the graphics process)
      const t = new THREE.DataTexture(env.px.data, env.px.width, env.px.height, THREE.RGBAFormat, THREE.UnsignedByteType);
      t.flipY = false; t.colorSpace = THREE.SRGBColorSpace; t.wrapS = THREE.RepeatWrapping; t.wrapT = THREE.ClampToEdgeWrapping;
      // no mips: the picture is only ever magnified, and mips would draw a seam where u wraps round
      t.generateMipmaps = false; t.minFilter = THREE.LinearFilter; t.magFilter = THREE.LinearFilter; t.needsUpdate = true;
      this.renderer.initTexture(t);
      e = { tex: t, sh: projectEnv(env.px.texels, ENV_W, ENV_W / 2) };
      this.envTex.set(env.url, e);
    }
    return e;
  }
  private showEnv() {
    const on = !!(this.env && this.envOn);
    this.scene.backgroundNode = on ? this.env : null;
    this.ambient();
  }

  /**
   * A picture as a texture, decoded in a Worker into raw bytes and uploaded as a plain buffer copy (an image upload
   * can hold the page while the graphics process converts it); the ordinary image path where the browser can't.
   * Same filters either way (the default mipmapped ones), so swapping one for another never changes a shader.
   */
  private async picture(url: string) {
    const raw = await rawImage(url);
    if (!raw) return new THREE.Texture(await bitmap(url));
    const t = new THREE.DataTexture(raw.data, raw.width, raw.height, THREE.RGBAFormat, THREE.UnsignedByteType);
    t.magFilter = THREE.LinearFilter; t.minFilter = THREE.LinearMipmapLinearFilter; t.generateMipmaps = true;
    return t;
  }
  private async tx(name: string, srgb: boolean) {
    const t = await this.picture(ASSET + name);
    t.flipY = false; t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    // the print stays crisp across the cloth as it turns away: full anisotropic filtering
    t.anisotropy = this.maxAniso; t.needsUpdate = true; return t;
  }
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
  async printTexture(url: string, mips: boolean) {
    const t = await this.picture(url);
    t.flipY = false; t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.LinearFilter;
    if (mips) { t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; t.anisotropy = this.maxAniso; }
    else { t.generateMipmaps = false; t.minFilter = THREE.LinearFilter; t.anisotropy = 1; }
    t.needsUpdate = true;
    return t;
  }

  private nodes: { back: ReturnType<typeof texture>; front: ReturnType<typeof texture>; normal: ReturnType<typeof texture> } | null = null;
  private normals: Record<string, THREE.Texture> = {};
  private gl: GLTFLoader | null = null;
  private loaded: THREE.Object3D[] = [];
  skinMat = new THREE.MeshPhysicalMaterial({ roughness: 0.48, metalness: 0, specularIntensity: 0.7, sheen: 0 });
  /** someone wearing it: the colours are painted per vertex (skin, denim, eyes), the surfaces differ */
  private painted(o: { roughness: number; spec: number; sheen?: number; sheenColor?: V3 }) {
    const m = new THREE.MeshPhysicalNodeMaterial({ roughness: o.roughness, metalness: 0, specularIntensity: o.spec });
    m.colorNode = vec3(vertexColor());
    if (o.sheen) { m.sheen = o.sheen; m.sheenRoughness = 0.5; m.sheenColor = new THREE.Color().setRGB(...(o.sheenColor ?? [1, 1, 1]), THREE.LinearSRGBColorSpace); }
    return m;
  }
  // skin: a little oil, and a soft warm fuzz at grazing angles where light goes into skin and comes back out
  personSkin: THREE.MeshPhysicalNodeMaterial = this.painted({ roughness: 0.5, spec: 0.7, sheen: 1, sheenColor: [0.16, 0.07, 0.045] });
  personDenim = this.painted({ roughness: 0.85, spec: 0.5, sheen: 1, sheenColor: [0.035, 0.035, 0.04] });
  personEyes = this.painted({ roughness: 0.12, spec: 0.75 });
  // hair (pipeline/hair.py): the skin's maps paint its strands; it shines, with no warm glow through it
  personHair: THREE.MeshPhysicalNodeMaterial = this.painted({ roughness: 0.45, spec: 0.8 });
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
    const m = new THREE.MeshPhysicalNodeMaterial({ metalness: 0, specularIntensity: hair ? 0.8 : 0.7 });
    m.colorNode = a.rgb.mul(vec3(vertexColor()));
    m.roughnessNode = r.b;
    const nx = r.r.mul(2).sub(1), ny = r.g.mul(2).sub(1);
    m.normalNode = normalMap(vec3(r.r, r.g, sqrt(max(float(1).sub(nx.mul(nx)).sub(ny.mul(ny)), 0)).mul(0.5).add(0.5)));
    if (hair) return m;
    // a soft warm fuzz at grazing angles, where light goes into skin and comes back out
    m.sheen = 1; m.sheenRoughness = 0.5; m.sheenColor = new THREE.Color().setRGB(0.16, 0.07, 0.045, THREE.LinearSRGBColorSpace);
    return m;
  }
  private skinMats = new Map<string, THREE.MeshPhysicalNodeMaterial>();
  private hairMats = new Map<string, THREE.MeshPhysicalNodeMaterial>();
  stoolMat = new THREE.MeshStandardMaterial({ roughness: 0.7, metalness: 0, color: new THREE.Color(0.05, 0.045, 0.04) });

  /**
   * Loads one simulated tee (a body + size + pose from the fit pipeline, or the shop tee on its ghost form),
   * and the body itself in fit mode; hands back the triangle soup for the path tracer.
   */
  async load(design: string, tee: "black" | "cream", v: Variant): Promise<() => TeeGeometry> {
    this.gl ??= new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath("/draco/"));
    const gl = this.gl;
    const glb = async (f: string) => gl.parseAsync(await (await grab(ASSET + f)).arrayBuffer(), ASSET + v.dir + "/");
    // everything at once (most of it is already downloading: the viewer started it before this code arrived)
    // the person's skin maps sit beside its GLB: <name>-skin.webp (colour), <name>-skin-n.webp (relief, roughness)
    const skinMapsP = v.person ? Promise.all([bitmap(v.person.replace(/\.glb$/, "-skin.webp")), bitmap(v.person.replace(/\.glb$/, "-skin-n.webp"))]).catch(() => null) : null;
    const [gltf, bodyGltf, [c0, o0], normalP, knitT] = await Promise.all([
      glb(`${v.dir}/${v.pose}.glb`),
      v.person ? grab(v.person).then(async (b) => gl.parseAsync(await b.arrayBuffer(), ASSET)) : v.body ? glb(`${v.dir}/body-${v.pose}.glb`) : Promise.resolve(null),
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
      m.positionNode = cloth.position;
      this.outer = m;
      this.lookNodes = { color: m.colorNode as LookNodes["color"], rough: m.roughnessNode as LookNodes["rough"], sheen: m.sheenNode as LookNodes["sheen"], relief: blended as unknown as LookNodes["relief"], fabric: this.fabric as unknown as LookNodes["fabric"] };
      this.nodes = { back: backN, front: frontN, normal: normalN };
    } else if (this.nodes) {
      this.nodes.back.value = c0; this.nodes.front.value = o0; this.nodes.normal.value = normalP;
    }
    this.inner.color.setRGB(...FABRIC[tee], THREE.LinearSRGBColorSpace);
    if (v.skin) this.skinMat.color.setRGB(...v.skin, THREE.LinearSRGBColorSpace);

    // swap out the previous tee/body
    for (const o of this.loaded) {
      this.pivot.remove(o);
      o.traverse((x) => { const mm = x as THREE.Mesh; if (mm.isMesh) mm.geometry.dispose(); });
    }
    this.loaded = [];
    const lift = v.body || v.person ? FLOOR : 0;
    this.pivot.position.y = lift;

    // The path tracer wants the whole scene as one triangle soup; it is only built when it asks (a photo), from
    // what each mesh was when taken: a load only walks what the cloth needs (the tee, the skin under it).
    const parts: { mesh: THREE.Mesh; mw: THREE.Matrix4; id: number; person: boolean }[] = [];
    const teeMeshes: { mesh: THREE.Mesh; pos: Float32Array; idx: ArrayLike<number>; plain: boolean }[] = [];
    // the body inside the tee, for the cloth to rest on (garment frame: no lift); not the eyes
    const skinP: number[] = [], skinN: number[] = [];
    let triCount = 0;
    const take = (root: THREE.Object3D, kind: "tee" | "body" | "stool" | "person") => {
      root.updateMatrixWorld(true);
      root.traverse((o) => {
        const mesh = o as THREE.Mesh;
        if (!mesh.isMesh) return;
        const mname = (mesh.material as THREE.Material)?.name || "";
        const isInner = kind === "tee" && /inner/i.test(mname);
        // the person: 4 skin, 5 denim, 6 eyes, 7 hair (the path tracer reads their colour per vertex too)
        const pid = /jeans/i.test(mname) ? 5 : /eye/i.test(mname) ? 6 : /hair/i.test(mname) ? 7 : 4;
        mesh.material = kind === "person" ? [this.personSkin, this.personDenim, this.personEyes, this.personHair][pid - 4]
          : kind === "body" ? this.skinMat : kind === "stool" ? this.stoolMat : isInner ? this.inner : this.outer!;
        const g = mesh.geometry, pa = g.attributes.position, na = g.attributes.normal, mw = mesh.matrixWorld.clone();
        const id = kind === "person" ? pid : kind === "body" ? 2 : kind === "stool" ? 3 : isInner ? 1 : 0;
        parts.push({ mesh, mw, id, person: kind === "person" });
        triCount += (g.index ? g.index.count : pa.count) / 3;
        const vv = new THREE.Vector3();
        if (kind === "tee") {
          // the cloth works in the pivot's frame; it needs the mesh's own frame to be that frame turned by nothing
          const e = mw.elements, plain = Math.abs(e[0] - 1) + Math.abs(e[5] - 1) + Math.abs(e[10] - 1) + Math.abs(e[1]) + Math.abs(e[2]) + Math.abs(e[4]) + Math.abs(e[6]) + Math.abs(e[8]) + Math.abs(e[9]) < 1e-4;
          const pos = new Float32Array(pa.count * 3);
          for (let i = 0; i < pa.count; i++) { vv.fromBufferAttribute(pa, i).applyMatrix4(mw); pos[3 * i] = vv.x; pos[3 * i + 1] = vv.y; pos[3 * i + 2] = vv.z; }
          teeMeshes.push({ mesh, pos, idx: g.index ? g.index.array : Array.from({ length: pa.count }, (_, i) => i), plain });
        }
        if (kind === "body" || (kind === "person" && pid !== 6 && pid !== 7)) {
          const nm = new THREE.Matrix3().getNormalMatrix(mw);
          for (let i = 0; i < pa.count; i++) {
            vv.fromBufferAttribute(pa, i).applyMatrix4(mw); skinP.push(vv.x, vv.y, vv.z);
            vv.fromBufferAttribute(na, i).applyMatrix3(nm).normalize(); skinN.push(vv.x, vv.y, vv.z);
          }
        }
      });
      this.pivot.add(root); this.loaded.push(root);
    };
    take(gltf.scene, "tee");
    // the cloth: on the shop form and on a standing body (raised arms and sitting stay as simulated).
    // The tee goes on screen at once, at rest; the net is built in a worker and takes over when it's ready.
    this.cloth?.stop();
    const skins: THREE.BufferAttribute[][] = [];
    for (const t of teeMeshes) {
      const g = t.mesh.geometry, nv = t.pos.length / 3;
      const I = new THREE.BufferAttribute(new Float32Array(4 * nv), 4), W = new THREE.BufferAttribute(new Float32Array(4 * nv), 4);
      g.setAttribute("sbI", I); g.setAttribute("sbW", W); skins.push([I, W]);
    }
    (this.offsets.image.data as Float32Array).fill(0); this.offsets.needsUpdate = true;
    for (const t of this.slopes) { (t.image.data as Float32Array).fill(0); t.needsUpdate = true; }
    const clothOn = v.pose === "stand" && teeMeshes.every((t) => t.plain);
    const skinMaps = skinMapsP ? await skinMapsP : null;
    // one skin material per person, made once (a new material is a new shader to build)
    if (skinMaps && v.person) {
      this.personSkin = this.skinMats.get(v.person) ?? this.skinMats.set(v.person, this.skinFrom(skinMaps[0], skinMaps[1])).get(v.person)!;
      this.personHair = this.hairMats.get(v.person) ?? this.hairMats.set(v.person, this.skinFrom(skinMaps[0], skinMaps[1], true)).get(v.person)!;
    }
    if (bodyGltf) take(bodyGltf.scene, v.person ? "person" : "body");
    if (v.body && v.pose === "sit" && v.seat) {
      // a plain stool, its top where the simulation's seat was (Blender y forward -> three z back)
      const box = new THREE.Mesh(new THREE.BoxGeometry(0.46, v.seat, 0.42));
      box.position.set(0, v.seat / 2, -0.04);
      const grp = new THREE.Group(); grp.add(box); take(grp, "stool");
    }
    // the net and the cloth on their own thread, once the skin under the tee is known (the tee is on screen and
    // turning meanwhile, at rest; the cloth takes over when the net is ready)
    if (clothOn) {
      this.cloth ??= new ClothLink(this.offsets, this.slopes);
      this.cloth.start(teeMeshes.map((t) => ({ pos: t.pos, idx: Uint32Array.from(t.idx) })), skinP.length ? { pos: new Float32Array(skinP), nrm: new Float32Array(skinN) } : null,
        lift, !matchMedia("(prefers-reduced-motion: reduce)").matches, (sk) => sk.forEach((x, i) => {
          const [I, W] = skins[i];
          (I.array as Float32Array).set(x.I); (W.array as Float32Array).set(x.W); I.needsUpdate = true; W.needsUpdate = true;
        }));
    }
    this.tris = triCount;
    let built: TeeGeometry | null = null;
    return () => (built ??= soupOf(parts, lift, skinMaps ? { albedo: skinMaps[0], rn: skinMaps[1] } : undefined));
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
    return this.cloth ? this.cloth.step(dt) : false;
  }

  /**
   * Up close: the tee laid flat on the table, `side` up, settled afresh each time (null: back on its form).
   * Only one of the two is in the scene: the form, its paper and its lights are hidden while the table is out.
   */
  private flat: FlatLay | null = null;
  private lookNodes: LookNodes | null = null;
  private sweepOn = true;
  async setFlat(side: Side | null) {
    if (side && this.lookNodes) {
      if (!this.flat) {
        const { FlatLay } = await import("./flat");
        this.flat = new FlatLay(this.lookNodes, this.maxAniso);
        this.scene.add(this.flat.group);
        // only the window over the table casts shadows (the studio's softboxes don't), so this costs nothing elsewhere
        this.renderer.shadowMap.enabled = true; this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      }
      await this.flat.place(side, { pos: this.camera.position, target: this.target }, matchMedia("(prefers-reduced-motion: reduce)").matches);
      this.flat.group.visible = true;
    } else if (this.flat) { this.flat.side = null; this.flat.group.visible = false; }
    const on = !!this.flat?.side;
    this.pivot.visible = this.rig.visible = this.hemi.visible = !on;
    this.sweep.visible = this.sweepOn && !on;
    if (on) await this.renderer.compileAsync(this.scene, this.camera).catch(() => {});
  }
  private target = new THREE.Vector3(...CAMERA.target);

  setKnit(on: boolean) { this.knit.value = on ? 0.55 : 0; }

  resize(w: number, h: number, dpr: number) {
    this.renderer.setPixelRatio(dpr);
    this.renderer.setSize(w, h, false);
  }

  render() { this.renderer.render(this.scene, this.camera); }
}
