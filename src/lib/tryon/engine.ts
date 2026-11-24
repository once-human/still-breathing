// Live try-on: your camera, the real tee on you, at its real size, moving the way a game character's clothes do.
// Everything runs in this tab: the pose model reads each video frame on this device; nothing is recorded or sent.
//
// 1. Pose. MediaPipe's pose landmarker gives 33 body points per frame: where they are in the picture, and where
//    they are in metres around the hips.
// 2. Camera solve. A small least-squares solve per frame recovers the camera's focal length (slowly) and where the
//    body stands in front of it, in metres. The result is pinned to the picture: the shoulders' midpoint lands
//    exactly where the model sees your shoulders in the frame.
// 3. The tee is a rigged character garment. pipeline/tryon_rig.py takes the tee exactly as it hung on a real
//    (Indian, 170 cm) body in the cloth simulation, and carries that body's skin weights onto it, smoothed the way
//    garment weights are. Its skeleton (hips, spine, neck, head, clavicles, shoulders, upper and lower arms) is
//    driven from your pose like a game character's: the torso from your shoulders and hips, each arm bone turned
//    toward your elbow and wrist. Raise an arm and the whole sleeve goes up with it, the side of the tee following.
// 4. In front and behind. The body it was draped on comes with it as an invisible occluder on the same skeleton:
//    your neck, head and shoulders hide the inside of the collar and the back, as on a person. Hands and forearms
//    in front of you are cut from the video and laid back on top.
// 5. Light. The room is read from the video (how bright, what colour, which side the light comes from) and lights
//    the tee through an image-based environment; your head and neck throw a soft shadow on the collar.
// 6. Steadiness. The picture is the very camera frame the pose was read from, drawn in the same instant as the tee.
//    Body shape and distance are smoothed apart (One Euro), the torso's turn has its own filter.
//
// The preview is a mirror (the video is flipped). The tee is placed in that mirrored space without being flipped
// itself, so its print reads the right way round.
import * as THREE from "three/webgpu";
import { texture, uv, vec2, vec3, float, normalMap, normalize, vertexColor, mix, positionGeometry, normalGeometry } from "three/tsl";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import type { PoseLandmarker, NormalizedLandmark, Landmark } from "@mediapipe/tasks-vision";
import { KNIT_REPEAT } from "@/lib/viewer/scene";
import { SIZES, type Size } from "@/content/tee";

const ASSET = "/tee/fit/";
const RIG = "/tee/tryon/m170-M.glb";
export type TryOnStatus = "model" | "camera" | "look" | "ready" | "nobody";

const NOSE = 0, L_EAR = 7, R_EAR = 8, L_SH = 11, R_SH = 12, L_EL = 13, R_EL = 14, L_WR = 15, R_WR = 16, L_IDX = 19, R_IDX = 20, L_HIP = 23, R_HIP = 24, L_KNEE = 25, R_KNEE = 26;
const SOLVE = [L_SH, R_SH, L_EL, R_EL, L_HIP, R_HIP, L_EAR, R_EAR, NOSE];
const TRACK = [L_SH, R_SH, L_EL, R_EL, L_WR, R_WR, L_HIP, R_HIP, L_EAR, R_EAR, NOSE, L_IDX, R_IDX, L_KNEE, R_KNEE];

/** One Euro filter: heavy smoothing when still, almost none when moving fast (Casiez et al. 2012) */
class OneEuro {
  private x = NaN; private dx = 0; private t = 0;
  constructor(private minCut = 0.9, private beta = 3, private dCut = 1.2) {}
  private static a(cut: number, dt: number) { const r = 2 * Math.PI * cut * dt; return r / (r + 1); }
  f(v: number, t: number) {
    if (Number.isNaN(this.x)) { this.x = v; this.t = t; return v; }
    const dt = Math.max(1e-3, t - this.t); this.t = t;
    this.dx += OneEuro.a(this.dCut, dt) * ((v - this.x) / dt - this.dx);
    this.x += OneEuro.a(this.minCut + this.beta * Math.abs(this.dx), dt) * (v - this.x);
    return this.x;
  }
  reset() { this.x = NaN; this.dx = 0; }
}
class Euro3 {
  private c: OneEuro[];
  constructor(cut = 0.9, beta = 3, cutZ = cut, betaZ = beta) { this.c = [new OneEuro(cut, beta), new OneEuro(cut, beta), new OneEuro(cutZ, betaZ)]; }
  f(v: THREE.Vector3, t: number) { return v.set(this.c[0].f(v.x, t), this.c[1].f(v.y, t), this.c[2].f(v.z, t)); }
  reset() { this.c.forEach((c) => c.reset()); }
}

/** small dense least squares: solves (A^T A) x = A^T b by Gaussian elimination */
function lsq(rows: number[][], rhs: number[], n: number) {
  const M = Array.from({ length: n }, () => new Array(n + 1).fill(0));
  rows.forEach((r, k) => { for (let i = 0; i < n; i++) { for (let j = 0; j < n; j++) M[i][j] += r[i] * r[j]; M[i][n] += r[i] * rhs[k]; } });
  for (let i = 0; i < n; i++) {
    let p = i; for (let k = i + 1; k < n; k++) if (Math.abs(M[k][i]) > Math.abs(M[p][i])) p = k;
    [M[i], M[p]] = [M[p], M[i]];
    if (Math.abs(M[i][i]) < 1e-12) return null;
    for (let k = 0; k < n; k++) if (k !== i) { const f = M[k][i] / M[i][i]; for (let j = i; j <= n; j++) M[k][j] -= f * M[i][j]; }
  }
  return M.map((r, i) => r[n] / r[i]);
}


