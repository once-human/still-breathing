// Host side of the WebGPU path tracer: uploads the tee (BVH, triangles, textures), then traces one
// sample per pixel per frame into a float buffer and shows the running average.
import { TRACE_WGSL, SHOW_WGSL, DENOISE_WGSL } from "./pt.wgsl";
import { buildBVHAsync } from "./bvh";
import { CAMERA, VFOV, ASPECT, KNIT_REPEAT, cameraBasis, lightFrame, radiance, turnY, type Camera, type Scene, type V3 } from "./scene";

/**
 * col: linear albedo per vertex (the person's denim and eyes, a tint on the skin); white elsewhere.
 * skin: the person's skin maps (pipeline/skin.py): colour, and relief + roughness (normal in R, G, roughness in B)
 */
export type TeeGeometry = {
  pos: Float32Array; nrm: Float32Array; uv: Float32Array; idx: Uint32Array; mat: Uint8Array; col?: Float32Array;
  skin?: { albedo: ImageBitmap; rn: ImageBitmap };
};
/** back: the back print, front: the chest print (both premultiplied, at print resolution) */
export type TeeImages = { back: ImageBitmap; front: ImageBitmap; normal: ImageBitmap; knit: ImageBitmap };
export type View = { yaw: number; crop: [number, number, number]; knit: boolean };

const U_SIZE = 256 + 6 * 80;

export class PathTracer {
  device!: GPUDevice;
  ctx!: GPUCanvasContext;
  format!: GPUTextureFormat;
  w = 0; h = 0;
  frame = 0;
  private trace!: GPUComputePipeline;
  private show!: GPURenderPipeline;
  private ubuf!: GPUBuffer;
  private dims!: GPUBuffer;
  private accum: GPUBuffer | null = null;
  private gbuf: GPUBuffer | null = null;
  private dn: [GPUBuffer, GPUBuffer] | null = null;
  private dnPipe!: GPUComputePipeline;
  private dnU: GPUBuffer[] = [];
  private dnBG: GPUBindGroup[] | null = null;
  private showDnBG: GPUBindGroup | null = null;
  /** true once denoise() has run on the current samples */
  clean = false;
  /** the accumulated linear image (rgb + sample weight per pixel) */
  readAccum() { return this.readBuf(this.accum!); }
  private async readBuf(buf: GPUBuffer) {
    const d = this.device, size = this.w * this.h * 16;
    const rb = d.createBuffer({ size, usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST });
    const enc = d.createCommandEncoder(); enc.copyBufferToBuffer(buf, 0, rb, 0, size); d.queue.submit([enc.finish()]);
    await rb.mapAsync(GPUMapMode.READ);
    const a = new Float32Array(rb.getMappedRange().slice(0)); rb.unmap(); rb.destroy();
    return a;
  }
  /** the finished frame as 8-bit sRGB, through the same view transform the screen uses */
  async toImageData() {
    const a = this.clean ? await this.readBuf(this.dn![0]) : await this.readAccum(), n = this.w * this.h, out = new ImageData(this.w, this.h), o = out.data;
    const c = [0, 0, 0];
    for (let i = 0; i < n; i++) {
      const w = a[i * 4 + 3] || 1;
      c[0] = a[i * 4] / w; c[1] = a[i * 4 + 1] / w; c[2] = a[i * 4 + 2] / w;
      const m = neutral(c);
      o[i * 4] = srgb8(m[0]); o[i * 4 + 1] = srgb8(m[1]); o[i * 4 + 2] = srgb8(m[2]); o[i * 4 + 3] = 255;
    }
    return out;
  }
  /** debug: mean displayed sRGB (0-255) of a box given in 0..1 frame coordinates, after the same view transform */
  async probe(x0: number, y0: number, x1: number, y1: number) {
    const a = await this.readAccum();
    const out = [0, 0, 0], lin = [0, 0, 0]; let n = 0;
    for (let y = Math.floor(y0 * this.h); y < y1 * this.h; y++) for (let x = Math.floor(x0 * this.w); x < x1 * this.w; x++) {
      const i = (y * this.w + x) * 4, w = a[i + 3] || 1, c = [a[i] / w, a[i + 1] / w, a[i + 2] / w];
      const m = neutral(c).map(srgb8);
      for (let k = 0; k < 3; k++) { out[k] += m[k]; lin[k] += c[k]; } n++;
    }
    return { srgb: out.map((v) => Math.round(v / n)), linear: lin.map((v) => +(v / n).toFixed(4)), spp: this.frame };
  }
  private geo: { nodes: GPUBuffer; tris: GPUBuffer; triv: GPUBuffer; verts: GPUBuffer } | null = null;
  private tex: Record<string, GPUTexture> = {};
  /** the person's skin maps (1 x 1 stand-ins without a person) */
  private skinTex: GPUTexture[] = [];
  /** the venue's 360 degree picture (a 1 x 1 stand-in until it arrives, or where there is none) */
  private envTex: GPUTexture | null = null;
  private sampler!: GPUSampler;
  private traceBG: GPUBindGroup | null = null;
  private showBG: GPUBindGroup | null = null;
  private scene!: Scene;
  private fabric: V3 = [0, 0, 0];
  private k = 1;
  private view: View = { yaw: 0, crop: [0, 0, 1], knit: true };
  lastMs = 0;
  camera: Camera = CAMERA;
  setCamera(c: Camera) { this.camera = c; this.reset(); }
  /** photo mode: a different frame shape from the same camera position (so perspective, and the tee, never change) */
  optics: { aspect: number; tanHalf: number } | null = null;
  /** skin for fit mode bodies (linear) */
  skin: V3 = [0.32, 0.17, 0.1];
  /** knit loop tile repeats across the atlas: atlas size in cm over an 11.4 x 11.1 mm tile */
  knitRepeat: [number, number] = KNIT_REPEAT;
  /** fitted against the Cycles turntable frames (black and off white, three patches each) */
  sheenK = 0.06;

