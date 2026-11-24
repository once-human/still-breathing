// Live try-on: your camera, the real tee on you, at its real size. Everything runs in this tab: the pose model
// reads each video frame on this device; nothing is recorded, nothing is uploaded.
//
// 1. Pose. MediaPipe's pose landmarker (full model) gives 33 body points per frame: where they are in the
//    picture, and where they are in metres around the hips.
// 2. Camera solve. Those two sets are tied by the camera's projection. A small least-squares solve per frame
//    recovers the camera's focal length (slowly, it doesn't change) and where the body stands in front of it,
//    in metres, from every point the model is sure of: shoulders, elbows, hips, ears, nose.
// 3. The body's frame. Shoulders (and hips when they're in view) give the torso's turn, lean and tilt as a
//    proper 3D rotation, not a flat sticker.
// 4. The tee. The shop tee, the same simulated garment and textures as the viewer, is set on that frame at its
//    real size for the size you pick: the collar at the base of your neck, its depth centred on your chest.
//    Each sleeve hangs from a bone at the shoulder that turns toward your upper arm, blended smoothly into the
//    yoke (normals turn with it, so the light stays right). The cloth simulation runs on top, so the hem and sleeves swing and settle as you move.
// 5. In front and behind. Your neck and head are invisible occluders, so the collar wraps behind your neck and
//    your chin can come down over it. Forearms in front of you are cut from the video and laid back on top.
// 6. Light. The room is read from the video (how bright, what colour, which side the light comes from) and
//    lights the tee through an image-based environment, so black cotton shows its folds.
// 7. Steadiness. The picture you see is not the live video: it is the very camera frame the pose was read
//    from, drawn in the same instant as the tee on it, so the two can never slide against each other however
//    long the pose model takes. The body's shape and where it stands are smoothed separately (One Euro: still
//    when you're still, no lag when you move), the distance to the camera most of all, since that's the
//    noisiest number and the one that would make the tee breathe in size. The sleeves ease to the arms.
//
// The preview is a mirror (the video is flipped). The tee is placed in that mirrored space without being
// flipped itself, so its print reads the right way round.
import * as THREE from "three/webgpu";
import { texture, uv, vec2, vec3, float, normalMap, normalize, vertexColor, mix, positionGeometry, normalGeometry } from "three/tsl";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import type { PoseLandmarker, NormalizedLandmark, Landmark } from "@mediapipe/tasks-vision";
import { Cloth, buildNetAsync, offsetTexture, slopeTextures, clothNodes } from "@/lib/viewer/cloth";
import { KNIT_REPEAT } from "@/lib/viewer/scene";
import { SIZES, type Size } from "@/content/tee";

const ASSET = "/tee/fit/";
export type TryOnStatus = "model" | "camera" | "look" | "ready" | "nobody";

const NOSE = 0, L_EAR = 7, R_EAR = 8, L_SH = 11, R_SH = 12, L_EL = 13, R_EL = 14, L_WR = 15, R_WR = 16, L_IDX = 19, R_IDX = 20, L_HIP = 23, R_HIP = 24;
const SOLVE = [L_SH, R_SH, L_EL, R_EL, L_HIP, R_HIP, L_EAR, R_EAR, NOSE];
const TRACK = [L_SH, R_SH, L_EL, R_EL, L_WR, R_WR, L_HIP, R_HIP, L_EAR, R_EAR, NOSE, L_IDX, R_IDX];

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

const ss = (a: number, b: number, v: number) => { const t = Math.min(1, Math.max(0, (v - a) / (b - a))); return t * t * (3 - 2 * t); };

