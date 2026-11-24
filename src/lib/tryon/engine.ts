// Live try-on: your camera, the tee on you. Everything runs in this browser tab: the pose model reads the
// video frame by frame on this device, nothing is recorded, nothing is uploaded.
//
// The pose model (MediaPipe pose landmarker, lite) gives 33 body points in the image and in metres. The shop
// tee (the same simulated garment as the viewer, the same textures) is placed in 3D so its shoulders sit on
// yours: depth from how wide your shoulders are in the frame, turn from their depth difference, lean from the
// shoulder line, size from your real shoulder width. The cloth simulation runs on top, so the hem swings when
// you move. Forearms in front of the body are drawn back over the tee from the video so your hands stay in front.
import * as THREE from "three/webgpu";
import { texture, uv, vec2, vec3, float, normalMap, normalize, vertexColor, mix } from "three/tsl";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import type { PoseLandmarker, NormalizedLandmark, Landmark } from "@mediapipe/tasks-vision";
import { Cloth, buildNetAsync, offsetTexture, clothedPosition } from "@/lib/viewer/cloth";
import { KNIT_REPEAT } from "@/lib/viewer/scene";

const ASSET = "/tee/fit/";
/** shoulder joint spacing of the body the shop tee was simulated on (171 cm, 88 cm chest), metres */
const FORM_SHOULDER = 0.355;
/** typical laptop / phone selfie camera, horizontal field of view */
const HFOV = (64 * Math.PI) / 180;

export type TryOnStatus = "model" | "camera" | "look" | "ready" | "nobody";

const L_SH = 11, R_SH = 12, L_EL = 13, R_EL = 14, L_WR = 15, R_WR = 16, L_HIP = 23, R_HIP = 24, L_IDX = 19, R_IDX = 20;

export class TryOn {
  private renderer: THREE.WebGPURenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(45, 4 / 3, 0.05, 20);
  private rig = new THREE.Group();
  private pose: PoseLandmarker | null = null;
  private cloth: Cloth | null = null;
  private offsets = offsetTexture();
  private anchor = new THREE.Vector3();
  private hemi = new THREE.HemisphereLight(0xffffff, 0x888888, 1.2);
  private key = new THREE.DirectionalLight(0xffffff, 1.6);
  private raf = 0;
  private lastVideoT = -1;
  private seen = 0;
  private sm: { p: THREE.Vector3; yaw: number; roll: number; s: number } | null = null;
  private probe = document.createElement("canvas").getContext("2d", { willReadFrequently: true })!;
  private frameN = 0;
  private colorN: { value: THREE.Texture } | null = null;
  private ormN: { value: THREE.Texture } | null = null;
  private tl = new THREE.TextureLoader();
  private dead = false;
  lms: NormalizedLandmark[] | null = null;
  world: Landmark[] | null = null;

  constructor(private video: HTMLVideoElement, private canvas: HTMLCanvasElement, private arms: HTMLCanvasElement, private onStatus: (s: TryOnStatus) => void) {
    this.renderer = new THREE.WebGPURenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.toneMapping = THREE.NeutralToneMapping;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.key.position.set(0.3, 1.2, 1.5);
    this.scene.add(this.hemi, this.key, this.rig);
    this.probe.canvas.width = this.probe.canvas.height = 8;
  }

  async start(design: string, tee: "black" | "cream") {
    this.onStatus("model");
    const [{ PoseLandmarker, FilesetResolver }] = await Promise.all([import("@mediapipe/tasks-vision"), this.renderer.init()]);
    const files = await FilesetResolver.forVisionTasks("/mediapipe");
    const opts = (delegate: "GPU" | "CPU") => ({
      baseOptions: { modelAssetPath: "/mediapipe/pose_landmarker_lite.task", delegate },
      runningMode: "VIDEO" as const, numPoses: 1, minPoseDetectionConfidence: 0.5, minTrackingConfidence: 0.5,
    });
    this.pose = await PoseLandmarker.createFromOptions(files, opts("GPU")).catch(() => PoseLandmarker.createFromOptions(files, opts("CPU")));
    if (this.dead) return;
    this.onStatus("camera");
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
    if (this.dead) { stream.getTracks().forEach((t) => t.stop()); return; }
    this.video.srcObject = stream;
    await this.video.play();
    await this.loadTee(design, tee);
    if (this.dead) return;
    await this.renderer.compileAsync(this.scene, this.camera).catch(() => {});
    this.onStatus("look");
    this.resize();
    let prev = performance.now();
    const loop = (now: number) => {
      this.raf = requestAnimationFrame(loop);
      const dt = Math.min(0.1, (now - prev) / 1000); prev = now;
      this.frame(now, dt);
    };
    this.raf = requestAnimationFrame(loop);
  }