export class TryOn {
  private renderer: THREE.WebGPURenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(50, 16 / 9, 0.05, 20);
  private rig = new THREE.Group();
  private pose: PoseLandmarker | null = null;
  private key = new THREE.DirectionalLight(0xffffff, 1);
  private fill = new THREE.HemisphereLight(0xffffff, 0x444444, 0.3);
  private occMat = new THREE.MeshBasicNodeMaterial({ colorWrite: false });
  private probe = document.createElement("canvas").getContext("2d", { willReadFrequently: true })!;
  private colorN: { value: THREE.Texture } | null = null;
  private ormN: { value: THREE.Texture } | null = null;
  private tl = new THREE.TextureLoader();
  private dead = false;
  private vfc = 0; private raf = 0;
  private lost = 0; private placed = false;
  private f = 0;                                  // focal length in video pixels, learned
  private prevT = 0; private frameN = 0;
  // the skeleton, by bone name, with each bone's rest orientation and head position in the model's own space
  private B = new Map<string, THREE.Bone>();
  private restQ = new Map<string, THREE.Quaternion>(); private restP = new Map<string, THREE.Vector3>();
  private restTorso = new THREE.Quaternion(); private modelShoulder = 0.34;
  private torsoQ = new THREE.Quaternion(); private hipQ = new THREE.Quaternion();
  private teeGeo: THREE.BufferGeometry | null = null; private basePos: Float32Array | null = null;
  private dims = { yTop: 0, zc: 0 };
  private mid = new THREE.Vector3();
  private hem: { name: string; b: THREE.Bone; dir: THREE.Vector3; out: THREE.Vector3 | null; len: number; K: number; cone: number; p: THREE.Vector3; v: THREE.Vector3; live: boolean }[] = [];
  private filt = new Map<number, Euro3>();
  private tFilt = new Euro3(1.0, 2, 0.35, 0.8);   // where the body stands; distance smoothed hardest
  private armOn = [false, false];
  private fctx: CanvasRenderingContext2D;
  private mask = document.createElement("canvas");
  private tier = 0; private busy = 0; private over = 0; private swapping = false; private camInt = 1 / 30;
  private makePose: ((model: "full" | "lite") => Promise<PoseLandmarker>) | null = null;
  private midU = new OneEuro(1.0, 0.015, 1.2); private midV = new OneEuro(1.0, 0.015, 1.2); private body = 0;
  private keyOff = new THREE.Vector3(0, 2, 2); private shown = false; private qSpeed = 0;
  private lit = false; private lum = 0.5; private tint = new THREE.Color(1, 1, 1); private side = new THREE.Vector2();
  private P = new Map<number, THREE.Vector3>();   // filtered camera-space points (mirrored), metres
  private img: { x: number; y: number }[] = [];
  private lms: NormalizedLandmark[] | null = null;

  constructor(private video: HTMLVideoElement, private frameCv: HTMLCanvasElement, private canvas: HTMLCanvasElement, private arms: HTMLCanvasElement, private onStatus: (s: TryOnStatus) => void) {
    this.renderer = new THREE.WebGPURenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.toneMapping = THREE.NeutralToneMapping;
    // your head and neck throw a soft shadow on the collar and chest: the strongest cue that the tee is on a body
    this.renderer.shadowMap.enabled = true; this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.key.castShadow = true; this.key.shadow.mapSize.set(1024, 1024);
    Object.assign(this.key.shadow.camera, { left: -0.9, right: 0.9, top: 0.9, bottom: -0.9, near: 0.2, far: 8 });
    this.key.shadow.bias = -0.0006; this.key.shadow.normalBias = 0.02; this.key.shadow.radius = 5;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.scene.add(this.key, this.key.target, this.fill, this.rig);
    this.probe.canvas.width = 16; this.probe.canvas.height = 9;
    this.fctx = frameCv.getContext("2d", { alpha: false, desynchronized: true })!;
  }

