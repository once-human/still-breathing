// The cloth's own thread: builds the net from the tee (and the skin under it), then steps the simulation whenever the
// page asks, sending back the offsets and slopes for the shader. See clothsim.ts for the physics.
import { Cloth, M3, V3c, buildNet, SUB_DT, TEX_W, TEX_H, type Out } from "./clothsim";

type Frame = { off: Float32Array; s0: Float32Array; s1: Float32Array; s2: Float32Array };
const N = TEX_W * TEX_H * 4;
const out = (d: Float32Array): Out => ({ image: { data: d }, needsUpdate: false });
let cloth: Cloth | null = null, token = 0;
// the cloth keeps these four objects; only the arrays inside them travel to the page and back
const tex = out(new Float32Array(N)), slopes = [out(new Float32Array(N)), out(new Float32Array(N)), out(new Float32Array(N))];
/** an array that is on its way to the page (or lost with a stopped tee) is replaced before it's written */
const whole = () => { for (const t of [tex, ...slopes]) if (t.image.data.length !== N) t.image.data = new Float32Array(N); };
const still = new M3(), at = new V3c();
const post = (m: unknown, t: Transferable[] = []) => (self as unknown as Worker).postMessage(m, t);

self.onmessage = (e: MessageEvent) => {
  const m = e.data;
  if (m.type === "stop") { cloth = null; return; }
  if (m.type === "init") {
    cloth = null; token = m.token;
    try {
      const net = buildNet(m.meshes, 0.03, TEX_W * TEX_H, SUB_DT);
      const skins = net.skins.map((s) => ({ I: s.I.slice(), W: s.W.slice() }));
      post({ type: "net", token, skins }, skins.flatMap((s) => [s.I.buffer, s.W.buffer]));
      whole(); for (const t of [tex, ...slopes]) t.image.data.fill(0);
      const c = new Cloth(net, tex as never, slopes as never);
      if (m.body && m.body.pos.length) c.setBody(m.body.pos, m.body.nrm);
      c.wind = m.wind;
      at.x = 0; at.y = m.lift; at.z = 0;
      cloth = c;
    } catch (err) { post({ type: "error", token, error: String(err) }); }
    return;
  }
  if (m.type === "step") {
    // the page's buffers come back to be written again (one set goes back and forth, nothing is allocated)
    const f = m.frame as Frame | null;
    if (f) { tex.image.data = f.off; slopes[0].image.data = f.s0; slopes[1].image.data = f.s1; slopes[2].image.data = f.s2; }
    if (!cloth || m.token !== token) return;
    whole();
    // the person stands still while the camera walks round: the garment's frame never moves, only the air does
    cloth.setPose(still, at, 1, m.dt);
    const moving = cloth.step(m.dt);
    const fr: Frame = { off: tex.image.data, s0: slopes[0].image.data, s1: slopes[1].image.data, s2: slopes[2].image.data };
    post({ type: "frame", token, moving, frame: fr }, [fr.off.buffer, fr.s0.buffer, fr.s1.buffer, fr.s2.buffer]);
  }
};
