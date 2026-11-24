// Real-time view on three.js WebGPURenderer (falls back to WebGL2 by itself where WebGPU is missing).
// It is the preview you drag; the path tracer takes over the moment you let go.
import * as THREE from "three/webgpu";
import { texture, uv, vec2, vec3, float, normalMap, normalize, uniform, mix, vertexColor } from "three/tsl";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { RectAreaLightTexturesLib } from "three/addons/lights/RectAreaLightTexturesLib.js";
import { CAMERA, VFOV, ASPECT, SWEEP, FLOOR, KNIT_REPEAT, lightFrame, radiance, type Camera, type Scene, type V3 } from "./scene";
import type { TeeGeometry } from "./pathtracer";
import { Cloth, buildNetAsync, offsetTexture, slopeTextures, clothNodes } from "./cloth";

export const ASSET = "/tee/fit/";
export type Pose = "stand" | "up" | "sit";
/** One simulated tee: `dir` is a body + size from the fit pipeline (e.g. m170-M) or the shop tee (form-M). */
export type Variant = { dir: string; size: string; pose: Pose; body: boolean; seat?: number; skin?: V3 };
export const FABRIC: Record<"black" | "cream", V3> = { black: srgbToLinear(0x151515), cream: srgbToLinear(0xfffae7) };