  static supported() { return typeof navigator !== "undefined" && "gpu" in navigator; }

  async init(canvas: HTMLCanvasElement) {
    const adapter = await navigator.gpu.requestAdapter({ powerPreference: "high-performance" });
    if (!adapter) throw new Error("no WebGPU adapter");
    this.device = await adapter.requestDevice({
      requiredLimits: {
        maxStorageBufferBindingSize: Math.min(adapter.limits.maxStorageBufferBindingSize, 512 * 1024 * 1024),
        maxBufferSize: Math.min(adapter.limits.maxBufferSize, 512 * 1024 * 1024),
      },
    });
    this.ctx = canvas.getContext("webgpu") as GPUCanvasContext;
    this.format = navigator.gpu.getPreferredCanvasFormat();
    this.ctx.configure({ device: this.device, format: this.format, alphaMode: "opaque" });
    const d = this.device;
    // compiled off the main thread: the big trace shader must never freeze the page
    const sm = d.createShaderModule({ code: SHOW_WGSL });
    [this.trace, this.show, this.dnPipe] = await Promise.all([
      d.createComputePipelineAsync({ layout: "auto", compute: { module: d.createShaderModule({ code: TRACE_WGSL }), entryPoint: "main" } }),
      d.createRenderPipelineAsync({ layout: "auto", vertex: { module: sm, entryPoint: "vs" }, fragment: { module: sm, entryPoint: "fs", targets: [{ format: this.format }] } }),
      d.createComputePipelineAsync({ layout: "auto", compute: { module: d.createShaderModule({ code: DENOISE_WGSL }), entryPoint: "main" } }),
    ]);
    this.dnU = [0, 1, 2, 3, 4].map(() => d.createBuffer({ size: 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST }));
    this.ubuf = d.createBuffer({ size: U_SIZE, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
    this.dims = d.createBuffer({ size: 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
    this.sampler = d.createSampler({ magFilter: "linear", minFilter: "linear", addressModeU: "repeat", addressModeV: "repeat" });
  }

  async setGeometry(g: TeeGeometry) {
    const bvh = await buildBVHAsync(g.pos, g.idx);
    const n = bvh.order.length;
    const tris = new Float32Array(n * 12), triv = new Uint32Array(n * 4);
    let t0 = performance.now();
    for (let i = 0; i < n; i++) {
      if ((i & 2047) === 0 && performance.now() - t0 > 2) { await new Promise((r) => setTimeout(r, 0)); t0 = performance.now(); }
      const t = bvh.order[i], a = g.idx[t * 3], b = g.idx[t * 3 + 1], c = g.idx[t * 3 + 2];
      const o = i * 12;
      for (let k = 0; k < 3; k++) {
        tris[o + k] = g.pos[a * 3 + k];
        tris[o + 4 + k] = g.pos[b * 3 + k] - g.pos[a * 3 + k];
        tris[o + 8 + k] = g.pos[c * 3 + k] - g.pos[a * 3 + k];
      }
      triv[i * 4] = a; triv[i * 4 + 1] = b; triv[i * 4 + 2] = c; triv[i * 4 + 3] = g.mat[t];
    }
    const nv = g.pos.length / 3, verts = new Float32Array(nv * 8);
    for (let v = 0; v < nv; v++) {
      verts[v * 8] = g.nrm[v * 3]; verts[v * 8 + 1] = g.nrm[v * 3 + 1]; verts[v * 8 + 2] = g.nrm[v * 3 + 2];
      verts[v * 8 + 3] = g.uv[v * 2]; verts[v * 8 + 4] = g.uv[v * 2 + 1];
      if (g.col) { verts[v * 8 + 5] = g.col[v * 3]; verts[v * 8 + 6] = g.col[v * 3 + 1]; verts[v * 8 + 7] = g.col[v * 3 + 2]; }
    }
    const up = (data: ArrayBufferView) => {
      const b = this.device.createBuffer({ size: Math.max(16, data.byteLength), usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST });
      this.device.queue.writeBuffer(b, 0, data.buffer, data.byteOffset, data.byteLength); return b;
    };
    this.geo = { nodes: up(new Float32Array(bvh.nodes)), tris: up(tris), triv: up(triv), verts: up(verts) };
    for (const t of this.skinTex) t.destroy();
    const img = (bmp: ImageBitmap | null, srgb: boolean, fill: number[]) => {
      const t = this.device.createTexture({
        size: bmp ? [bmp.width, bmp.height] : [1, 1], format: srgb ? "rgba8unorm-srgb" : "rgba8unorm",
        usage: GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST | GPUTextureUsage.RENDER_ATTACHMENT,
      });
      if (bmp) this.device.queue.copyExternalImageToTexture({ source: bmp }, { texture: t }, [bmp.width, bmp.height]);
      else this.device.queue.writeTexture({ texture: t }, new Uint8Array(fill), {}, [1, 1]);
      return t;
    };
    this.skinTex = [img(g.skin?.albedo ?? null, true, [255, 255, 255, 255]), img(g.skin?.rn ?? null, false, [128, 128, 128, 255])];
    this.traceBG = null;
    return { tris: n, nodes: bvh.nodeCount };
  }

  setImages(im: TeeImages) {
    const mk = (bmp: ImageBitmap, srgb: boolean) => {
      const t = this.device.createTexture({
        size: [bmp.width, bmp.height], format: srgb ? "rgba8unorm-srgb" : "rgba8unorm",
        usage: GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST | GPUTextureUsage.RENDER_ATTACHMENT,
      });
      this.device.queue.copyExternalImageToTexture({ source: bmp }, { texture: t }, [bmp.width, bmp.height]);
      return t;
    };
    for (const t of Object.values(this.tex)) t.destroy();
    this.tex = { back: mk(im.back, true), front: mk(im.front, true), normal: mk(im.normal, false), knit: mk(im.knit, false) };
    this.traceBG = null; this.reset();
  }

  /** the place all round (equirect, sRGB); null clears it */
  setEnv(bmp: ImageBitmap | null) {
    this.envTex?.destroy(); this.envTex = null;
    if (bmp) {
      const t = this.device.createTexture({ size: [bmp.width, bmp.height], format: "rgba8unorm-srgb", usage: GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST | GPUTextureUsage.RENDER_ATTACHMENT });
      this.device.queue.copyExternalImageToTexture({ source: bmp }, { texture: t }, [bmp.width, bmp.height]);
      this.envTex = t;
    }
    this.traceBG = null; this.reset();
  }
  private envView() {
    if (!this.envTex) {
      const t = this.device.createTexture({ size: [1, 1], format: "rgba8unorm-srgb", usage: GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST });
      this.device.queue.writeTexture({ texture: t }, new Uint8Array([0, 0, 0, 255]), {}, [1, 1]);
      this.envTex = t;
    }
    return this.envTex.createView();
  }

  /** only the colourway maps change between black and off white */
  setColourway(back: ImageBitmap, front: ImageBitmap) {
    this.setImages({ back, front, normal: this.imgNormal!, knit: this.imgKnit! });
  }
  imgNormal: ImageBitmap | null = null;
  imgKnit: ImageBitmap | null = null;

  setScene(scene: Scene, fabric: V3, cream: boolean) { this.scene = scene; this.fabric = fabric; this.k = cream ? scene.creamK : 1; this.reset(); }
  setView(v: View) { this.view = v; this.reset(); }
  reset() { this.frame = 0; this.clean = false; this.row = 0; }
  /** strip tracing: next row to trace, and the measured GPU cost of one row (ms, smoothed) */
  private row = 0;
  private msPerRow = 0;

  resize(w: number, h: number) {
    if (w === this.w && h === this.h) return;
    this.w = w; this.h = h;
    this.accum?.destroy(); this.gbuf?.destroy(); this.dn?.forEach((b) => b.destroy());
    const mk = (bytes: number) => this.device.createBuffer({ size: bytes, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC });
    this.accum = mk(w * h * 16); this.gbuf = mk(w * h * 32); this.dn = [mk(w * h * 16), mk(w * h * 16)];
    this.traceBG = null; this.showBG = null; this.dnBG = null; this.showDnBG = null; this.reset();
    this.device.queue.writeBuffer(this.dims, 0, new Uint32Array([w, h, 0, 0]));
  }

  private writeUniforms() {
    const f = new Float32Array(U_SIZE / 4), u = new Uint32Array(f.buffer);
    const cam = this.camera;
    const { f: F, r: R, u: Up } = cameraBasis(cam);
    const set = (o: number, v: V3, w: number) => { f[o] = v[0]; f[o + 1] = v[1]; f[o + 2] = v[2]; f[o + 3] = w; };
    set(0, cam.pos, (cam.lensMm / cam.fstop / 2) / 1000);
    set(4, R, this.optics?.tanHalf ?? Math.tan(VFOV / 2));
    set(8, Up, this.optics?.aspect ?? ASPECT);
    set(12, F, cam.focus);
    const [cx, cy, z] = this.view.crop; f[16] = cx; f[17] = cy; f[18] = z; f[19] = this.sheenK;
    const yr = (this.view.yaw * Math.PI) / 180; f[20] = Math.cos(yr); f[21] = Math.sin(yr); f[22] = this.row;
    f[23] = this.scene.envLight ?? 0;
    const s = this.scene;
    set(24, s.world, this.view.knit ? 0.55 : 0);
    set(28, s.paper, s.open ? 0 : 1);
    set(32, this.fabric, 1);
    set(36, this.skin, s.env && this.envTex && this.envTex.width > 1 ? 1 : 0);
    f[40] = this.knitRepeat[0]; f[41] = this.knitRepeat[1];
    const L = s.lights.slice(0, 6);
    u[44] = this.w; u[45] = this.h; u[46] = this.frame; u[47] = L.length;
    // light selection by emitted power, so the key gets most of the shadow rays
    const pw = L.map((l) => l.power * (l.tint[0] + l.tint[1] + l.tint[2])), tot = pw.reduce((a, b) => a + b, 0) || 1;
    let cdf = 0;
    // at a venue the lights stay with the place while the camera walks round: turned with the person
    const t = (v: V3) => (s.venue ? turnY(v, this.view.yaw) : v);
    L.forEach((l, i) => {
      const o = 48 + i * 20, fr = lightFrame(l, s.aim), rad = radiance(l, this.k), p = pw[i] / tot; cdf += p;
      set(o, t(l.pos), i === L.length - 1 ? 1 : cdf);
      set(o + 4, t(fr.ex), fr.area);
      set(o + 8, t(fr.ey), p);
      set(o + 12, rad, 0);
      set(o + 16, t(fr.n), 0);
    });
    this.device.queue.writeBuffer(this.ubuf, 0, f);
  }

  get ready() { return !!(this.geo && this.tex.back && this.accum && this.scene); }

  /**
   * Background work in strips: traces as many rows as fit in `budgetMs` of GPU time (learned as it goes), so
   * the page's own frames are never held up. Each pixel keeps its own sample count; a full sample completes when
   * the strips reach the bottom. Resolves when the GPU has finished the strip.
   */
  async work(budgetMs: number) {
    if (!this.ready) return;
    this.bind();
    const d = this.device;
    const rows = this.msPerRow > 0 ? Math.max(8, Math.min(this.h - this.row, Math.floor(budgetMs / this.msPerRow / 8) * 8)) : 16;
    this.writeUniforms();
    const enc = d.createCommandEncoder(), pass = enc.beginComputePass();
    pass.setPipeline(this.trace); pass.setBindGroup(0, this.traceBG);
    pass.dispatchWorkgroups(Math.ceil(this.w / 8), Math.ceil(rows / 8));
    pass.end(); d.queue.submit([enc.finish()]);
    const t0 = performance.now();
    await d.queue.onSubmittedWorkDone();
    const per = (performance.now() - t0) / rows;
    this.msPerRow = this.msPerRow ? this.msPerRow * 0.7 + per * 0.3 : per;
    this.lastMs = this.msPerRow * this.h;
    this.row += rows;
    if (this.row >= this.h) { this.row = 0; this.frame++; }
    this.clean = false;
  }

  private bind() {
    const d = this.device;
    if (!this.traceBG) {
      this.traceBG = d.createBindGroup({
        layout: this.trace.getBindGroupLayout(0),
        entries: [
          { binding: 0, resource: { buffer: this.ubuf } },
          { binding: 1, resource: { buffer: this.geo!.nodes } },
          { binding: 2, resource: { buffer: this.geo!.tris } },
          { binding: 3, resource: { buffer: this.geo!.triv } },
          { binding: 4, resource: { buffer: this.geo!.verts } },
          { binding: 5, resource: { buffer: this.accum! } },
          { binding: 6, resource: this.sampler },
          { binding: 7, resource: this.tex.back.createView() },
          { binding: 8, resource: this.tex.front.createView() },
          { binding: 9, resource: this.tex.normal.createView() },
          { binding: 10, resource: this.tex.knit.createView() },
          { binding: 11, resource: { buffer: this.gbuf! } },
          { binding: 12, resource: this.envView() },
          { binding: 13, resource: this.skinTex[0].createView() },
          { binding: 14, resource: this.skinTex[1].createView() },
        ],
      });
    }
    if (!this.showBG) {
      this.showBG = d.createBindGroup({ layout: this.show.getBindGroupLayout(0), entries: [{ binding: 0, resource: { buffer: this.accum! } }, { binding: 1, resource: { buffer: this.dims } }] });
    }
  }

  /** Trace `spp` whole samples per pixel and present (photos). Resolves when the GPU has finished. */
  async step(spp = 1, present = true) {
    if (!this.ready) return;
    const d = this.device;
    this.bind(); this.row = 0;
    const t0 = performance.now();
    for (let i = 0; i < spp; i++) {
      this.writeUniforms();
      const enc = d.createCommandEncoder();
      const pass = enc.beginComputePass();
      pass.setPipeline(this.trace); pass.setBindGroup(0, this.traceBG);
      pass.dispatchWorkgroups(Math.ceil(this.w / 8), Math.ceil(this.h / 8));
      pass.end();
      d.queue.submit([enc.finish()]);
      this.frame++;
    }
    this.clean = false;
    if (present) this.present(false);
    await d.queue.onSubmittedWorkDone();
    this.lastMs = (performance.now() - t0) / spp;
  }

  /** Smooth away the sampling noise of the samples so far (five a-trous passes, a few ms). */
  async denoise(present = true) {
    if (!this.ready || this.frame === 0) return;
    const d = this.device, [A, B] = this.dn!;
    if (!this.dnBG) {
      // pass i reads src, writes dst: 0 accum->A, 1 A->B, 2 B->A, 3 A->B, 4 B->A (last, remodulated, ends in A)
      const io: [GPUBuffer, GPUBuffer][] = [[A, A], [A, B], [B, A], [A, B], [B, A]];
      this.dnBG = io.map(([src, dst], i) => d.createBindGroup({
        layout: this.dnPipe.getBindGroupLayout(0),
        entries: [
          { binding: 0, resource: { buffer: this.dnU[i] } },
          { binding: 1, resource: { buffer: this.accum! } },
          { binding: 2, resource: { buffer: this.gbuf! } },
          { binding: 3, resource: { buffer: i === 0 ? this.accum! : src } },
          { binding: 4, resource: { buffer: dst } },
        ],
      }));
      this.dnU.forEach((b, i) => d.queue.writeBuffer(b, 0, new Uint32Array([this.w, this.h, 1 << i, i === 0 ? 0 : i === 4 ? 2 : 1])));
    }
    const enc = d.createCommandEncoder();
    for (const bg of this.dnBG) {
      const pass = enc.beginComputePass();
      pass.setPipeline(this.dnPipe); pass.setBindGroup(0, bg);
      pass.dispatchWorkgroups(Math.ceil(this.w / 8), Math.ceil(this.h / 8)); pass.end();
    }
    d.queue.submit([enc.finish()]);
    this.clean = true;
    if (present) this.present(true);
    await d.queue.onSubmittedWorkDone();
  }

  private present(clean: boolean) {
    const d = this.device;
    if (clean && !this.showDnBG) {
      this.showDnBG = d.createBindGroup({ layout: this.show.getBindGroupLayout(0), entries: [{ binding: 0, resource: { buffer: this.dn![0] } }, { binding: 1, resource: { buffer: this.dims } }] });
    }
    const enc = d.createCommandEncoder();
    const rp = enc.beginRenderPass({ colorAttachments: [{ view: this.ctx.getCurrentTexture().createView(), loadOp: "clear", storeOp: "store", clearValue: [0, 0, 0, 1] }] });
    rp.setPipeline(this.show); rp.setBindGroup(0, clean ? this.showDnBG! : this.showBG!); rp.draw(3); rp.end();
    d.queue.submit([enc.finish()]);
  }
}

/** Khronos PBR Neutral, the same curve as the display shader */
function neutral(c: number[]) {
  const x = Math.min(c[0], c[1], c[2]), off = x < 0.08 ? x - 6.25 * x * x : 0.04;
  let r = c[0] - off, g = c[1] - off, b = c[2] - off;
  const peak = Math.max(r, g, b), st = 0.76;
  if (peak < st) return [r, g, b];
  const dd = 1 - st, np = 1 - (dd * dd) / (peak + dd - st);
  r = (r * np) / peak; g = (g * np) / peak; b = (b * np) / peak;
  const k = 1 - 1 / (0.15 * (peak - np) + 1);
  return [r + (np - r) * k, g + (np - g) * k, b + (np - b) * k];
}
function srgb8(v: number) {
  v = Math.min(1, Math.max(0, v));
  return Math.round(255 * (v <= 0.0031308 ? v * 12.92 : 1.055 * Math.pow(v, 1 / 2.4) - 0.055));
}