  private tx(name: string, srgb: boolean) {
    return this.tl.loadAsync(ASSET + name).then((t) => { t.flipY = false; t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace; t.anisotropy = 8; return t; });
  }

  private async loadTee(design: string, tee: "black" | "cream") {
    const gl = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath("/draco/"));
    const [gltf, c, o, n, k] = await Promise.all([
      gl.loadAsync(`${ASSET}form-M/stand.glb`), this.tx(`tex/color-${design}-${tee}.jpg`, true), this.tx(`tex/orm-${design}-${tee}.png`, false),
      this.tx("tex/normal-M.png", false), this.tx("tex/knit-normal.png", false),
    ]);
    k.wrapS = k.wrapT = THREE.RepeatWrapping;
    const outer = new THREE.MeshPhysicalNodeMaterial({ roughness: 1, metalness: 0, specularIntensity: 0.5 });
    const colorN = texture(c), ormN = texture(o);
    this.colorN = colorN; this.ormN = ormN;
    outer.colorNode = colorN;
    outer.roughnessNode = ormN.g;
    outer.aoNode = mix(float(1), vertexColor().r, 0.85);
    outer.sheenNode = vec3(float(0.35 * 0.06).mul(float(1).sub(ormN.b)));
    outer.sheenRoughnessNode = float(0.3);
    const n1 = texture(n).xyz.mul(2).sub(1), kk = texture(k, uv().mul(vec2(KNIT_REPEAT[0], KNIT_REPEAT[1]))).xyz.mul(2).sub(1);
    outer.normalNode = normalMap(normalize(vec3(n1.xy.add(kk.xy.mul(0.55)), n1.z.mul(kk.z))).mul(0.5).add(0.5));
    outer.positionNode = clothedPosition(this.offsets);
    const inner = new THREE.MeshStandardNodeMaterial({ roughness: 0.95, metalness: 0, color: tee === "black" ? 0x151515 : 0xfffae7 });
    inner.positionNode = clothedPosition(this.offsets);