function srgbToLinear(hex: number): V3 {
  const c = new THREE.Color().setHex(hex, THREE.SRGBColorSpace);
  return [c.r, c.g, c.b];
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
  lights: THREE.RectAreaLight[] = [];
  hemi = new THREE.HemisphereLight(0xf4f2ee, 0x6d6a64, 0.15);
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
  colorTex: Record<string, THREE.Texture> = {};
  ormTex: Record<string, THREE.Texture> = {};
  tris = 0;
  isWebGPU = false;

  constructor(canvas: HTMLCanvasElement) {
    // on a 2x screen the pixels already supersample the edges; multisampling on top only costs frames
    this.renderer = new THREE.WebGPURenderer({ canvas, antialias: (globalThis.devicePixelRatio || 1) < 1.5, alpha: false });
    this.renderer.toneMapping = THREE.NeutralToneMapping;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.scene.add(this.pivot, this.hemi);
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
    for (const l of this.lights) this.scene.remove(l);
    const k = cream ? s.creamK : 1;
    this.lights = s.lights.map((l) => {
      const fr = lightFrame(l), L = radiance(l, k);
      const peak = Math.max(...L);
      const rl = new THREE.RectAreaLight(new THREE.Color(L[0] / peak, L[1] / peak, L[2] / peak), peak, l.size[0], l.size[1]);
      rl.position.set(...l.pos);
      rl.lookAt(l.pos[0] + fr.n[0], l.pos[1] + fr.n[1], l.pos[2] + fr.n[2]);
      this.scene.add(rl);
      return rl;
    });
    this.paperMat.color.setRGB(...s.paper, THREE.LinearSRGBColorSpace);
    this.sweep.visible = !s.open;
    this.scene.background = new THREE.Color().setRGB(...s.world, THREE.LinearSRGBColorSpace);
    // uniform world light: irradiance pi * W, as the path tracer integrates it
    const w = Math.max(...s.world, 1e-6);
    this.hemi.color.setRGB(s.world[0] / w, s.world[1] / w, s.world[2] / w, THREE.LinearSRGBColorSpace);
    this.hemi.groundColor.copy(this.hemi.color).multiplyScalar(0.6);
    this.hemi.intensity = Math.PI * w;
  }

  private tl = new THREE.TextureLoader();
  private async tx(name: string, srgb: boolean) {
    const t = await this.tl.loadAsync(ASSET + name);
    t.flipY = false; t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    // the print stays crisp across the cloth as it turns away: full anisotropic filtering
    t.anisotropy = this.maxAniso; return t;
  }
  /** colour + roughness/ink maps for one design in one colourway, loaded once */
  private async look(design: string, t: "black" | "cream") {
    const key = `${design}-${t}`;
    if (!this.colorTex[key]) {
      const [c, o] = await Promise.all([this.tx(`tex/color-${key}.jpg`, true), this.tx(`tex/orm-${key}.png`, false)]);
      this.colorTex[key] = c; this.ormTex[key] = o;
    }
    return [this.colorTex[key], this.ormTex[key]] as const;
  }

  async setLook(design: string, t: "black" | "cream") {
    const [c, o] = await this.look(design, t);
    if (this.nodes) { this.nodes.color.value = c; this.nodes.orm.value = o; }
    this.inner.color.setRGB(...FABRIC[t], THREE.LinearSRGBColorSpace);
  }

  private nodes: { color: ReturnType<typeof texture>; orm: ReturnType<typeof texture>; normal: ReturnType<typeof texture> } | null = null;
  private normals: Record<string, THREE.Texture> = {};
  private gl: GLTFLoader | null = null;
  private loaded: THREE.Object3D[] = [];
  skinMat = new THREE.MeshPhysicalMaterial({ roughness: 0.48, metalness: 0, specularIntensity: 0.7, sheen: 0 });
  stoolMat = new THREE.MeshStandardMaterial({ roughness: 0.7, metalness: 0, color: new THREE.Color(0.05, 0.045, 0.04) });

  /**
   * Loads one simulated tee (a body + size + pose from the fit pipeline, or the shop tee on its ghost form),
   * and the body itself in fit mode; hands back the triangle soup for the path tracer.
   */
  async load(design: string, tee: "black" | "cream", v: Variant): Promise<TeeGeometry> {
    this.gl ??= new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath("/draco/"));
    const gl = this.gl;
    const normalP = (this.normals[v.size] ??= await this.tx(`tex/normal-${v.size}.png`, false));
    const [gltf, bodyGltf, [c0, o0]] = await Promise.all([
      gl.loadAsync(`${ASSET}${v.dir}/${v.pose}.glb`),
      v.body ? gl.loadAsync(`${ASSET}${v.dir}/body-${v.pose}.glb`) : Promise.resolve(null),
      this.look(design, tee),
    ]);
    if (!this.nodes) {
      const knitT = await this.tx("tex/knit-normal.png", false);
      knitT.wrapS = knitT.wrapT = THREE.RepeatWrapping;
      const colorN = texture(c0), ormN = texture(o0), normalN = texture(normalP);
      const m = new THREE.MeshPhysicalNodeMaterial({ roughness: 1, metalness: 0, specularIntensity: 0.5 });
      m.colorNode = colorN;
      m.roughnessNode = ormN.g;
      // ambient occlusion is baked into the mesh (it changes with every size and pose)
      m.aoNode = mix(float(1), vertexColor().r, 0.85);
      // cotton fuzz only off the ink: over the print it reads as a white haze
      m.sheenNode = vec3(float(0.35 * 0.06).mul(float(1).sub(ormN.b)));   // same fitted strength as the path tracer
      m.sheenRoughnessNode = float(0.3);
      // construction relief (rib, stitches) + jersey loops, whiteout blend
      const n1 = normalN.xyz.mul(2).sub(1);
      const k = texture(knitT, uv().mul(vec2(KNIT_REPEAT[0], KNIT_REPEAT[1]))).xyz.mul(2).sub(1);
      const blended = normalize(vec3(n1.xy.add(k.xy.mul(this.knit)), n1.z.mul(k.z)));
      const cloth = clothNodes(this.offsets, this.slopes);
      m.normalNode = cloth.bend(normalMap(blended.mul(0.5).add(0.5)));
      m.positionNode = cloth.position;
      this.outer = m;
      this.nodes = { color: colorN, orm: ormN, normal: normalN };
    } else {
      this.nodes.color.value = c0; this.nodes.orm.value = o0; this.nodes.normal.value = normalP;
    }
    this.inner.color.setRGB(...FABRIC[tee], THREE.LinearSRGBColorSpace);
    if (v.skin) this.skinMat.color.setRGB(...v.skin, THREE.LinearSRGBColorSpace);

    // swap out the previous tee/body
    for (const o of this.loaded) {
      this.pivot.remove(o);
      o.traverse((x) => { const mm = x as THREE.Mesh; if (mm.isMesh) mm.geometry.dispose(); });
    }
    this.loaded = [];
    const lift = v.body ? FLOOR : 0;
    this.pivot.position.y = lift;

    const P: number[] = [], N: number[] = [], UV: number[] = [], I: number[] = [], M: number[] = [];
    const teeMeshes: { mesh: THREE.Mesh; pos: Float32Array; idx: ArrayLike<number>; plain: boolean }[] = [];
    const take = (root: THREE.Object3D, kind: "tee" | "body" | "stool") => {
      root.updateMatrixWorld(true);
      root.traverse((o) => {
        const mesh = o as THREE.Mesh;
        if (!mesh.isMesh) return;
        const isInner = kind === "tee" && /inner/i.test((mesh.material as THREE.Material)?.name || "");
        mesh.material = kind === "body" ? this.skinMat : kind === "stool" ? this.stoolMat : isInner ? this.inner : this.outer!;
        const g = mesh.geometry, pa = g.attributes.position, na = g.attributes.normal, ua = g.attributes.uv;
        const base = P.length / 3, mw = mesh.matrixWorld, nm = new THREE.Matrix3().getNormalMatrix(mw);
        const vv = new THREE.Vector3();
        for (let i = 0; i < pa.count; i++) {
          vv.fromBufferAttribute(pa, i).applyMatrix4(mw); P.push(vv.x, vv.y + lift, vv.z);
          vv.fromBufferAttribute(na, i).applyMatrix3(nm).normalize(); N.push(vv.x, vv.y, vv.z);
          UV.push(ua ? ua.getX(i) : 0, ua ? ua.getY(i) : 0);
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
        const id = kind === "body" ? 2 : kind === "stool" ? 3 : isInner ? 1 : 0;
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
        cloth.wind = !matchMedia("(prefers-reduced-motion: reduce)").matches;
        this.cloth = cloth;
      }).catch((e) => console.info("cloth off", e));
    }
    if (bodyGltf) take(bodyGltf.scene, "body");
    if (v.body && v.pose === "sit" && v.seat) {
      // a plain stool, its top where the simulation's seat was (Blender y forward -> three z back)
      const box = new THREE.Mesh(new THREE.BoxGeometry(0.46, v.seat, 0.42));
      box.position.set(0, v.seat / 2, -0.04);
      const grp = new THREE.Group(); grp.add(box); take(grp, "stool");
    }
    this.tris = I.length / 3;
    return { pos: new Float32Array(P), nrm: new Float32Array(N), uv: new Float32Array(UV), idx: new Uint32Array(I), mat: new Uint8Array(M) };
  }

  setCamera(c: Camera) {
    this.camera.position.set(...c.pos);
    this.camera.lookAt(...c.target);
  }

  setView(yaw: number, crop: [number, number, number], w: number, h: number) {
    this.pivot.rotation.y = (yaw * Math.PI) / 180;
    const [cx, cy, z] = crop;
    if (z > 1.0001) {
      // magnify = crop the same frame (no camera move, so the perspective never changes)
      const cw = w / z, ch = h / z;
      const x = ((cx + 1) / 2) * w - cw / 2, y = ((1 - cy) / 2) * h - ch / 2;
      this.camera.setViewOffset(w, h, x, y, cw, ch);
    } else this.camera.clearViewOffset();
    this.camera.updateProjectionMatrix();
  }

  private m3 = new THREE.Matrix3(); private m4 = new THREE.Matrix4();
  /** advance the cloth to the pivot's current turn; true while the cloth is still moving */
  simulate(dt: number) {
    if (!this.cloth) return false;
    this.pivot.updateMatrixWorld();
    this.m4.makeRotationFromQuaternion(this.pivot.quaternion);
    this.cloth.setPose(this.m3.setFromMatrix4(this.m4), this.pivot.position, 1, dt);
    return this.cloth.step(dt);
  }

  setKnit(on: boolean) { this.knit.value = on ? 0.55 : 0; }

  resize(w: number, h: number, dpr: number) {
    this.renderer.setPixelRatio(dpr);
    this.renderer.setSize(w, h, false);
  }

  render() { this.renderer.render(this.scene, this.camera); }
}
