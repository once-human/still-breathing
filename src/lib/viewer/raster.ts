// Real-time view on three.js WebGPURenderer (falls back to WebGL2 by itself where WebGPU is missing).
// It is the preview you drag; the path tracer takes over the moment you let go.
import * as THREE from "three/webgpu";
import { texture, uv, vec2, vec3, float, normalMap, normalize, uniform, mix, vertexColor, step, fwidth, clamp, length, normalWorldGeometry, atan, asin, cos, sin } from "three/tsl";
import { PRINT_BACK, PRINT_FRONT, type Rect } from "./print";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { RectAreaLightTexturesLib } from "three/addons/lights/RectAreaLightTexturesLib.js";
import { CAMERA, VFOV, ASPECT, SWEEP, FLOOR, KNIT_REPEAT, lightFrame, radiance, type Camera, type Scene, type V3 } from "./scene";
import type { TeeGeometry } from "./pathtracer";
import { grab, bitmap } from "./grab";
import { Cloth, buildNetAsync, offsetTexture, slopeTextures, clothNodes } from "./cloth";

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

/** the probe's view of the place: 64 x 32 texels, linear radiance (the canvas averages in sRGB; close enough for light) */
const ENV_W = 64;
function envTexels(bmp: ImageBitmap) {
  const W = ENV_W, H = ENV_W / 2;
  const cv = new OffscreenCanvas(W, H), cx = cv.getContext("2d")!;
  cx.imageSmoothingQuality = "high"; cx.drawImage(bmp, 0, 0, W, H);
  const px = cx.getImageData(0, 0, W, H).data, out = new Float32Array(W * H * 3);
  for (let i = 0; i < W * H; i++)
    for (let c = 0; c < 3; c++) {
      const v = px[i * 4 + c] / 255;
      out[i * 3 + c] = v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    }
  return out;
}

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
  lights: THREE.RectAreaLight[] = [];
  hemi = new THREE.HemisphereLight(0xf4f2ee, 0x6d6a64, 0.15);
  /** the place's picture as light on the person (its spherical harmonics, turned with the place) */
  probe = new THREE.LightProbe(undefined, 0);
  /** the picture, small and linear, for the probe: radiance per texel, rows from straight up */
  private envPix: Float32Array | null = null;
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
  private loadToken = 0;
  cloth: Cloth | null = null;
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
    for (const l of this.lights) this.rig.remove(l);
    this.venue = !!s.venue; this.rig.rotation.y = this.venue ? this.pivot.rotation.y : 0;
    const k = cream ? s.creamK : 1;
    this.lights = s.lights.map((l) => {
      const fr = lightFrame(l, s.aim), L = radiance(l, k);
      const peak = Math.max(...L);
      const rl = new THREE.RectAreaLight(new THREE.Color(L[0] / peak, L[1] / peak, L[2] / peak), peak, l.size[0], l.size[1]);
      rl.position.set(...l.pos);
      rl.lookAt(l.pos[0] + fr.n[0], l.pos[1] + fr.n[1], l.pos[2] + fr.n[2]);
      this.rig.add(rl);
      return rl;
    });
    this.paperMat.color.setRGB(...s.paper, THREE.LinearSRGBColorSpace);
    this.sweep.visible = !s.open;
    this.scene.background = new THREE.Color().setRGB(...s.world, THREE.LinearSRGBColorSpace);
    this.envOn = !!s.env; this.envLight = s.envLight ?? 0; this.world = s.world; this.showEnv();
  }

  /**
   * Light from all round: the place's picture where it lights the person (projected on spherical harmonics, which
   * three.js turns into the irradiance a surface facing each way receives), otherwise the uniform world light.
   */
  private ambient() {
    const pix = this.envPix, lit = !!(pix && this.envOn && this.envLight > 0);
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
    const sh = this.probe.sh; sh.zero();
    const c = Math.cos(yaw), sn = Math.sin(yaw), W = ENV_W, H = ENV_W / 2, basis = new Array<number>(9).fill(0);
    const d = new THREE.Vector3(), dw = (2 * Math.PI / W) * (Math.PI / H);
    for (let j = 0; j < H; j++) {
      const lat = Math.PI / 2 - ((j + 0.5) / H) * Math.PI, cl = Math.cos(lat), y = Math.sin(lat), dO = dw * cl;
      for (let i = 0; i < W; i++) {
        // the texel's direction in the place (u = 0.5 - atan2(x, z) / 2pi), then turned into the world with the place
        const a = (0.5 - (i + 0.5) / W) * 2 * Math.PI, px = Math.sin(a) * cl, pz = Math.cos(a) * cl;
        d.set(c * px + sn * pz, y, -sn * px + c * pz);
        THREE.SphericalHarmonics3.getBasisAt(d, basis);
        const o = (j * W + i) * 3;
        for (let k = 0; k < 9; k++) {
          const b = basis[k] * dO;
          sh.coefficients[k].x += pix![o] * b; sh.coefficients[k].y += pix![o + 1] * b; sh.coefficients[k].z += pix![o + 2] * b;
        }
      }
    }
    this.probe.intensity = this.envLight;
  }

  /**
   * The 360 degree picture of the place (stage ahead of the person, the hall behind). Looked up by direction the
   * same way the path tracer does: u = 0.5 - atan2(x, z) / 2pi (the stage, +z, in the middle), v = 0 straight up.
   * It turns with the person, as the lights do (a game camera walking round a place that stays put).
   */
  setEnv(bmp: ImageBitmap | null) {
    this.envPix = bmp ? envTexels(bmp) : null; this.probeYaw = NaN;
    if (!bmp) { this.env = null; this.showEnv(); return; }
    const t = new THREE.Texture(bmp);
    t.flipY = false; t.colorSpace = THREE.SRGBColorSpace; t.wrapS = THREE.RepeatWrapping; t.wrapT = THREE.ClampToEdgeWrapping;
    // no mips: the picture is only ever magnified, and mips would draw a seam where u wraps round
    t.generateMipmaps = false; t.minFilter = THREE.LinearFilter; t.magFilter = THREE.LinearFilter; t.needsUpdate = true;
    if (this.env) { this.env.value = t; this.showEnv(); return; }
    const d = normalize(normalWorldGeometry);
    const c = cos(this.envYaw), sn = sin(this.envYaw);
    const x = c.mul(d.x).sub(sn.mul(d.z)), z = sn.mul(d.x).add(c.mul(d.z));
    const u = float(0.5).sub(atan(x, z).div(2 * Math.PI));
    const v = float(0.5).sub(asin(clamp(d.y, -1, 1)).div(Math.PI));
    this.env = texture(t, vec2(u, v));
    this.showEnv();
  }
  private showEnv() {
    const on = !!(this.env && this.envOn);
    this.scene.backgroundNode = on ? this.env : null;
    this.ambient();
  }

  private async tx(name: string, srgb: boolean) {
    const t = new THREE.Texture(await bitmap(ASSET + name));
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
   * The full source resolution of a back print, for close up. Close up the print is only ever magnified, so it
   * needs no mip chain and no anisotropic filtering: uploaded as one plain level (a third less memory, no mip
   * build), and only bound while zoomed in; zoomed out, the regular print with its mips is used.
   */
  setFullPrint(design: string, t: "black" | "cream", tex: THREE.Texture) {
    this.fullTex[`${design}-${t}`] = tex;
    this.detail(this.detailOn);
  }
  private fullTex: Record<string, THREE.Texture> = {};
  private detailOn = false;
  detail(on: boolean) {
    this.detailOn = on;
    if (!this.nodes) return;
    const want = (on && this.fullTex[this.current]) || this.backTex[this.current];
    if (want && this.nodes.back.value !== want) this.nodes.back.value = want;
  }
  current = "";
  async printTexture(url: string) {
    const t = new THREE.Texture(await bitmap(url));
    t.flipY = false; t.colorSpace = THREE.SRGBColorSpace;
    t.generateMipmaps = false; t.minFilter = THREE.LinearFilter; t.magFilter = THREE.LinearFilter; t.anisotropy = 1;
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
  personSkin = this.painted({ roughness: 0.5, spec: 0.7, sheen: 1, sheenColor: [0.16, 0.07, 0.045] });
  personDenim = this.painted({ roughness: 0.85, spec: 0.5, sheen: 1, sheenColor: [0.035, 0.035, 0.04] });
  personEyes = this.painted({ roughness: 0.12, spec: 0.75 });
  stoolMat = new THREE.MeshStandardMaterial({ roughness: 0.7, metalness: 0, color: new THREE.Color(0.05, 0.045, 0.04) });

  /**
   * Loads one simulated tee (a body + size + pose from the fit pipeline, or the shop tee on its ghost form),
   * and the body itself in fit mode; hands back the triangle soup for the path tracer.
   */
  async load(design: string, tee: "black" | "cream", v: Variant): Promise<TeeGeometry> {
    this.gl ??= new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath("/draco/"));
    const gl = this.gl;
    const glb = async (f: string) => gl.parseAsync(await (await grab(ASSET + f)).arrayBuffer(), ASSET + v.dir + "/");
    // everything at once (most of it is already downloading: the viewer started it before this code arrived)
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

    const P: number[] = [], N: number[] = [], UV: number[] = [], I: number[] = [], M: number[] = [], C: number[] = [];
    const teeMeshes: { mesh: THREE.Mesh; pos: Float32Array; idx: ArrayLike<number>; plain: boolean }[] = [];
    // the body inside the tee, for the cloth to rest on (garment frame: no lift); not the eyes
    const skinP: number[] = [], skinN: number[] = [];
    const take = (root: THREE.Object3D, kind: "tee" | "body" | "stool" | "person") => {
      root.updateMatrixWorld(true);
      root.traverse((o) => {
        const mesh = o as THREE.Mesh;
        if (!mesh.isMesh) return;
        const mname = (mesh.material as THREE.Material)?.name || "";
        const isInner = kind === "tee" && /inner/i.test(mname);
        // the person: 4 skin, 5 denim, 6 eyes (the path tracer reads their colour per vertex too)
        const pid = /jeans/i.test(mname) ? 5 : /eye/i.test(mname) ? 6 : 4;
        mesh.material = kind === "person" ? [this.personSkin, this.personDenim, this.personEyes][pid - 4]
          : kind === "body" ? this.skinMat : kind === "stool" ? this.stoolMat : isInner ? this.inner : this.outer!;
        const g = mesh.geometry, pa = g.attributes.position, na = g.attributes.normal, ua = g.attributes.uv, ca = g.attributes.color;
        const base = P.length / 3, mw = mesh.matrixWorld, nm = new THREE.Matrix3().getNormalMatrix(mw);
        const vv = new THREE.Vector3();
        for (let i = 0; i < pa.count; i++) {
          vv.fromBufferAttribute(pa, i).applyMatrix4(mw); P.push(vv.x, vv.y + lift, vv.z);
          vv.fromBufferAttribute(na, i).applyMatrix3(nm).normalize(); N.push(vv.x, vv.y, vv.z);
          UV.push(ua ? ua.getX(i) : 0, ua ? ua.getY(i) : 0);
          if (kind === "person" && ca) C.push(ca.getX(i), ca.getY(i), ca.getZ(i)); else C.push(1, 1, 1);
          if ((kind === "body" || (kind === "person" && pid !== 6))) {
            skinP.push(P[P.length - 3], P[P.length - 2] - lift, P[P.length - 1]);
            skinN.push(N[N.length - 3], N[N.length - 2], N[N.length - 1]);
          }
        }
        const ix = g.index ? Array.from(g.index.array) : Array.from({ length: pa.count }, (_, i) => i);
        for (let i = 0; i < ix.length; i++) I.push(ix[i] + base);
        if (kind === "tee") {
          // the cloth works in the pivot's frame; it needs the mesh's own frame to be that frame turned by nothing
          const e = mw.elements, plain = Math.abs(e[0] - 1) + Math.abs(e[5] - 1) + Math.abs(e[10] - 1) + Math.abs(e[1]) + Math.abs(e[2]) + Math.abs(e[4]) + Math.abs(e[6]) + Math.abs(e[8]) + Math.abs(e[9]) < 1e-4;
          const pos = new Float32Array(pa.count * 3);
          for (let i = 0; i < pa.count; i++) { pos[3 * i] = P[3 * (base + i)]; pos[3 * i + 1] = P[3 * (base + i) + 1] - lift; pos[3 * i + 2] = P[3 * (base + i) + 2]; }
          teeMeshes.push({ mesh, pos, idx: ix, plain });
        }
        const id = kind === "person" ? pid : kind === "body" ? 2 : kind === "stool" ? 3 : isInner ? 1 : 0;
        for (let i = 0; i < ix.length / 3; i++) M.push(id);
      });
      this.pivot.add(root); this.loaded.push(root);
    };
    take(gltf.scene, "tee");
    // the cloth: on the shop form and on a standing body (raised arms and sitting stay as simulated).
    // The tee goes on screen at once, at rest; the net is built in a worker and takes over when it's ready.
    this.cloth = null;
    const token = ++this.loadToken;
    const skins: THREE.BufferAttribute[][] = [];
    for (const t of teeMeshes) {
      const g = t.mesh.geometry, nv = t.pos.length / 3;
      const I = new THREE.BufferAttribute(new Float32Array(4 * nv), 4), W = new THREE.BufferAttribute(new Float32Array(4 * nv), 4);
      g.setAttribute("sbI", I); g.setAttribute("sbW", W); skins.push([I, W]);
    }
    (this.offsets.image.data as Float32Array).fill(0); this.offsets.needsUpdate = true;
    for (const t of this.slopes) { (t.image.data as Float32Array).fill(0); t.needsUpdate = true; }
    if (v.pose === "stand" && teeMeshes.every((t) => t.plain)) {
      buildNetAsync(teeMeshes.map((t) => ({ pos: t.pos, idx: Uint32Array.from(t.idx) }))).then((net) => {
        if (token !== this.loadToken) return;
        net.skins.forEach((sk, i) => {
          const [I, W] = skins[i];
          (I.array as Float32Array).set(sk.I); (W.array as Float32Array).set(sk.W); I.needsUpdate = true; W.needsUpdate = true;
        });
        const cloth = new Cloth(net, this.offsets, this.slopes);
        if (skinP.length) cloth.setBody(new Float32Array(skinP), new Float32Array(skinN));
        cloth.wind = !matchMedia("(prefers-reduced-motion: reduce)").matches;
        this.cloth = cloth;
      }).catch((e) => console.info("cloth off", e));
    }
    if (bodyGltf) take(bodyGltf.scene, v.person ? "person" : "body");
    if (v.body && v.pose === "sit" && v.seat) {
      // a plain stool, its top where the simulation's seat was (Blender y forward -> three z back)
      const box = new THREE.Mesh(new THREE.BoxGeometry(0.46, v.seat, 0.42));
      box.position.set(0, v.seat / 2, -0.04);
      const grp = new THREE.Group(); grp.add(box); take(grp, "stool");
    }
    this.tris = I.length / 3;
    return { pos: new Float32Array(P), nrm: new Float32Array(N), uv: new Float32Array(UV), idx: new Uint32Array(I), mat: new Uint8Array(M), col: new Float32Array(C) };
  }

  setCamera(c: Camera) {
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

  private still = new THREE.Matrix3();
  /** advance the cloth (the person stands still while the camera goes round: only the air moves it); true while it moves */
  simulate(dt: number) {
    if (!this.cloth) return false;
    this.cloth.setPose(this.still, this.pivot.position, 1, dt);
    return this.cloth.step(dt);
  }

  setKnit(on: boolean) { this.knit.value = on ? 0.55 : 0; }

  resize(w: number, h: number, dpr: number) {
    this.renderer.setPixelRatio(dpr);
    this.renderer.setSize(w, h, false);
  }

  render() { this.renderer.render(this.scene, this.camera); }
}