    const meshes: { mesh: THREE.Mesh; pos: Float32Array; idx: ArrayLike<number> }[] = [];
    gltf.scene.updateMatrixWorld(true);
    let yTop = -1e9;
    gltf.scene.traverse((ob) => {
      const m = ob as THREE.Mesh;
      if (!m.isMesh) return;
      m.geometry.applyMatrix4(m.matrixWorld); m.position.set(0, 0, 0); m.quaternion.identity(); m.scale.set(1, 1, 1);
      const inn = /inner/i.test((m.material as THREE.Material)?.name || "");
      m.material = inn ? inner : outer;
      m.frustumCulled = false;
      const pos = m.geometry.attributes.position.array as Float32Array;
      for (let i = 1; i < pos.length; i += 3) yTop = Math.max(yTop, pos[i]);
      meshes.push({ mesh: m, pos, idx: m.geometry.index ? m.geometry.index.array : Array.from({ length: pos.length / 3 }, (_, i) => i) });
    });
    // the geometry now carries its world placement: every node in the file sits at the origin
    gltf.scene.traverse((ob) => { ob.position.set(0, 0, 0); ob.quaternion.identity(); ob.scale.set(1, 1, 1); });
    const net = await buildNetAsync(meshes.map((m) => ({ pos: m.pos, idx: Uint32Array.from(m.idx) })));
    meshes.forEach((m, i) => { m.mesh.geometry.setAttribute("sbI", new THREE.BufferAttribute(net.skins[i].I, 4)); m.mesh.geometry.setAttribute("sbW", new THREE.BufferAttribute(net.skins[i].W, 4)); });
    this.cloth = new Cloth(net, this.offsets);
    this.cloth.wind = false;
    // the point that sits between the wearer's shoulder joints: about 5 cm under the top of the shoulder seam
    this.anchor.set(0, yTop - 0.055, 0);
    this.rig.add(gltf.scene);
    this.rig.visible = false;
  }

  /** a different design on the same tee */
  async setLook(design: string, tee: "black" | "cream") {
    if (!this.colorN || !this.ormN) return;
    const [c, o] = await Promise.all([this.tx(`tex/color-${design}-${tee}.jpg`, true), this.tx(`tex/orm-${design}-${tee}.png`, false)]);
    this.colorN.value = c; this.ormN.value = o;
  }

  resize() {
    const r = this.canvas.getBoundingClientRect(), dpr = Math.min(devicePixelRatio || 1, 2);
    this.renderer.setPixelRatio(dpr); this.renderer.setSize(r.width, r.height, false);
    this.arms.width = Math.round(r.width * dpr); this.arms.height = Math.round(r.height * dpr);
    const aspect = (this.video.videoWidth || 4) / (this.video.videoHeight || 3);
    this.camera.aspect = aspect;
    this.camera.fov = (2 * Math.atan(Math.tan(HFOV / 2) / aspect) * 180) / Math.PI;
    this.camera.updateProjectionMatrix();
  }

  private frame(now: number, dt: number) {
    const v = this.video;
    if (v.readyState >= 2 && v.currentTime !== this.lastVideoT && this.pose) {
      this.lastVideoT = v.currentTime;
      const r = this.pose.detectForVideo(v, now);
      this.lms = r.landmarks[0] ?? null; this.world = r.worldLandmarks[0] ?? null;
      this.place();
    }
    // light from the room: the mean colour and brightness of the frame, now and then
    if (this.frameN++ % 15 === 0 && v.readyState >= 2) {
      this.probe.drawImage(v, 0, 0, 8, 8);
      const d = this.probe.getImageData(0, 0, 8, 8).data; let r = 0, g = 0, b = 0;
      for (let i = 0; i < d.length; i += 4) { r += d[i]; g += d[i + 1]; b += d[i + 2]; }
      const n = d.length / 4, lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / n / 255;
      this.hemi.color.setRGB(r / n / 255 + 0.35, g / n / 255 + 0.35, b / n / 255 + 0.35).multiplyScalar(0.75);
      this.hemi.intensity = 0.7 + lum * 1.4; this.key.intensity = 0.8 + lum * 1.6;
    }
    if (this.cloth && this.rig.visible) {
      this.rig.updateMatrixWorld();
      const m3 = new THREE.Matrix3().setFromMatrix4(new THREE.Matrix4().makeRotationFromQuaternion(this.rig.quaternion));
      this.cloth.setPose(m3, this.rig.position, this.rig.scale.x);
      this.cloth.step(dt);
    }
    this.renderer.render(this.scene, this.camera);
    this.drawArms();
  }

  /** shoulders and hips -> where the tee goes, smoothed so it doesn't jitter but still keeps up */
  private place() {
    const l = this.lms, w = this.world;
    const ok = l && w && l[L_SH].visibility! > 0.5 && l[R_SH].visibility! > 0.5;
    if (!ok) {
      if (++this.seen > 8) { this.rig.visible = false; this.sm = null; this.onStatus("nobody"); }
      return;
    }
    this.seen = 0;
    const W = this.video.videoWidth, H = this.video.videoHeight;
    const ls = l![L_SH], rs = l![R_SH], wl = w![L_SH], wr = w![R_SH];
    const shoulderM = Math.hypot(wl.x - wr.x, wl.y - wr.y, wl.z - wr.z);
    const yaw = Math.atan2(wl.z - wr.z, wl.x - wr.x);
    const roll = -Math.atan2((ls.y - rs.y) * H, (ls.x - rs.x) * W);
    const px = Math.hypot((ls.x - rs.x) * W, (ls.y - rs.y) * H) / Math.max(0.35, Math.cos(yaw));
    const fx = W / 2 / Math.tan(HFOV / 2);
    const depth = (fx * shoulderM) / Math.max(px, 1);
    // shoulder midpoint, pushed back a little to the joints' depth inside the body
    const mx = ((ls.x + rs.x) / 2 - 0.5) * W, my = ((ls.y + rs.y) / 2 - 0.5) * H;
    const p = new THREE.Vector3((mx / fx) * depth, (-my / fx) * depth, -depth);
    const s = THREE.MathUtils.clamp(shoulderM / FORM_SHOULDER, 0.82, 1.3);
    const k = this.sm ? 0.45 : 1;
    if (!this.sm) this.sm = { p: p.clone(), yaw, roll, s };
    else { this.sm.p.lerp(p, k); this.sm.yaw += (yaw - this.sm.yaw) * k; this.sm.roll += (roll - this.sm.roll) * k; this.sm.s += (s - this.sm.s) * 0.2; }
    const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, this.sm.yaw, this.sm.roll, "YXZ"));
    this.rig.quaternion.copy(q);
    this.rig.scale.setScalar(this.sm.s);
    // put the tee's anchor exactly on the shoulder midpoint
    const a = this.anchor.clone().multiplyScalar(this.sm.s).applyQuaternion(q);
    this.rig.position.copy(this.sm.p).sub(a);
    if (!this.rig.visible) { this.rig.visible = true; this.onStatus("ready"); }
  }

  /** forearms and hands that are in front of the body, cut from the video and laid back over the tee */
  private drawArms() {
    const c = this.arms.getContext("2d")!, l = this.lms, w = this.world;
    c.clearRect(0, 0, this.arms.width, this.arms.height);
    if (!l || !w || !this.rig.visible) return;
    const W = this.arms.width, H = this.arms.height;
    const sw = Math.hypot((l[L_SH].x - l[R_SH].x) * W, (l[L_SH].y - l[R_SH].y) * H);
    const torsoZ = (w[L_SH].z + w[R_SH].z + w[L_HIP].z + w[R_HIP].z) / 4;
    c.save(); c.beginPath();
    let any = false;
    for (const [el, wr, ix] of [[L_EL, L_WR, L_IDX], [R_EL, R_WR, R_IDX]]) {
      if (l[wr].visibility! < 0.5 || w[wr].z > torsoZ - 0.06) continue;   // only arms clearly in front of the body
      any = true;
      const pts = [l[el], l[wr], l[ix]].map((p) => [p.x * W, p.y * H]);
      const r = sw * 0.11;
      for (let i = 0; i < 2; i++) {
        const [x0, y0] = pts[i], [x1, y1] = pts[i + 1], L = Math.hypot(x1 - x0, y1 - y0) || 1, nx = -(y1 - y0) / L * r, ny = (x1 - x0) / L * r;
        c.moveTo(x0 + nx, y0 + ny); c.lineTo(x1 + nx, y1 + ny); c.lineTo(x1 - nx, y1 - ny); c.lineTo(x0 - nx, y0 - ny); c.closePath();
        c.moveTo(x1 + r * 1.25, y1); c.arc(x1, y1, r * 1.25, 0, Math.PI * 2);
      }
    }
    if (any) { c.clip(); c.drawImage(this.video, 0, 0, W, H); }
    c.restore();
  }

  /** a still, the right way round (as other people see you), video + tee + hands */
  async snapshot(): Promise<Blob> {
    const W = this.video.videoWidth, H = this.video.videoHeight, out = document.createElement("canvas");
    out.width = W; out.height = H;
    const c = out.getContext("2d")!;
    this.renderer.render(this.scene, this.camera);
    c.drawImage(this.video, 0, 0, W, H);
    c.drawImage(this.canvas, 0, 0, W, H);
    c.drawImage(this.arms, 0, 0, W, H);
    return new Promise((res, rej) => out.toBlob((b) => (b ? res(b) : rej(new Error("no image"))), "image/jpeg", 0.92));
  }

  dispose() {
    this.dead = true;
    cancelAnimationFrame(this.raf);
    (this.video.srcObject as MediaStream | null)?.getTracks().forEach((t) => t.stop());
    this.video.srcObject = null;
    this.pose?.close();
    this.renderer.dispose();
  }
}
