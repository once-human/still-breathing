// Real-time cloth: the tee lags and settles as it turns, and a slow breeze moves through it.
//
// The render mesh (~340k vertices, both shells) is far too heavy to simulate per frame, so a coarse particle
// net is built from it: one particle per 3 cm cell, edges wherever the mesh connects two cells. Each particle
// is a mass on a spring toward where the garment rests (the rest pose already holds gravity and the form's
// support). Only the neckband sits fixed on the form; the yoke and chest are carried but still give a little,
// and below them and along the sleeves the cloth hangs free with the swing of 240 GSM cotton: a pendulum of
// the cloth below it, settled by knit friction and the air in a swing or two.
// Distance constraints along the edges keep the jersey from stretching, so motion travels through it the way it
// does through real knit. The simulation runs in world space while the garment is turned, so inertia is real.
//
// Wind: light air (a room with the door open) moves through it. Gusts travel across the cloth as waves (so a ripple runs from
// one side seam to the other), the direction drifts, and there are lulls when it drops to a soft draught (it never stops dead). The
// push is aerodynamic: it acts along each patch's normal and against the patch's own velocity, so a panel
// facing the breeze bellies, one edge-on barely moves, and fast swings are damped by the air.
//
// The body is solid: every particle knows the skin under it (the nearest point of the body and its outward
// normal) and may come in only until it rests on it, a few millimetres off, or wherever it already hung if that is
// closer. A gust presses the tee onto the chest and stops there; it never passes into the body.
//
// Folds and creases are not painted on: the net's own shape is the cloth's shape. Each frame the slope of the
// displacement around every particle (how the cloth around it is tilted, bunched or pulled) is measured, and
// the shading follows it, so a ripple the breeze runs across the back catches the light exactly as the moving
// cloth would, and on still cloth there is nothing at all.
//
// The net and each vertex's skin (its 4 nearest particles) are built in a Worker, so the tee is on screen and
// turning while that runs. Offsets and slopes reach the vertex shader through small float textures, so
// the CPU only ever touches the net. Once everything is still, both snap to exactly zero: the path tracer's
// geometry is the rest pose, so the two always agree.
import * as THREE from "three/webgpu";
import { attribute, textureLoad, ivec2, int, floor, positionLocal, normalLocal, length, max, float, vec4, modelViewMatrix, normalMap, varying } from "three/tsl";
import { TEX_W, TEX_H, SLOPE_MAX } from "./clothsim";

export { TEX_W, TEX_H };

type Mesh = { pos: Float32Array; idx: Uint32Array };
type Frame = { off: Float32Array; s0: Float32Array; s1: Float32Array; s2: Float32Array };

/**
 * The page's end of the cloth. The net is built and the cloth simulated in a Worker; each frame the page hands it the
 * frame's length and gets back the last step's offsets and slopes, which it copies into the shader's textures. One
 * step is in flight at a time: if the worker is still busy the last shape stays up (and the time carries over), so
 * a slow frame there never holds up a frame here.
 */
export class ClothLink {
  private w: Worker;
  private token = 0;
  private frame: Frame | null = null;
  private ready = false;
  private inFlight = false;
  private owed = 0;
  /** still moving as of the last step that came back */
  moving = false;

  constructor(private tex: THREE.DataTexture, private slopes: THREE.DataTexture[]) {
    this.w = new Worker(new URL("./cloth.worker.ts", import.meta.url));
    this.w.onmessage = (e) => this.got(e.data);
  }
  private onNet: ((skins: { I: Float32Array; W: Float32Array }[]) => void) | null = null;

  /**
   * A new tee (the last one's cloth stops). onNet gets each mesh's skin (its 4 particles and weights) once the
   * net is built; the cloth runs from then on.
   */
  start(meshes: Mesh[], body: { pos: Float32Array; nrm: Float32Array } | null, lift: number, wind: boolean, onNet: (skins: { I: Float32Array; W: Float32Array }[]) => void) {
    const token = ++this.token;
    this.ready = false; this.inFlight = false; this.owed = 0; this.moving = false; this.onNet = onNet;
    const copies = meshes.map((m) => ({ pos: m.pos.slice(), idx: Uint32Array.from(m.idx) }));
    const send: Transferable[] = copies.flatMap((c) => [c.pos.buffer, c.idx.buffer]);
    if (body) send.push(body.pos.buffer, body.nrm.buffer);
    this.w.postMessage({ type: "init", token, meshes: copies, body, lift, wind }, send);
  }
  stop() { ++this.token; this.ready = false; this.inFlight = false; this.moving = false; this.w.postMessage({ type: "stop" }); }