export class TryOn {
  private renderer: THREE.WebGPURenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(50, 16 / 9, 0.05, 20);
  private rig = new THREE.Group();
  private pose: PoseLandmarker | null = null;
  private offsets = offsetTexture();
  private slopes = slopeTextures();
  private key = new THREE.DirectionalLight(0xffffff, 1);
  private fill = new THREE.HemisphereLight(0xffffff, 0x444444, 0.3);
  private occluders = new THREE.Group();
  private neck: THREE.Mesh; private head: THREE.Mesh;
  private cloth: Cloth | null = null; private m3 = new THREE.Matrix3(); private m4 = new THREE.Matrix4();
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
  private anchor = new THREE.Vector3();           // garment frame: between the shoulder joints
  private bones: THREE.Bone[] = [];               // shoulder bones (+x, -x), waist
  private sleeves: THREE.Bone[] = []; private lifts: THREE.Bone[] = []; private tmpV = new THREE.Vector3(); private armQ = [new THREE.Quaternion(), new THREE.Quaternion()];
  private restArm = [new THREE.Vector3(), new THREE.Vector3()];
  private sizeScale = new THREE.Vector3(1, 1, 1);
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
    Object.assign(this.key.shadow.camera, { left: -0.6, right: 0.6, top: 0.6, bottom: -0.6, near: 0.2, far: 8 });
    this.key.shadow.bias = -0.0004; this.key.shadow.normalBias = 0.015; this.key.shadow.radius = 5;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.scene.add(this.key, this.key.target, this.fill, this.rig, this.occluders);
    this.probe.canvas.width = 16; this.probe.canvas.height = 9;
    this.fctx = frameCv.getContext("2d", { alpha: false, desynchronized: true })!;
    // neck and head: depth only, drawn first, so the tee is hidden wherever they are in front of it
    const occ = this.occMat;
    this.neck = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 1, 20, 1, true), occ);
    this.head = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 16), occ);
    for (const m of [this.neck, this.head]) { m.renderOrder = -1; m.castShadow = true; this.occluders.add(m); }
    this.occluders.visible = false;
  }

  async start(design: string, tee: "black" | "cream", size: Size) {
    this.onStatus("model");
    const [{ PoseLandmarker, FilesetResolver }] = await Promise.all([import("@mediapipe/tasks-vision"), this.renderer.init()]);
    const files = await FilesetResolver.forVisionTasks("/mediapipe");
    const opts = (delegate: "GPU" | "CPU", model: string) => ({
      baseOptions: { modelAssetPath: `/mediapipe/pose_landmarker_${model}.task`, delegate },
      runningMode: "VIDEO" as const, numPoses: 1, minPoseDetectionConfidence: 0.5, minPosePresenceConfidence: 0.5, minTrackingConfidence: 0.6,
    });
    // a phone, a small laptop or a browser without WebGPU starts one step down (the lighter pose model); every
    // device is then watched frame by frame and eased down further only if it can't keep up (see govern)
    const weak = /iPhone|iPad|Android/i.test(navigator.userAgent) || (navigator.hardwareConcurrency || 8) <= 4 || !("gpu" in navigator);
    this.tier = weak ? 1 : 0;
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
    void tee;
    const gl = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath("/draco/"));
    const [gltf, c, o, n, k] = await Promise.all([
      gl.loadAsync(`${ASSET}form-M/stand.glb`), this.tx(`tex/color-${design}-${tee}.jpg`, true), this.tx(`tex/orm-${design}-${tee}.png`, false),
      this.tx("tex/normal-M.png", false), this.tx("tex/knit-normal.png", false),
    ]);
    k.wrapS = k.wrapT = THREE.RepeatWrapping;
    const colorN = texture(c), ormN = texture(o);
    this.colorN = colorN; this.ormN = ormN;
    const cloth = clothNodes(this.offsets, this.slopes);
    const outer = new THREE.MeshPhysicalNodeMaterial({ roughness: 1, metalness: 0, specularIntensity: 0.5 });
    outer.colorNode = colorN;
    outer.roughnessNode = ormN.g;
    outer.aoNode = mix(float(1), vertexColor().r, 0.85);
    outer.sheenNode = vec3(float(0.35 * 0.06).mul(float(1).sub(ormN.b)));
    outer.sheenRoughnessNode = float(0.3);
    const n1 = texture(n).xyz.mul(2).sub(1), kk = texture(k, uv().mul(vec2(KNIT_REPEAT[0], KNIT_REPEAT[1]))).xyz.mul(2).sub(1);
    outer.normalNode = cloth.bend(normalMap(normalize(vec3(n1.xy.add(kk.xy.mul(0.55)), n1.z.mul(kk.z))).mul(0.5).add(0.5)));
    outer.positionNode = cloth.position;

    // the tee's geometry in its own frame. Only the outer shell: the inner one is only ever seen through the neck
    // and sleeve openings, and on a body those are filled by you (it showed as black shards round the collar)
    let parts: { geo: THREE.BufferGeometry; pos: Float32Array; idx: Uint32Array }[] = [];
    gltf.scene.updateMatrixWorld(true);
    gltf.scene.traverse((ob) => {
      const m = ob as THREE.Mesh;
      if (!m.isMesh) return;
      const geo = m.geometry.clone().applyMatrix4(m.matrixWorld);
      const pos = geo.attributes.position.array as Float32Array;
      const idx = geo.index ? Uint32Array.from(geo.index.array) : Uint32Array.from({ length: pos.length / 3 }, (_, i) => i);
      parts.push({ geo, pos, idx });
    });
    const girth = (p: { geo: THREE.BufferGeometry }) => { p.geo.computeBoundingBox(); const b = p.geo.boundingBox!; return b.max.x - b.min.x + b.max.z - b.min.z; };
    parts = [parts.reduce((a, b) => (girth(b) > girth(a) ? b : a))];

    // its landmarks, measured on the mesh
    let yTop = -1e9;
    for (const p of parts) for (let i = 1; i < p.pos.length; i += 3) yTop = Math.max(yTop, p.pos[i]);
    let zs = 0, zn = 0;
    for (const p of parts) for (let i = 0; i < p.pos.length; i += 3) { const y = p.pos[i + 1]; if (y < yTop - 0.08 && y > yTop - 0.16 && Math.abs(p.pos[i]) < 0.1) { zs += p.pos[i + 2]; zn++; } }
    // between the shoulder joints: 6 cm under the top of the shoulder line, at the chest's mid depth
    this.anchor.set(0, yTop - 0.06, zn ? zs / zn : 0);
    // the body's side and the armpit, measured on the draped mesh (the cut-on sleeve starts where the body ends)
    let B = 0;
    for (const p of parts) for (let i = 0; i < p.pos.length; i += 3) { const y = p.pos[i + 1]; if (y < yTop - 0.38 && y > yTop - 0.46) B = Math.max(B, Math.abs(p.pos[i])); }
    let armpit = yTop - 0.29;
    for (let d = 0.2; d < 0.4; d += 0.01) {
      let m = 0;
      for (const p of parts) for (let i = 0; i < p.pos.length; i += 3) { const y = p.pos[i + 1]; if (y < yTop - d && y > yTop - d - 0.01) m = Math.max(m, Math.abs(p.pos[i])); }
      if (m < B + 0.012) { armpit = yTop - d + 0.03; break; }
    }
    // round the collar, any surface that faces in toward the body (the inside of the neckband, mostly the back
    // half) is never seen on a person: your neck and shoulders fill it. It's cut, so only the outside shows
    {
      const P = positionGeometry, N = normalGeometry;
      const collar = P.y.greaterThan(yTop - 0.13).and(P.x.abs().lessThan(0.17));
      const inward = N.x.mul(P.x).add(N.z.mul(P.z.sub(this.anchor.z))).lessThan(0);
      outer.maskNode = collar.and(inward).not();
    }
    const joints = [new THREE.Vector3(0.18, yTop - 0.06, this.anchor.z), new THREE.Vector3(-0.18, yTop - 0.06, this.anchor.z)];

    // a skeleton: the body; a shoulder bone per side across the yoke with the sleeve hanging from it; a waist bone
    // that follows your hips; and a bone per side that lifts the body under the arm when the arm goes up
    const root = new THREE.Bone();
    this.bones = joints.map((j) => { const b = new THREE.Bone(); b.position.copy(j); root.add(b); return b; });
    let yBot = 1e9;
    for (const p of parts) for (let i = 1; i < p.pos.length; i += 3) yBot = Math.min(yBot, p.pos[i]);
    { const b = new THREE.Bone(); b.position.set(0, yTop - 0.45, this.anchor.z); root.add(b); this.bones.push(b); }
    this.sleeves = this.bones.slice(0, 2).map((sb) => { const b = new THREE.Bone(); sb.add(b); return b; });
    this.lifts = [0, 1].map(() => { const b = new THREE.Bone(); root.add(b); return b; });
    root.updateMatrixWorld(true);
    // bone indices: 0 root, 1-2 shoulders, 3 waist, 4-5 sleeves, 6-7 lifts
    const skeleton = new THREE.Skeleton([root, ...this.bones, ...this.sleeves, ...this.lifts]);
    const sums = [new THREE.Vector3(), new THREE.Vector3()], cnt = [0, 0];
    const meshes: THREE.SkinnedMesh[] = [];
    for (const p of parts) {
      const nv = p.pos.length / 3, SI = new Uint16Array(4 * nv), SW = new Float32Array(4 * nv);
      for (let v = 0; v < nv; v++) {
        const x = p.pos[3 * v], y = p.pos[3 * v + 1], ax = Math.abs(x), s = x >= 0 ? 0 : 1;
        const above = ss(armpit - 0.02, armpit + 0.03, y);
        // the whole sleeve, underside included: everything outside the body's side line, so it rises as a tube
        const a = ss(B - 0.005, B + 0.03, ax) * Math.max(above, ss(B + 0.005, B + 0.025, ax) * ss(armpit - 0.09, armpit - 0.04, y));
        // the yoke between the neck and the sleeve takes a share of the turn
        const w = Math.max(a, ss(0.07, B, ax) * above);
        // the side under the arm rises with it (the hem lifts on that side, as on a real tee)
        const lift = (1 - w) * ss(0.04, B, ax) * ss(yBot - 0.1, armpit, y) * (1 - ss(armpit, armpit + 0.1, y));
        const h = (1 - w - lift) * ss(armpit - 0.05, yBot + 0.04, y);
        const inf: [number, number][] = [[0, 1 - w - lift - h], [1 + s, w - a], [4 + s, a], [6 + s, lift], [3, h]];
        inf.sort((m, n) => n[1] - m[1]);
        const tot = inf[0][1] + inf[1][1] + inf[2][1] + inf[3][1] || 1;
        for (let k = 0; k < 4; k++) { SI[4 * v + k] = inf[k][0]; SW[4 * v + k] = Math.max(0, inf[k][1]) / tot; }
        if (a > 0.9) { sums[s].x += x; sums[s].y += y; sums[s].z += p.pos[3 * v + 2]; cnt[s]++; }
      }
      p.geo.setAttribute("skinIndex", new THREE.Uint16BufferAttribute(SI, 4));
      p.geo.setAttribute("skinWeight", new THREE.Float32BufferAttribute(SW, 4));
      p.geo.setAttribute("sbI", new THREE.BufferAttribute(new Float32Array(4 * nv), 4));
      p.geo.setAttribute("sbW", new THREE.BufferAttribute(new Float32Array(4 * nv), 4));
      const sm = new THREE.SkinnedMesh(p.geo, outer);
      sm.frustumCulled = false; sm.receiveShadow = true;
      meshes.push(sm);
    }
    meshes[0].add(root);
    for (const sm of meshes) { sm.bind(skeleton); this.rig.add(sm); }
    for (const s of [0, 1] as const) {
      this.restArm[s].copy(cnt[s] ? sums[s].divideScalar(cnt[s]).sub(joints[s]).normalize() : new THREE.Vector3(s ? -0.64 : 0.64, -0.77, 0));
    }
    this.rig.visible = false;
    // the cloth net builds in a worker; until it's ready the tee is simply held on the body
    buildNetAsync(parts.map((p) => ({ pos: p.pos, idx: p.idx }))).then((net) => {
      if (this.dead) return;
      parts.forEach((p, i) => {
        const I = p.geo.attributes.sbI as THREE.BufferAttribute, W = p.geo.attributes.sbW as THREE.BufferAttribute;
        (I.array as Float32Array).set(net.skins[i].I); (W.array as Float32Array).set(net.skins[i].W); I.needsUpdate = W.needsUpdate = true;
      });
      this.cloth = new Cloth(net, this.offsets, this.slopes);
      // worn cloth: no breeze, and the same gentle inertia as the shop viewer. More than that and every bit of
      // tracking noise reads as motion: the whole tee shivers and the sleeves tear
      this.cloth.wind = false;
    }).catch(() => {});
  }

  /** a different design on the same tee */
  async setLook(design: string, tee: "black" | "cream") {
    if (!this.colorN || !this.ormN) return;
    const [c, o] = await Promise.all([this.tx(`tex/color-${design}-${tee}.jpg`, true), this.tx(`tex/orm-${design}-${tee}.png`, false)]);
    this.colorN.value = c; this.ormN.value = o;
  }

  /** the real garment for that size: wider and longer by the size chart, from the simulated M */
  setSize(s: Size) {
    const w = SIZES[s].chest_round / SIZES.M.chest_round, l = SIZES[s].length / SIZES.M.length;
    this.sizeScale.set(w, l, w);
  }

  /**
   * Smooth on any device: the time each camera frame takes here (read the pose, place the tee, draw) is measured.
   * If it keeps running past the camera's own frame time, the try-on eases down one step and stays there:
   * 1 the lighter pose model, 2 lower render resolution and no soft shadow, 3 no cloth simulation.
   * It never goes back up mid-session, so nothing flickers between levels.
   */
  private govern(busy: number, interval: number) {
    this.busy = this.busy ? this.busy + (busy - this.busy) * 0.1 : busy;
    const budget = Math.max(14, Math.min(40, interval * 1000)) * 0.85;
    this.over = this.busy > budget ? this.over + 1 : 0;
    if (this.over < 45 || this.tier >= 3 || this.swapping) return;
    this.over = 0; this.busy = 0; this.tier++;
    if (this.tier === 1 && this.makePose) {
      this.swapping = true;
      this.makePose("lite").then((p) => { if (this.dead) { p.close(); return; } const old = this.pose; this.pose = p; old?.close(); }).catch(() => {}).finally(() => { this.swapping = false; });
    }
    if (this.tier === 2) { this.key.castShadow = false; this.resize(); }
  }

  resize() {
    const r = this.canvas.getBoundingClientRect(), dpr = Math.min(devicePixelRatio || 1, this.tier >= 2 ? 1 : 1.5);
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
    if (this.cloth && this.rig.visible && this.tier < 3) {
      this.cloth.setPose(this.m3.setFromMatrix4(this.m4.makeRotationFromQuaternion(this.rig.quaternion)), this.rig.position, this.rig.scale.x, dt);
      this.cloth.step(dt);
    }
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
    const sx = (right - left) / (right + left + 1e-3), sy = (top - bot) / (top + bot + 1e-3);
    // the room is read every few frames; the tee eases toward it so a camera's auto-exposure never makes it flicker
    const k = this.lit ? 1 - Math.exp(-dt * 3) : 1; this.lit = true;
    this.tint.lerp(new THREE.Color(0.35 + 0.65 * r / m, 0.35 + 0.65 * g / m, 0.35 + 0.65 * b / m), k);
    this.lum += (lum - this.lum) * k; this.side.x += (sx - this.side.x) * k; this.side.y += (sy - this.side.y) * k;
    this.scene.environmentIntensity = 0.3 + this.lum * 1.3;
    this.key.color.copy(this.tint); this.key.intensity = 0.5 + this.lum * 2.4;
    this.fill.color.copy(this.tint); this.fill.intensity = 0.15 + this.lum * 0.4;
    this.keyOff.set(this.side.x * 3, 1.5 + this.side.y * 2, 1.5);
    if (this.placed) this.key.target.position.copy(this.rig.position);
  }

  /** the camera solve, the body's frame, and the tee on it */
  private place(l: NormalizedLandmark[] | null, w: Landmark[] | null, t: number, dt: number) {
    const ok = l && w && (l[L_SH].visibility ?? 0) > 0.55 && (l[R_SH].visibility ?? 0) > 0.55;
    if (!ok) {
      if (++this.lost > 6) { this.rig.visible = false; this.occluders.visible = false; this.placed = false; this.lms = null; this.filt.forEach((f) => f.reset()); this.tFilt.reset(); this.midU.reset(); this.midV.reset(); this.body = 0; this.onStatus("nobody"); }
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
      let f = this.filt.get(i); if (!f) this.filt.set(i, (f = new Euro3(0.9, 2.5)));
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
      // and fitted to you: the form's shoulder joints are 36 cm apart, yours are what the model measures. Learned
      // over a second or two, so the tee never breathes in size, and the size you pick is on top of that
      const k = Math.min(1.35, Math.max(0.8, this.P.get(L_SH)!.distanceTo(this.P.get(R_SH)!) / 0.36));
      this.body = this.body ? this.body + (k - this.body) * (1 - Math.exp(-dt / 1.5)) : k;
    }
    this.lms = l;
    this.img = l!.map((p) => ({ x: p.x, y: p.y }));

    // the torso's frame: the tee's +x is the shoulder on the preview's right (landmark 12, mirrored)
    const sL = this.P.get(L_SH)!, sR = this.P.get(R_SH)!, mid = sL.clone().add(sR).multiplyScalar(0.5);
    const xA = sR.clone().sub(sL).normalize();
    let up = new THREE.Vector3(0, 1, 0);
    if ((l![L_HIP].visibility ?? 0) > 0.6 && (l![R_HIP].visibility ?? 0) > 0.6) up = mid.clone().sub(this.P.get(L_HIP)!.clone().add(this.P.get(R_HIP)!).multiplyScalar(0.5)).normalize();
    const zA = new THREE.Vector3().crossVectors(xA, up).normalize(), yA = new THREE.Vector3().crossVectors(zA, xA).normalize();
    // the torso's turn is the noisiest thing the pose model gives (depth from one camera), so it gets its own
    // filter: it holds still when you hold still and follows with almost no lag when you turn
    const qNew = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(xA, yA, zA));
    if (!this.placed) { this.rig.quaternion.copy(qNew); this.qSpeed = 0; }
    else {
      const speed = this.rig.quaternion.angleTo(qNew) / Math.max(dt, 1e-3);
      this.qSpeed += (speed - this.qSpeed) * (1 - Math.exp(-dt * 8));
      const cut = 1.2 + 2.2 * this.qSpeed, rr = 2 * Math.PI * cut * dt;
      this.rig.quaternion.slerp(qNew, rr / (rr + 1));
    }
    this.rig.scale.copy(this.sizeScale).multiplyScalar(this.body);
    this.rig.position.copy(mid).sub(this.anchor.clone().multiply(this.rig.scale).applyQuaternion(this.rig.quaternion));
    this.rig.updateMatrixWorld();
    this.key.target.position.copy(this.rig.position); this.key.position.copy(this.rig.position).add(this.keyOff);

    // sleeves: each bone turns from the sleeve's rest line toward the upper arm (garment frame)
    const inv = this.rig.matrixWorld.clone().invert();
    const pairs: [number, number, 0 | 1][] = [[R_SH, R_EL, 0], [L_SH, L_EL, 1]];
    const ease = 1 - Math.exp(-dt * 16);
    for (const [sh, el, s] of pairs) {
      const vis = l![el].visibility ?? 0;
      // an arm counts once it's clearly seen and stops counting only once it's clearly gone: no flicker
      this.armOn[s] = this.armOn[s] ? vis > 0.4 : vis > 0.6;
      const cur = this.armQ[s];
      if (!this.armOn[s]) { cur.slerp(new THREE.Quaternion(), 1 - Math.exp(-dt * 5)); this.splitArm(s); continue; }
      const J = this.P.get(sh)!.clone().applyMatrix4(inv), E = this.P.get(el)!.clone().applyMatrix4(inv);
      const q = new THREE.Quaternion().setFromUnitVectors(this.restArm[s], E.sub(J).normalize());
      // past about 100 degrees a cut-on sleeve can't follow without tearing the yoke: hold it there
      const ang = 2 * Math.acos(Math.min(1, Math.abs(q.w)));
      if (ang > 1.75) q.slerp(new THREE.Quaternion(), 1 - 1.75 / ang);
      cur.slerp(q, ease); this.splitArm(s);
    }

    // the lower body follows the hips: their line, relative to the shoulders', twists and tilts the hem
    {
      const hip = this.bones[2], both = (l![L_HIP].visibility ?? 0) > 0.6 && (l![R_HIP].visibility ?? 0) > 0.6;
      if (both) {
        const hl = this.P.get(L_HIP)!.clone().applyMatrix4(inv), hr = this.P.get(R_HIP)!.clone().applyMatrix4(inv);
        const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), hr.sub(hl).normalize());
        const ang = 2 * Math.acos(Math.min(1, Math.abs(q.w)));
        if (ang > 0.6) q.slerp(new THREE.Quaternion(), 1 - 0.6 / ang);
        hip.quaternion.slerp(q, 1 - Math.exp(-dt * 10));
      } else hip.quaternion.slerp(new THREE.Quaternion(), 1 - Math.exp(-dt * 4));
    }

    // neck and head occluders
    const eL = this.P.get(L_EAR)!, eR = this.P.get(R_EAR)!, headC = eL.clone().add(eR).multiplyScalar(0.5);
    const headR = Math.max(0.07, eL.distanceTo(eR) * 0.62);
    this.head.position.copy(headC); this.head.scale.setScalar(headR);
    const neckBase = mid.clone().add(zA.clone().multiplyScalar(-0.02)), neckTop = headC.clone().add(yA.clone().multiplyScalar(-headR * 0.5));
    const nl = Math.max(0.02, neckBase.distanceTo(neckTop)), nr = Math.max(0.045, sL.distanceTo(sR) * 0.16);
    this.neck.position.copy(neckBase).add(neckTop).multiplyScalar(0.5);
    this.neck.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), neckTop.clone().sub(neckBase).normalize());
    this.neck.scale.set(nr, nl, nr * 0.9);
    this.occluders.visible = true;

    this.placed = true;
    if (!this.rig.visible) { this.rig.visible = true; this.onStatus("ready"); }
  }

  /** the arm's turn, shared: 25% at the shoulder across the yoke, the rest in the sleeve */
  private splitArm(s: 0 | 1) {
    const q = this.armQ[s], sh = this.bones[s].quaternion.identity().slerp(q, 0.25);
    this.sleeves[s].quaternion.copy(sh).invert().multiply(q);
    // how far the arm has come up from hanging: 0 at rest, about 1 at shoulder height
    const r = this.restArm[s], dy = this.tmpV.copy(r).applyQuaternion(q).y;
    this.lifts[s].position.y = 0.055 * Math.min(1.6, Math.max(0, (dy - r.y) / Math.max(0.2, -r.y)));
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
