// Host side of the WebGPU path tracer: uploads the tee (BVH, triangles, textures), then traces one
// sample per pixel per frame into a float buffer and shows the running average.
import { TRACE_WGSL, SHOW_WGSL } from "./pt.wgsl";
import { buildBVHAsync } from "./bvh";
import { CAMERA, VFOV, ASPECT, cameraBasis, lightFrame, radiance, type Scene, type V3 } from "./scene";

export type TeeGeometry = { pos: Float32Array; nrm: Float32Array; uv: Float32Array; idx: Uint32Array; mat: Uint8Array };
export type TeeImages = { color: ImageBitmap; orm: ImageBitmap; normal: ImageBitmap; knit: ImageBitmap };
export type View = { yaw: number; crop: [number, number, number]; knit: boolean };

const U_SIZE = 256 + 4 * 80;

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
  /** debug: mean displayed sRGB (0-255) of a box given in 0..1 frame coordinates, after the same view transform */
  async probe(x0: number, y0: number, x1: number, y1: number) {
    const d = this.device, size = this.w * this.h * 16;
    const rb = d.createBuffer({ size, usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST });
    const enc = d.createCommandEncoder(); enc.copyBufferToBuffer(this.accum!, 0, rb, 0, size); d.queue.submit([enc.finish()]);
    await rb.mapAsync(GPUMapMode.READ);
    const a = new Float32Array(rb.getMappedRange().slice(0)); rb.unmap(); rb.destroy();
    const neutral = (c: number[]) => {
      const x = Math.min(...c), off = x < 0.08 ? x - 6.25 * x * x : 0.04; c = c.map((v) => v - off);
      const peak = Math.max(...c), st = 0.76; if (peak < st) return c;
      const dd = 1 - st, np = 1 - (dd * dd) / (peak + dd - st); c = c.map((v) => (v * np) / peak);
      const g = 1 - 1 / (0.15 * (peak - np) + 1); return c.map((v) => v + (np - v) * g);
    };
    const srgb = (v: number) => 255 * (v <= 0.0031308 ? v * 12.92 : 1.055 * Math.pow(v, 1 / 2.4) - 0.055);
    const out = [0, 0, 0], lin = [0, 0, 0]; let n = 0;
    for (let y = Math.floor(y0 * this.h); y < y1 * this.h; y++) for (let x = Math.floor(x0 * this.w); x < x1 * this.w; x++) {
      const i = (y * this.w + x) * 4, w = a[i + 3] || 1, c = [a[i] / w, a[i + 1] / w, a[i + 2] / w];
      const m = neutral(c).map((v) => srgb(Math.min(1, Math.max(0, v))));
      for (let k = 0; k < 3; k++) { out[k] += m[k]; lin[k] += c[k]; } n++;
    }
    return { srgb: out.map((v) => Math.round(v / n)), linear: lin.map((v) => +(v / n).toFixed(4)), spp: this.frame };
  }
  private geo: { nodes: GPUBuffer; tris: GPUBuffer; triv: GPUBuffer; verts: GPUBuffer } | null = null;
  private tex: Record<string, GPUTexture> = {};
  private sampler!: GPUSampler;
  private traceBG: GPUBindGroup | null = null;
  private showBG: GPUBindGroup | null = null;
  private scene!: Scene;
  private fabric: V3 = [0, 0, 0];
  private k = 1;
  private view: View = { yaw: 0, crop: [0, 0, 1], knit: true };
  lastMs = 0;
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
    this.trace = d.createComputePipeline({ layout: "auto", compute: { module: d.createShaderModule({ code: TRACE_WGSL }), entryPoint: "main" } });
    const sm = d.createShaderModule({ code: SHOW_WGSL });
    this.show = d.createRenderPipeline({ layout: "auto", vertex: { module: sm, entryPoint: "vs" }, fragment: { module: sm, entryPoint: "fs", targets: [{ format: this.format }] } });
    this.ubuf = d.createBuffer({ size: U_SIZE, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
    this.dims = d.createBuffer({ size: 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
    this.sampler = d.createSampler({ magFilter: "linear", minFilter: "linear", addressModeU: "repeat", addressModeV: "repeat" });
  }

  async setGeometry(g: TeeGeometry) {
    const bvh = await buildBVHAsync(g.pos, g.idx);
    const n = bvh.order.length;
    const tris = new Float32Array(n * 12), triv = new Uint32Array(n * 4);
    for (let i = 0; i < n; i++) {
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
    }
    const up = (data: ArrayBufferView) => {
      const b = this.device.createBuffer({ size: Math.max(16, data.byteLength), usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST });
      this.device.queue.writeBuffer(b, 0, data.buffer, data.byteOffset, data.byteLength); return b;
    };
    this.geo = { nodes: up(new Float32Array(bvh.nodes)), tris: up(tris), triv: up(triv), verts: up(verts) };
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
    this.tex = { color: mk(im.color, true), orm: mk(im.orm, false), normal: mk(im.normal, false), knit: mk(im.knit, false) };
    this.traceBG = null; this.reset();
  }

  /** only the colourway maps change between black and off white */
  setColourway(color: ImageBitmap, orm: ImageBitmap) {
    this.setImages({ color, orm, normal: this.imgNormal!, knit: this.imgKnit! });
  }
  imgNormal: ImageBitmap | null = null;
  imgKnit: ImageBitmap | null = null;

  setScene(scene: Scene, fabric: V3, cream: boolean) { this.scene = scene; this.fabric = fabric; this.k = cream ? scene.creamK : 1; this.reset(); }
  setView(v: View) { this.view = v; this.reset(); }
  reset() { this.frame = 0; }

  resize(w: number, h: number) {
    if (w === this.w && h === this.h) return;
    this.w = w; this.h = h;
    this.accum?.destroy();
    this.accum = this.device.createBuffer({ size: w * h * 16, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC });
    this.traceBG = null; this.showBG = null; this.reset();
    this.device.queue.writeBuffer(this.dims, 0, new Uint32Array([w, h, 0, 0]));
  }

  private writeUniforms() {
    const f = new Float32Array(U_SIZE / 4), u = new Uint32Array(f.buffer);
    const { f: F, r: R, u: Up } = cameraBasis();
    const set = (o: number, v: V3, w: number) => { f[o] = v[0]; f[o + 1] = v[1]; f[o + 2] = v[2]; f[o + 3] = w; };
    set(0, CAMERA.pos, (CAMERA.lensMm / CAMERA.fstop / 2) / 1000);
    set(4, R, Math.tan(VFOV / 2));
    set(8, Up, ASPECT);
    set(12, F, CAMERA.focus);
    const [cx, cy, z] = this.view.crop; f[16] = cx; f[17] = cy; f[18] = z; f[19] = this.sheenK;
    const yr = (this.view.yaw * Math.PI) / 180; f[20] = Math.cos(yr); f[21] = Math.sin(yr);
    const s = this.scene;
    set(24, s.world, this.view.knit ? 0.55 : 0);
    set(28, s.paper, 1);
    set(32, this.fabric, 1);
    const L = s.lights.slice(0, 4);
    u[36] = this.w; u[37] = this.h; u[38] = this.frame; u[39] = L.length;
    // light selection by emitted power, so the key gets most of the shadow rays
    const pw = L.map((l) => l.power * (l.tint[0] + l.tint[1] + l.tint[2])), tot = pw.reduce((a, b) => a + b, 0) || 1;
    let cdf = 0;
    L.forEach((l, i) => {
      const o = 40 + i * 20, fr = lightFrame(l), rad = radiance(l, this.k), p = pw[i] / tot; cdf += p;
      set(o, l.pos, i === L.length - 1 ? 1 : cdf);
      set(o + 4, fr.ex, fr.area);
      set(o + 8, fr.ey, p);
      set(o + 12, rad, 0);
      set(o + 16, fr.n, 0);
    });
    this.device.queue.writeBuffer(this.ubuf, 0, f);
  }

  get ready() { return !!(this.geo && this.tex.color && this.accum && this.scene); }

  /** Trace `spp` samples per pixel and present. Resolves when the GPU has finished. */
  async step(spp = 1) {
    if (!this.ready) return;
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
          { binding: 7, resource: this.tex.color.createView() },
          { binding: 8, resource: this.tex.orm.createView() },
          { binding: 9, resource: this.tex.normal.createView() },
          { binding: 10, resource: this.tex.knit.createView() },
        ],
      });
    }
    if (!this.showBG) {
      this.showBG = d.createBindGroup({ layout: this.show.getBindGroupLayout(0), entries: [{ binding: 0, resource: { buffer: this.accum! } }, { binding: 1, resource: { buffer: this.dims } }] });
    }
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
    const enc = d.createCommandEncoder();
    const rp = enc.beginRenderPass({ colorAttachments: [{ view: this.ctx.getCurrentTexture().createView(), loadOp: "clear", storeOp: "store", clearValue: [0, 0, 0, 1] }] });
    rp.setPipeline(this.show); rp.setBindGroup(0, this.showBG); rp.draw(3); rp.end();
    d.queue.submit([enc.finish()]);
    await d.queue.onSubmittedWorkDone();
    this.lastMs = (performance.now() - t0) / spp;
  }
}
