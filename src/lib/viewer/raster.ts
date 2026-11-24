// Real-time view on three.js WebGPURenderer (falls back to WebGL2 by itself where WebGPU is missing).
// It is the preview you drag; the path tracer takes over the moment you let go.
import * as THREE from "three/webgpu";
import { texture, uv, vec2, vec3, float, normalMap, normalize, uniform, mix } from "three/tsl";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { RectAreaLightTexturesLib } from "three/addons/lights/RectAreaLightTexturesLib.js";
import { CAMERA, VFOV, ASPECT, SWEEP, lightFrame, radiance, type Scene, type V3 } from "./scene";
import type { TeeGeometry } from "./pathtracer";

export const ASSET = "/tee/fred/";
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
  inner = new THREE.MeshStandardMaterial({ roughness: 0.95, metalness: 0 });
  knit = uniform(0.55);
  colorTex: Record<string, THREE.Texture> = {};
  ormTex: Record<string, THREE.Texture> = {};
  tris = 0;
  isWebGPU = false;

  constructor(canvas: HTMLCanvasElement) {
    this.renderer = new THREE.WebGPURenderer({ canvas, antialias: true, alpha: false });
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
  }

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
    t.anisotropy = 8; return t;
  }
  /** colour + roughness/ink maps for one design in one colourway, loaded once */
  private async look(design: string, t: "black" | "cream") {
    const key = `${design}-${t}`;
    if (!this.colorTex[key]) {
      const [c, o] = await Promise.all([this.tx(`color-${key}.jpg`, true), this.tx(`orm-${key}.png`, false)]);
      this.colorTex[key] = c; this.ormTex[key] = o;
    }
    return [this.colorTex[key], this.ormTex[key]] as const;
  }

  async setLook(design: string, t: "black" | "cream") {
    const [c, o] = await this.look(design, t);
    if (this.outer) {
      (this.outer as unknown as { _color: { value: THREE.Texture } })._color.value = c;
      (this.outer as unknown as { _orm: { value: THREE.Texture } })._orm.value = o;
    }
    this.inner.color.setRGB(...FABRIC[t], THREE.LinearSRGBColorSpace);
  }

  /** Loads the tee once; hands back the triangle soup for the path tracer. */
  async load(design: string, tee: "black" | "cream"): Promise<TeeGeometry> {
    const tx = (n: string, s: boolean) => this.tx(n, s);
    const draco = new DRACOLoader().setDecoderPath("/draco/");
    const gl = new GLTFLoader().setDRACOLoader(draco);
    const [gltf, normal, knitT, [c0, o0]] = await Promise.all([
      gl.loadAsync(ASSET + "tee.glb"), tx("normal.png", false), tx("knit-normal.png", false), this.look(design, tee),
    ]);
    knitT.wrapS = knitT.wrapT = THREE.RepeatWrapping;

    const colorN = texture(c0), ormN = texture(o0);
    const m = new THREE.MeshPhysicalNodeMaterial({ roughness: 1, metalness: 0, specularIntensity: 0.5 });
    m.colorNode = colorN;
    m.roughnessNode = ormN.g;
    m.aoNode = mix(float(1), ormN.r, 0.85);
    // cotton fuzz only off the ink: over the print it reads as a white haze
    m.sheenNode = vec3(float(0.35 * 0.06).mul(float(1).sub(ormN.b)));   // same fitted strength as the path tracer
    m.sheenRoughnessNode = float(0.3);
    // construction relief (rib, stitches) + jersey loops, whiteout blend
    const n1 = texture(normal).xyz.mul(2).sub(1);
    const k = texture(knitT, uv().mul(vec2(175.43859649, 68.46846847))).xyz.mul(2).sub(1);
    const blended = normalize(vec3(n1.xy.add(k.xy.mul(this.knit)), n1.z.mul(k.z)));
    m.normalNode = normalMap(blended.mul(0.5).add(0.5));
    Object.assign(m, { _color: colorN, _orm: ormN });
    this.outer = m;
    this.inner.color.setRGB(...FABRIC[tee], THREE.LinearSRGBColorSpace);

    const P: number[] = [], N: number[] = [], UV: number[] = [], I: number[] = [], M: number[] = [];
    gltf.scene.updateMatrixWorld(true);
    gltf.scene.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      const isInner = /inner/i.test((mesh.material as THREE.Material)?.name || "");
      mesh.material = isInner ? this.inner : m;
      const g = mesh.geometry, pa = g.attributes.position, na = g.attributes.normal, ua = g.attributes.uv;
      const base = P.length / 3, mw = mesh.matrixWorld, nm = new THREE.Matrix3().getNormalMatrix(mw);
      const v = new THREE.Vector3();
      for (let i = 0; i < pa.count; i++) {
        v.fromBufferAttribute(pa, i).applyMatrix4(mw); P.push(v.x, v.y, v.z);
        v.fromBufferAttribute(na, i).applyMatrix3(nm).normalize(); N.push(v.x, v.y, v.z);
        UV.push(ua.getX(i), ua.getY(i));
      }
      const ix = g.index ? Array.from(g.index.array) : Array.from({ length: pa.count }, (_, i) => i);
      for (let i = 0; i < ix.length; i++) I.push(ix[i] + base);
      for (let i = 0; i < ix.length / 3; i++) M.push(isInner ? 1 : 0);
    });
    this.pivot.add(gltf.scene);
    this.tris = I.length / 3;
    return { pos: new Float32Array(P), nrm: new Float32Array(N), uv: new Float32Array(UV), idx: new Uint32Array(I), mat: new Uint8Array(M) };
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

  setKnit(on: boolean) { this.knit.value = on ? 0.55 : 0; }

  resize(w: number, h: number, dpr: number) {
    this.renderer.setPixelRatio(dpr);
    this.renderer.setSize(w, h, false);
  }

  render() { this.renderer.render(this.scene, this.camera); }
}