  async start(design: string, tee: "black" | "cream", size: Size) {
    this.onStatus("model");
    const [{ PoseLandmarker, FilesetResolver }] = await Promise.all([import("@mediapipe/tasks-vision"), this.renderer.init()]);
    const files = await FilesetResolver.forVisionTasks("/mediapipe");
    const opts = (delegate: "GPU" | "CPU", model: string) => ({
      baseOptions: { modelAssetPath: `/mediapipe/pose_landmarker_${model}.task`, delegate },
      runningMode: "VIDEO" as const, numPoses: 1, minPoseDetectionConfidence: 0.5, minPosePresenceConfidence: 0.5, minTrackingConfidence: 0.6,
    });
    // every device starts at full quality and is eased down only if it really can't keep up (see govern)
    this.tier = 0;
    this.makePose = (model) => PoseLandmarker.createFromOptions(files, opts("GPU", model)).catch(() => PoseLandmarker.createFromOptions(files, opts("CPU", "lite")));
    this.pose = await this.makePose(this.tier ? "lite" : "full");
    if (this.dead) return;
    // a soft room-like environment; its strength and colour follow the video
    this.scene.environment = new THREE.PMREMGenerator(this.renderer).fromScene(new RoomEnvironment(), 0.04).texture;
    this.onStatus("camera");
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 960 }, height: { ideal: 540 }, frameRate: { ideal: 30, max: 30 } }, audio: false });
    if (this.dead) { stream.getTracks().forEach((t) => t.stop()); return; }
    this.video.srcObject = stream;
    this.camInt = 1 / (stream.getVideoTracks()[0]?.getSettings().frameRate || 30);
    await this.video.play();
    await this.loadTee(design, tee);
    if (this.dead) return;
    this.setSize(size);
    await this.renderer.compileAsync(this.scene, this.camera).catch(() => {});
    this.onStatus("look");
    this.resize();
    // one pass per camera frame, so the tee and the picture always change together
    const v = this.video as HTMLVideoElement & { requestVideoFrameCallback?: (cb: (now: number) => void) => number };
    if (v.requestVideoFrameCallback) {
      const tick = (now: number) => { if (this.dead) return; this.vfc = v.requestVideoFrameCallback!(tick); this.frame(now); };
      this.vfc = v.requestVideoFrameCallback(tick);
    } else {
      let last = -1;
      const tick = (now: number) => { if (this.dead) return; this.raf = requestAnimationFrame(tick); if (v.currentTime !== last) { last = v.currentTime; this.frame(now); } };
      this.raf = requestAnimationFrame(tick);
    }
  }

  private tx(name: string, srgb: boolean) {
    return this.tl.loadAsync(ASSET + name).then((t) => { t.flipY = false; t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace; t.anisotropy = 8; return t; });
  }

  private async loadTee(design: string, tee: "black" | "cream") {
    const gl = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath("/draco/"));
    const [gltf, c, o, n, k] = await Promise.all([
      gl.loadAsync(RIG), this.tx(`tex/color-${design}-${tee}.jpg`, true), this.tx(`tex/orm-${design}-${tee}.png`, false),
      this.tx("tex/normal-M.png", false), this.tx("tex/knit-normal.png", false),
    ]);
    k.wrapS = k.wrapT = THREE.RepeatWrapping;
    const colorN = texture(c), ormN = texture(o);
    this.colorN = colorN; this.ormN = ormN;
    const outer = new THREE.MeshPhysicalNodeMaterial({ roughness: 1, metalness: 0, specularIntensity: 0.5 });
    outer.colorNode = colorN;
    outer.roughnessNode = ormN.g;
    outer.aoNode = mix(float(1), vertexColor().r, 0.85);
    outer.sheenNode = vec3(float(0.35 * 0.06).mul(float(1).sub(ormN.b)));
    outer.sheenRoughnessNode = float(0.3);
    const n1 = texture(n).xyz.mul(2).sub(1), kk = texture(k, uv().mul(vec2(KNIT_REPEAT[0], KNIT_REPEAT[1]))).xyz.mul(2).sub(1);
    outer.normalNode = normalMap(normalize(vec3(n1.xy.add(kk.xy.mul(0.55)), n1.z.mul(kk.z))).mul(0.5).add(0.5));

    let teeMesh: THREE.SkinnedMesh | null = null, occ: THREE.SkinnedMesh | null = null;
    gltf.scene.traverse((ob) => {
      const b = ob as THREE.Bone;
      if (b.isBone) this.B.set(b.name, b);
      const m = ob as THREE.SkinnedMesh;
      if (m.isSkinnedMesh) { if (/occluder/.test(m.name)) occ = m; else teeMesh = m; }
    });
    if (!teeMesh) throw new Error("try-on rig has no tee");
    const tm = teeMesh as THREE.SkinnedMesh;
    tm.material = outer; tm.frustumCulled = false; tm.receiveShadow = true; tm.castShadow = true;
    if (occ) {
      // the body the tee was draped on: depth only, drawn first, and it throws the head and neck's shadow
      const om = occ as THREE.SkinnedMesh;
      om.material = this.occMat; om.renderOrder = -1; om.frustumCulled = false; om.castShadow = true;
      // and a second skin of it, drawn after the tee, that shows only the shadows falling on you: the hem's on
      // your trousers, the collar's on your neck, the sleeves' on your arms. The tee sits on you, not over you
      const catcher = new THREE.SkinnedMesh(om.geometry, new THREE.ShadowNodeMaterial({ opacity: 0.4, depthWrite: false }));
      catcher.bind(om.skeleton, om.bindMatrix); catcher.receiveShadow = true; catcher.frustumCulled = false; catcher.renderOrder = 2;
      om.parent!.add(catcher); catcher.position.copy(om.position); catcher.quaternion.copy(om.quaternion); catcher.scale.copy(om.scale);
    }
    this.rig.add(gltf.scene);
    this.rig.updateMatrixWorld(true);
    // the rest pose, in the model's own space (the rig is still at identity here)
    for (const [name, b] of this.B) {
      this.restQ.set(name, b.getWorldQuaternion(new THREE.Quaternion()));
      this.restP.set(name, b.getWorldPosition(new THREE.Vector3()));
    }
    const sL = this.bp("upperarm01.L"), sR = this.bp("upperarm01.R"), root = this.bp("root");
    const axisZ = this.bp("spine01").z;
    for (let k = 0; this.bone(`hem${k}`); k++) {
      const name = `hem${k}`, b = this.bone(name)!, head = this.bp(name), tail = this.bp(`hem${k}end`), d = tail.clone().sub(head);
      this.hem.push({ name, b, dir: d.clone().normalize(), len: d.length(), out: new THREE.Vector3(head.x, 0, head.z - axisZ).normalize(), K: 55, cone: 1.2, p: new THREE.Vector3(), v: new THREE.Vector3(), live: false });
    }
    // the sleeves' own springs: stiffer, and held within a small cone round the arm so they never pass through it
    for (const S of ["L", "R"]) {
      const name = `sleeve.${S}`, b = this.bone(name); if (!b) continue;
      const d = this.bp(`sleeve.${S}end`).sub(this.bp(name));
      this.hem.push({ name: b.name, b, dir: d.clone().normalize(), len: d.length(), out: null, K: 80, cone: 0.28, p: new THREE.Vector3(), v: new THREE.Vector3(), live: false });
    }
    this.modelShoulder = sL.distanceTo(sR);
    const xR = sL.clone().sub(sR).normalize(), yR = sL.clone().add(sR).multiplyScalar(0.5).sub(root).normalize();
    const zR = new THREE.Vector3().crossVectors(xR, yR).normalize(); yR.crossVectors(zR, xR);
    this.restTorso.setFromRotationMatrix(new THREE.Matrix4().makeBasis(xR, yR, zR));

    // the tee as simulated (size M), kept so the other sizes can be made from it
    this.teeGeo = tm.geometry;
    const pa = tm.geometry.attributes.position.array as Float32Array;
    this.basePos = pa.slice();
    let yTop = -1e9; for (let i = 1; i < pa.length; i += 3) yTop = Math.max(yTop, pa[i]);
    let zs = 0, zn = 0;
    for (let i = 0; i < pa.length; i += 3) { const y = pa[i + 1]; if (y < yTop - 0.08 && y > yTop - 0.16 && Math.abs(pa[i]) < 0.1) { zs += pa[i + 2]; zn++; } }
    this.dims = { yTop, zc: zn ? zs / zn : 0 };
    // round the collar, any surface that faces in toward the body (the inside of the neckband) is never seen on a
    // person: your neck fills it. It's cut, so only the outside shows
    {
      const P = positionGeometry, N = normalGeometry;
      const collar = P.y.greaterThan(yTop - 0.13).and(P.x.abs().lessThan(0.17));
      const inward = N.x.mul(P.x).add(N.z.mul(P.z.sub(this.dims.zc))).lessThan(0);
      outer.maskNode = collar.and(inward).not();
    }
    this.rig.visible = false;
  }

  /** turn a bone so that, in the model's space, it sits at its rest orientation turned by delta */
  private setBone(name: string, delta: THREE.Quaternion, ease = 1) {
    const b = this.bone(name); if (!b) return;
    const pq = b.parent ? b.parent.getWorldQuaternion(new THREE.Quaternion()) : new THREE.Quaternion();
    const local = pq.invert().multiply(delta.clone().multiply(this.restQ.get(b.name)!));
    if (ease >= 1) b.quaternion.copy(local); else b.quaternion.slerp(local, ease);
    b.updateMatrixWorld(true);
  }
  /** how far a bone's parent has turned from rest: what the bone carries before it turns itself */
  private carried(name: string) {
    const p = this.bone(name)?.parent as THREE.Bone | undefined;
    if (!p || !this.restQ.has(p.name)) return new THREE.Quaternion();
    return p.getWorldQuaternion(new THREE.Quaternion()).multiply(this.restQ.get(p.name)!.clone().invert());
  }

  /**
   * The hem and sleeves hang like cloth. Eight spring bones run from the waist to the hem and one down each sleeve
   * to the cuff; each is a damped pendulum whose
   * tip is pulled toward where the body would carry it, while gravity and its own momentum act on it. Lean forward
   * and the front falls away from you; turn and the hem swings, then settles. It never goes further into the body
   * than it hangs at rest. Stiffness and damping are set for 240 GSM jersey: about one slow swing, no bounce.
   */
  private hang(dt: number) {
    const C = 7, G = new THREE.Vector3(0, -9.81, 0), s = this.rig.scale.x;
    for (const h of this.hem) {
      const head = h.b.getWorldPosition(new THREE.Vector3()), D = this.carried(h.name);
      const rest = h.dir.clone().applyQuaternion(D), out = h.out ? h.out.clone().applyQuaternion(D) : null, L = h.len * s, K = h.K;
      const T = head.clone().addScaledVector(rest, L);
      // the drape already hangs under gravity as you stand: only the change in gravity relative to the body pulls
      const g = G.clone().sub(G.clone().applyQuaternion(D));
      if (!h.live || h.p.distanceTo(T) > 0.5) { h.p.copy(T); h.v.set(0, 0, 0); h.live = true; }
      const n = 2, st = Math.min(dt, 0.05) / n;
      for (let i = 0; i < n; i++) {
        const a = T.clone().sub(h.p).multiplyScalar(K).add(g).addScaledVector(h.v, -C);
        h.v.addScaledVector(a, st); h.p.addScaledVector(h.v, st);
        const d = h.p.clone().sub(head).normalize();
        if (out) {
          const inside = d.dot(out) - rest.dot(out);
          if (inside < -0.03) { d.addScaledVector(out, -0.03 - inside).normalize(); h.v.addScaledVector(out, -Math.min(0, h.v.dot(out))); }
        }
        const a0 = d.angleTo(rest);
        if (a0 > h.cone) { d.copy(rest.clone().lerp(d, h.cone / a0).normalize()); h.v.multiplyScalar(0.5); }
        h.p.copy(head).addScaledVector(d, L);
      }
      const dir = h.p.clone().sub(head).normalize();
      this.setBone(h.name, new THREE.Quaternion().setFromUnitVectors(rest, dir).multiply(D));
    }
  }

  /** a bone's rest head position in the model's space (names as in Blender; the loader drops the dots) */
  private bone(name: string) { return this.B.get(THREE.PropertyBinding.sanitizeNodeName(name)) ?? this.B.get(name); }
  private bp(name: string) { const b = this.bone(name); return b ? this.restP.get(b.name)!.clone() : new THREE.Vector3(); }

  /** a different design on the same tee */
  async setLook(design: string, tee: "black" | "cream") {
    if (!this.colorN || !this.ormN) return;
    const [c, o] = await Promise.all([this.tx(`tex/color-${design}-${tee}.jpg`, true), this.tx(`tex/orm-${design}-${tee}.png`, false)]);
    this.colorN.value = c; this.ormN.value = o;
  }

  /** the real garment for that size: wider and longer by the size chart, made from the simulated M on the same body */
  setSize(sz: Size) {
    const g = this.teeGeo, src = this.basePos; if (!g || !src) return;
    const w = SIZES[sz].chest_round / SIZES.M.chest_round, l = SIZES[sz].length / SIZES.M.length, { yTop, zc } = this.dims;
    const dst = g.attributes.position.array as Float32Array;
    for (let i = 0; i < src.length; i += 3) {
      dst[i] = src[i] * w; dst[i + 1] = yTop - (yTop - src[i + 1]) * l; dst[i + 2] = zc + (src[i + 2] - zc) * w;
    }
    g.attributes.position.needsUpdate = true;
  }

  /**
   * Realism first, then picture quality, then frame rate. The time each camera frame takes here (read the pose,
   * place the tee, draw) is measured; only if it keeps running well past the camera's frame time (under about
   * 20 fps) does the try-on ease down, and never far: 1 the lighter pose model, 2 a smaller shadow map and a
   * render at the screen's own resolution. The cloth and the shadow always stay. It never steps back up
   * mid-session, so nothing flickers between levels.
   */
  private govern(busy: number, interval: number) {
    this.busy = this.busy ? this.busy + (busy - this.busy) * 0.1 : busy;
    const budget = Math.max(14, Math.min(40, interval * 1000)) * 1.5;
    this.over = this.busy > budget ? this.over + 1 : 0;
    if (this.over < 45 || this.tier >= 2 || this.swapping) return;
    this.over = 0; this.busy = 0; this.tier++;
    if (this.tier === 1 && this.makePose) {
      this.swapping = true;
      this.makePose("lite").then((p) => { if (this.dead) { p.close(); return; } const old = this.pose; this.pose = p; old?.close(); }).catch(() => {}).finally(() => { this.swapping = false; });
    }
    if (this.tier === 2) { this.key.shadow.mapSize.set(512, 512); this.key.shadow.map?.dispose(); this.key.shadow.map = null; this.resize(); }
  }

  resize() {
    const r = this.canvas.getBoundingClientRect(), dpr = Math.min(devicePixelRatio || 1, this.tier >= 2 ? 1.25 : 1.5);
    this.renderer.setPixelRatio(dpr); this.renderer.setSize(r.width, r.height, false);
    this.arms.width = Math.round(r.width * dpr); this.arms.height = Math.round(r.height * dpr);
  }

  private frame(now: number) {
    const v = this.video, t = now / 1000;
    const dt = this.prevT ? Math.min(0.1, t - this.prevT) : 1 / 30; this.prevT = t;
    if (v.readyState < 2 || !this.pose || !v.videoWidth) return;
    const t0 = performance.now();
    // freeze this camera frame: the pose is read from it and it's what is shown, together with the tee
    const fc = this.frameCv;
    if (fc.width !== v.videoWidth || fc.height !== v.videoHeight) { fc.width = v.videoWidth; fc.height = v.videoHeight; }
    this.fctx.drawImage(v, 0, 0);
    const r = this.pose.detectForVideo(fc, now);
    this.place(r.landmarks[0] ?? null, r.worldLandmarks[0] ?? null, t, dt);
    if (this.frameN++ % 10 === 0) this.light(dt * 10);
    this.renderer.render(this.scene, this.camera);
    this.drawArms();
    if (!this.shown) { this.shown = true; v.style.opacity = "0"; }
    this.govern(performance.now() - t0, this.camInt);
  }

  /** the room: brightness, colour, and which side the light comes from */
  private light(dt: number) {
    const c = this.probe, W = 16, H = 9;
    c.drawImage(this.frameCv, 0, 0, W, H);
    const d = c.getImageData(0, 0, W, H).data;
    let r = 0, g = 0, b = 0, left = 0, right = 0, top = 0, bot = 0;
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const i = 4 * (y * W + x), l = 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
      r += d[i]; g += d[i + 1]; b += d[i + 2];
      if (x < W / 2) right += l; else left += l;     // the video is unmirrored: its left is the preview's right
      if (y < H / 2) top += l; else bot += l;
    }
    const n = W * H, lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / n / 255, m = Math.max(r, g, b) || 1;
    let sx = (right - left) / (right + left + 1e-3);
    const sy = (top - bot) / (top + bot + 1e-3);
    // better still, your face: it's lit by the same lamp as you, so the brighter cheek says where the light is
    const l = this.lms, fc = this.frameCv;
    if (l && Math.min(l[L_EAR].visibility ?? 0, l[R_EAR].visibility ?? 0, l[NOSE].visibility ?? 0) > 0.6) {
      const cheek = (ear: number) => {
        const x = ((l[NOSE].x + l[ear].x) / 2) * fc.width, y = ((l[NOSE].y + l[ear].y) / 2 + 0.01) * fc.height;
        const r2 = Math.max(3, Math.abs(l[L_EAR].x - l[R_EAR].x) * fc.width * 0.12);
        c.drawImage(fc, x - r2, y - r2, 2 * r2, 2 * r2, 0, 0, 4, 4);
        const q = c.getImageData(0, 0, 4, 4).data; let s2 = 0;
        for (let i = 0; i < q.length; i += 4) s2 += 0.2126 * q[i] + 0.7152 * q[i + 1] + 0.0722 * q[i + 2];
        return s2;
      };
      // the right ear's cheek is on the preview's right (+x); the left's on its left
      const cr = cheek(R_EAR), cl = cheek(L_EAR);
      sx = Math.max(-1, Math.min(1, 1.6 * (cr - cl) / (cr + cl + 1e-3)));
    }
    // the room is read every few frames; the tee eases toward it so a camera's auto-exposure never makes it flicker
    const k = this.lit ? 1 - Math.exp(-dt * 3) : 1; this.lit = true;
    this.tint.lerp(new THREE.Color(0.35 + 0.65 * r / m, 0.35 + 0.65 * g / m, 0.35 + 0.65 * b / m), k);
    this.lum += (lum - this.lum) * k; this.side.x += (sx - this.side.x) * k; this.side.y += (sy - this.side.y) * k;
    this.scene.environmentIntensity = 0.3 + this.lum * 1.3;
    this.key.color.copy(this.tint); this.key.intensity = 0.5 + this.lum * 2.4;
    this.fill.color.copy(this.tint); this.fill.intensity = 0.15 + this.lum * 0.4;
    this.keyOff.set(this.side.x * 3, 1.5 + this.side.y * 2, 1.5);
    if (this.placed) this.key.target.position.copy(this.mid);
  }

  /** the camera solve, the body's frame, and the tee on it */
  private place(l: NormalizedLandmark[] | null, w: Landmark[] | null, t: number, dt: number) {
    const ok = l && w && (l[L_SH].visibility ?? 0) > 0.55 && (l[R_SH].visibility ?? 0) > 0.55;
    if (!ok) {
      if (++this.lost > 6) { this.rig.visible = false; this.placed = false; this.hem.forEach((h) => (h.live = false)); this.lms = null; this.filt.forEach((f) => f.reset()); this.tFilt.reset(); this.midU.reset(); this.midV.reset(); this.body = 0; this.onStatus("nobody"); }
      return;
    }
    this.lost = 0;
    const V = this.video, W = V.videoWidth, H = V.videoHeight;
    if (!this.f) this.f = W / 2 / Math.tan((70 * Math.PI) / 360);   // a typical webcam until it learns better
    // mirrored, centred, y up: image (u, v) in px, body (X, Y, Z) in metres with Z away from the camera
    const use = SOLVE.filter((i) => (l![i].visibility ?? 0) > 0.6);
    const U = (i: number) => (1 - l![i].x) * W - W / 2, Vv = (i: number) => (0.5 - l![i].y) * H;
    const X = (i: number) => -w![i].x, Y = (i: number) => -w![i].y, Z = (i: number) => w![i].z;
    // the focal length as well: unknowns (f, f*Tx, f*Ty, Tz), held near what it has learned so far
    if (use.length >= 5) {
      const rows: number[][] = [], rhs: number[] = [];
      for (const i of use) {
        rows.push([X(i), 1, 0, -U(i)]); rhs.push(U(i) * Z(i));
        rows.push([Y(i), 0, 1, -Vv(i)]); rhs.push(Vv(i) * Z(i));
      }
      rows.push([0.3, 0, 0, 0]); rhs.push(0.3 * this.f);
      const s = lsq(rows, rhs, 4);
      if (s && s[0] > 0.45 * W && s[0] < 2.2 * W) this.f += (s[0] - this.f) * 0.03;
    }
    // then where the body stands, with the focal length held
    const rows: number[][] = [], rhs: number[] = [];
    for (const i of use.length >= 2 ? use : [L_SH, R_SH]) {
      rows.push([this.f, 0, -U(i)]); rhs.push(U(i) * Z(i) - this.f * X(i));
      rows.push([0, this.f, -Vv(i)]); rhs.push(Vv(i) * Z(i) - this.f * Y(i));
    }
    const T0 = lsq(rows, rhs, 3);
    if (!T0 || T0[2] < 0.25) return;
    const Tv = this.tFilt.f(new THREE.Vector3(T0[0], T0[1], T0[2]), t), T = [Tv.x, Tv.y, Tv.z];
    this.camera.fov = (2 * Math.atan(H / 2 / this.f) * 180) / Math.PI;
    this.camera.aspect = W / H; this.camera.updateProjectionMatrix();
    for (const i of TRACK) {
      // the body's own shape (metres around the hips) and where it stands are smoothed apart
      let f = this.filt.get(i); if (!f) this.filt.set(i, (f = new Euro3(0.9, 2.5, 0.45, 1.2)));
      const b = f.f(new THREE.Vector3(X(i), Y(i), Z(i)), t);
      this.P.set(i, new THREE.Vector3(b.x + T[0], b.y + T[1], -(b.z + T[2])));
    }
    // pinned to the picture: the 3D points can drift a little against the video (their depth is a guess from one
    // camera), but where your shoulders are in the frame is the model's surest answer. Everything is slid so the
    // shoulders' midpoint lands exactly on that spot, at the depth the solve found
    {
      const mu = this.midU.f((U(L_SH) + U(R_SH)) / 2, t), mv = this.midV.f((Vv(L_SH) + Vv(R_SH)) / 2, t);
      const m0 = this.P.get(L_SH)!.clone().add(this.P.get(R_SH)!).multiplyScalar(0.5), Zc = -m0.z;
      const shift = new THREE.Vector3((mu * Zc) / this.f, (mv * Zc) / this.f, -Zc).sub(m0);
      this.P.forEach((p) => p.add(shift));
      // and fitted to you: the draped body's shoulder joints against yours as the model measures them. Learned over
      // a second or two, so the tee never breathes in size, and the size you pick is on top of that
      const k = Math.min(1.3, Math.max(0.8, this.P.get(L_SH)!.distanceTo(this.P.get(R_SH)!) / this.modelShoulder));
      this.body = this.body ? this.body + (k - this.body) * (1 - Math.exp(-dt / 1.5)) : k;
    }
    this.lms = l;
    this.img = l!.map((p) => ({ x: p.x, y: p.y }));

    // the torso's frame: the model's left (+x) is the shoulder on the preview's right (landmark 12, mirrored)
    const sL = this.P.get(L_SH)!, sR = this.P.get(R_SH)!, mid = this.mid.copy(sL).add(sR).multiplyScalar(0.5);
    const xA = sR.clone().sub(sL).normalize();
    const hips = (l![L_HIP].visibility ?? 0) > 0.6 && (l![R_HIP].visibility ?? 0) > 0.6;
    const hipMid = hips ? this.P.get(L_HIP)!.clone().add(this.P.get(R_HIP)!).multiplyScalar(0.5) : null;
    const up = hipMid ? mid.clone().sub(hipMid).normalize() : new THREE.Vector3(0, 1, 0);
    const frame = (x: THREE.Vector3, y: THREE.Vector3) => {
      const z = new THREE.Vector3().crossVectors(x, y).normalize(), yy = new THREE.Vector3().crossVectors(z, x).normalize();
      return new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(x.clone().normalize(), yy, z));
    };
    // the torso's turn is the noisiest thing the pose model gives (depth from one camera), so it gets its own
    // filter: it holds still when you hold still and follows with almost no lag when you turn
    const qNew = frame(xA, up);
    if (!this.placed) { this.torsoQ.copy(qNew); this.hipQ.copy(qNew); this.qSpeed = 0; }
    else {
      const speed = this.torsoQ.angleTo(qNew) / Math.max(dt, 1e-3);
      this.qSpeed += (speed - this.qSpeed) * (1 - Math.exp(-dt * 8));
      const cut = 1.2 + 2.2 * this.qSpeed, rr = 2 * Math.PI * cut * dt;
      this.torsoQ.slerp(qNew, rr / (rr + 1));
    }
    // the pelvis is its own frame: its line is your hips', and it stands on your legs (hip to knee, or plain upright
    // when the knees are out of the picture). Bend forward and the chest goes with your shoulders while the pelvis
    // mostly stays: the spine curves between them and the hem stays round your hips instead of swinging out
    if (hips) {
      const kn = [L_KNEE, R_KNEE].filter((i) => (l![i].visibility ?? 0) > 0.5).map((i) => this.P.get(i)!);
      const leg = kn.length ? hipMid!.clone().sub(kn.reduce((a, b) => a.clone().add(b)).multiplyScalar(1 / kn.length)).normalize() : new THREE.Vector3(0, 1, 0);
      const pelvisUp = leg.multiplyScalar(0.55).add(up.clone().multiplyScalar(0.45)).normalize();
      this.hipQ.slerp(frame(this.P.get(R_HIP)!.clone().sub(this.P.get(L_HIP)!), pelvisUp), 1 - Math.exp(-dt * 10));
    } else this.hipQ.slerp(this.torsoQ, 1 - Math.exp(-dt * 4));

    // ---- the skeleton, posed like a game character's ----
    this.rig.position.set(0, 0, 0); this.rig.scale.setScalar(this.body); this.rig.updateMatrixWorld(true);
    const inv = this.restTorso.clone().invert();
    const dC = this.torsoQ.clone().multiply(inv), dH = this.hipQ.clone().multiply(inv);
    const set = (name: string, delta: THREE.Quaternion, ease = 1) => this.setBone(name, delta, ease), carried = (name: string) => this.carried(name);
    set("root", dH);
    const spine = ["spine05", "spine04", "spine03", "spine02"];
    spine.forEach((nm, i) => set(nm, dH.clone().slerp(dC, (i + 1) / (spine.length + 1))));
    set("spine01", dC);
    // each arm bone turns from where its parent carried it toward your elbow, then your wrist
    const ease = 1 - Math.exp(-dt * 18), relax = 1 - Math.exp(-dt * 5);
    const aim = (bone: string, child: string, from: number, to: number, on: boolean) => {
      const D = carried(bone);
      if (!on) { set(bone, D, relax); return; }
      const rest = this.bp(child).sub(this.bp(bone)).normalize().applyQuaternion(D);
      const target = this.P.get(to)!.clone().sub(this.P.get(from)!).normalize();
      set(bone, new THREE.Quaternion().setFromUnitVectors(rest, target).multiply(D), ease);
    };
    const sides: ["L" | "R", number, number, number, 0 | 1][] = [["L", R_SH, R_EL, R_WR, 0], ["R", L_SH, L_EL, L_WR, 1]];
    for (const [S, sh, el, wr, k] of sides) {
      const vis = l![el].visibility ?? 0;
      // an arm counts once it's clearly seen and stops counting only once it's clearly gone: no flicker
      this.armOn[k] = this.armOn[k] ? vis > 0.4 : vis > 0.6;
      aim(`upperarm01.${S}`, `lowerarm01.${S}`, sh, el, this.armOn[k]);
      aim(`lowerarm01.${S}`, `wrist.${S}`, el, wr, this.armOn[k] && (l![wr].visibility ?? 0) > 0.5);
      // the shoulder helper turns half as far as the arm: the armhole hands over from torso to sleeve in two halves
      const ua = this.bone(`upperarm01.${S}`)!, hb = this.bone(`armhole.${S}`);
      if (hb) set(`armhole.${S}`, carried(`upperarm01.${S}`).slerp(ua.getWorldQuaternion(new THREE.Quaternion()).multiply(this.restQ.get(ua.name)!.clone().invert()), 0.5));
    }
    // the neck leans toward your head
    {
      const eM = this.P.get(L_EAR)!.clone().add(this.P.get(R_EAR)!).multiplyScalar(0.5);
      const D = carried("neck01"), rest = this.bp("head").sub(this.bp("neck01")).normalize().applyQuaternion(D);
      const target = eM.sub(mid).normalize();
      set("neck01", new THREE.Quaternion().slerp(new THREE.Quaternion().setFromUnitVectors(rest, target), 0.6).multiply(D), ease);
    }
    // placed so the skeleton's shoulder joints straddle yours, exactly where the picture shows them
    const jm = this.bone("upperarm01.L")!.getWorldPosition(new THREE.Vector3()).add(this.bone("upperarm01.R")!.getWorldPosition(new THREE.Vector3())).multiplyScalar(0.5);
    this.rig.position.copy(mid).sub(jm);
    this.rig.updateMatrixWorld(true);
    this.key.target.position.copy(mid); this.key.position.copy(mid).add(this.keyOff);
    this.hang(dt);

    this.placed = true;
    if (!this.rig.visible) { this.rig.visible = true; this.onStatus("ready"); }
  }

  /** forearms and hands in front of the body, cut from the video and laid back over the tee */
  private drawArms() {
    const c = this.arms.getContext("2d")!, l = this.lms;
    const W = this.arms.width, H = this.arms.height;
    c.clearRect(0, 0, W, H);
    if (!l || !this.rig.visible) return;
    const P = this.P, torsoZ = (P.get(L_SH)!.z + P.get(R_SH)!.z) / 2;
    const sw = Math.hypot((this.img[L_SH].x - this.img[R_SH].x) * W, (this.img[L_SH].y - this.img[R_SH].y) * H), r = sw * 0.11;
    // the arm as one solid shape: a round-capped stroke along the forearm into the hand, plus the palm.
    // Drawn opaque into a mask (no overlapping sub-paths cancelling each other), softened, then filled with the video
    const m = this.mask, mc = m.getContext("2d")!;
    if (m.width !== W || m.height !== H) { m.width = W; m.height = H; }
    mc.clearRect(0, 0, W, H);
    mc.fillStyle = mc.strokeStyle = "#fff"; mc.lineCap = mc.lineJoin = "round"; mc.lineWidth = 2 * r;
    let any = false;
    for (const [el, wr, ix] of [[L_EL, L_WR, L_IDX], [R_EL, R_WR, R_IDX]]) {
      // only an arm the model is sure of, clearly in front of the chest (camera z grows toward the lens)
      if (Math.min(l[el].visibility ?? 0, l[wr].visibility ?? 0) < 0.75 || P.get(wr)!.z < torsoZ + 0.1) continue;
      any = true;
      const [e, w, i] = [el, wr, ix].map((k) => [this.img[k].x * W, this.img[k].y * H]);
      mc.beginPath(); mc.moveTo(e[0], e[1]); mc.lineTo(w[0], w[1]); mc.lineTo(i[0], i[1]); mc.stroke();
      mc.beginPath(); mc.arc((w[0] + i[0]) / 2, (w[1] + i[1]) / 2, r * 1.35, 0, Math.PI * 2); mc.fill();
    }
    if (!any) return;
    c.filter = `blur(${Math.max(1, r * 0.18).toFixed(1)}px)`;
    c.drawImage(m, 0, 0);
    c.filter = "none";
    c.globalCompositeOperation = "source-in";
    c.drawImage(this.frameCv, 0, 0, W, H);
    c.globalCompositeOperation = "source-over";
  }

  /** the picture as you see it: the mirror, the tee, your hands */
  async snapshot(): Promise<Blob> {
    const W = this.video.videoWidth, H = this.video.videoHeight, out = document.createElement("canvas");
    out.width = W; out.height = H;
    const c = out.getContext("2d")!;
    this.renderer.render(this.scene, this.camera);
    c.save(); c.translate(W, 0); c.scale(-1, 1); c.drawImage(this.frameCv, 0, 0, W, H); c.restore();
    c.drawImage(this.canvas, 0, 0, W, H);
    c.save(); c.translate(W, 0); c.scale(-1, 1); c.drawImage(this.arms, 0, 0, W, H); c.restore();
    return new Promise((res, rej) => out.toBlob((b) => (b ? res(b) : rej(new Error("no image"))), "image/jpeg", 0.92));
  }

  dispose() {
    this.dead = true;
    const v = this.video as HTMLVideoElement & { cancelVideoFrameCallback?: (h: number) => void };
    if (this.vfc) v.cancelVideoFrameCallback?.(this.vfc);
    cancelAnimationFrame(this.raf);
    (this.video.srcObject as MediaStream | null)?.getTracks().forEach((t) => t.stop());
    this.video.srcObject = null;
    this.pose?.close();
    this.renderer.dispose();
  }
}