  private got(m: { type: string; token: number; skins?: { I: Float32Array; W: Float32Array }[]; frame?: Frame; moving?: boolean; error?: string }) {
    if (m.token !== this.token) { if (m.frame) this.frame = m.frame; return; }
    if (m.type === "error") { console.info("cloth off", m.error); return; }
    if (m.type === "net") { this.onNet?.(m.skins!); this.ready = true; return; }
    if (m.type === "frame") {
      const f = m.frame!, t = this.tex.image.data as Float32Array;
      t.set(f.off); this.tex.needsUpdate = true;
      [f.s0, f.s1, f.s2].forEach((d, i) => { (this.slopes[i].image.data as Float32Array).set(d); this.slopes[i].needsUpdate = true; });
      this.frame = f; this.moving = !!m.moving; this.inFlight = false;
    }
  }

  /** this frame's length: asks for the next step (if none is in flight); true while the cloth was last seen moving */
  step(dt: number) {
    if (!this.ready) return false;
    this.owed = Math.min(0.05, this.owed + dt);
    if (!this.inFlight && this.owed > 0) {
      const f = this.frame; this.frame = null; this.inFlight = true;
      this.w.postMessage({ type: "step", token: this.token, dt: this.owed, frame: f }, f ? [f.off.buffer, f.s0.buffer, f.s1.buffer, f.s2.buffer] : []);
      this.owed = 0;
    }
    return this.moving;
  }
  dispose() { this.w.terminate(); }
}

/** the shared offset texture (one per renderer, reused for every tee) */
export function offsetTexture() {
  const t = new THREE.DataTexture(new Float32Array(TEX_W * TEX_H * 4), TEX_W, TEX_H, THREE.RGBAFormat, THREE.FloatType);
  t.magFilter = t.minFilter = THREE.NearestFilter; t.generateMipmaps = false; t.needsUpdate = true;
  return t;
}

/** the three rows of each particle's displacement slope (same layout as the offsets) */
export function slopeTextures() { return [offsetTexture(), offsetTexture(), offsetTexture()]; }

/** vertex shader node: rest position + the cloth offset, blended from the 4 particles this vertex follows */
export function clothedPosition(offsets: THREE.DataTexture) {
  return clothNodes(offsets, null).position;
}

/**
 * The full cloth for a material: `position` for positionNode, and `bend(n)` to turn a view-space shading
 * normal by the cloth's slope at that point. Everything is read in the vertex shader (the particle indices
 * can't be interpolated) and handed to the fragment as one smooth vector.
 */
export function clothNodes(offsets: THREE.DataTexture, slopes: THREE.DataTexture[] | null) {
  const I = attribute("sbI", "vec4"), Wt = attribute("sbW", "vec4");
  const at = (tex: THREE.DataTexture, f: typeof I.x) => {
    const row = floor(f.div(TEX_W));
    return textureLoad(tex, ivec2(int(f.sub(row.mul(TEX_W))), int(row))).xyz;
  };
  const blend = (tex: THREE.DataTexture) => at(tex, I.x).mul(Wt.x).add(at(tex, I.y).mul(Wt.y)).add(at(tex, I.z).mul(Wt.z)).add(at(tex, I.w).mul(Wt.w));
  const position = positionLocal.add(blend(offsets));
  if (!slopes) return { position, bend: <T,>(n: T) => n };
  // a surface whose points move by o(x) turns its normal n by -(do/dx)^T n. Built from the vertex's own normal,
  // it's right for both shells whichever way each faces; zero (exactly) wherever the cloth is at rest.
  const n = normalLocal, r0 = blend(slopes[0]), r1 = blend(slopes[1]), r2 = blend(slopes[2]);
  const raw = r0.mul(n.x).add(r1.mul(n.y)).add(r2.mul(n.z)).negate();
  const tang = raw.sub(n.mul(n.dot(raw)));
  const tilt = tang.mul(float(SLOPE_MAX).div(max(length(tang), float(SLOPE_MAX))));
  const tiltView = varying(modelViewMatrix.mul(vec4(tilt, 0)).xyz, "vClothTilt");
  return { position, bend: (nv: ReturnType<typeof normalMap>) => nv.add(tiltView).normalize() };
}
