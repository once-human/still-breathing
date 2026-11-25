// One download per file, shared: the viewer starts fetching its tee, textures and decoder the moment it
// knows it will run, while the 3D code itself is still on its way. Whoever asks later gets the same bytes.
import { asset } from "@/lib/asset";

const cache = new Map<string, Promise<Blob>>();

export function grab(url: string): Promise<Blob> {
  let p = cache.get(url);
  if (!p) {
    p = fetch(asset(url), { priority: "high" } as RequestInit).then((r) => {
      if (!r.ok) throw new Error(`${url}: ${r.status}`);
      return r.blob();
    });
    p.catch(() => cache.delete(url));
    cache.set(url, p);
  }
  return p;
}

/** an image as an ImageBitmap, bytes exactly as stored (no colour conversion, no premultiply) */
export async function bitmap(url: string) {
  return createImageBitmap(await grab(url), { colorSpaceConversion: "none", premultiplyAlpha: "none" });
}

/** everything the first tee needs, started now */
export function prefetchTee(v: { dir: string; size: string; pose: string; body: boolean; person?: string }, design: string, tee: string) {
  const A = "/tee/fit/";
  const urls = [
    `${A}${v.dir}/${v.pose}.glb`, `${A}tex/print-back-${design}-${tee}.webp`, `${A}tex/print-front-${tee}.webp`,
    `${A}tex/normal-${v.size}.png`, `${A}tex/knit-normal.png`, "/draco/draco_wasm_wrapper.js", "/draco/draco_decoder.wasm",
  ];
  if (v.person) urls.push(v.person, v.person.replace(/\.glb$/, "-skin.webp"), v.person.replace(/\.glb$/, "-skin-n.webp"));
  else if (v.body) urls.push(`${A}${v.dir}/body-${v.pose}.glb`);
  for (const u of urls) grab(u).catch(() => {});
}

/** an opaque picture as raw RGBA bytes, and its 64 x 32 linear version for a light probe */
export type Pixels = { data: Uint8Array; width: number; height: number; texels: Float32Array };

// Decoded, shrunk and read back in a Worker, on a canvas that lives in plain memory: the page's own thread never
// touches the pixels, and never waits on the graphics process to read a picture back. Opaque pictures only (a
// canvas keeps colour premultiplied by alpha, which would lose detail where a picture is see-through).
const DECODE = `
const read = (b) => { const c = new OffscreenCanvas(b.width, b.height).getContext("2d", { willReadFrequently: true }); c.drawImage(b, 0, 0); b.close(); return c.getImageData(0, 0, c.canvas.width, c.canvas.height).data; };
// any picture, alpha and all, as the file stores it (WebCodecs: no canvas, so no premultiplying on the way)
const rgba = async (blob) => {
  const dec = new ImageDecoder({ data: blob.stream(), type: blob.type || "image/webp", colorSpaceConversion: "none", premultiplyAlpha: "none" });
  try {
    const { image } = await dec.decode();
    const width = image.displayWidth, height = image.displayHeight, data = new Uint8Array(width * height * 4);
    await image.copyTo(data, { format: "RGBA", rect: { x: 0, y: 0, width, height }, layout: [{ offset: 0, stride: width * 4 }] });
    image.close();
    return { width, height, data };
  } finally { dec.close(); }
};
// The mip chain, each level a box filter of the one above at WebGPU's sizes (half, rounded down). sRGB pictures are
// averaged as light (decoded, averaged, encoded: what the GPU's own mip pass does with an sRGB texture); the rest,
// and alpha, as stored. Where a size is odd a texel covers a texel and a half, weighted by how much of it it covers.
const S2L = new Float32Array(256), L2S = new Uint8Array(65537);
for (let i = 0; i < 256; i++) { const v = i / 255; S2L[i] = v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
for (let i = 0; i <= 65536; i++) { const v = i / 65536; L2S[i] = Math.round(255 * (v <= 0.0031308 ? v * 12.92 : 1.055 * Math.pow(v, 1 / 2.4) - 0.055)); }
const taps = (n, m) => {
  const k = n / m, K = Math.ceil(k) + (k % 1 ? 1 : 0), at = new Int32Array(m * K), w = new Float32Array(m * K);
  for (let i = 0; i < m; i++) {
    const lo = i * k, hi = lo + k;
    for (let j = Math.floor(lo), t = 0; j < hi && t < K; j++, t++) { at[i * K + t] = Math.min(j, n - 1); w[i * K + t] = (Math.min(hi, j + 1) - Math.max(lo, j)) / k; }
  }
  return { K, at, w };
};
const half = (src, sw, sh, srgb) => {
  const dw = Math.max(1, sw >> 1), dh = Math.max(1, sh >> 1), dst = new Uint8Array(dw * dh * 4);
  const X = taps(sw, dw), Y = taps(sh, dh);
  for (let y = 0; y < dh; y++) for (let x = 0; x < dw; x++) {
    let r = 0, g = 0, b = 0, a = 0;
    for (let ty = 0; ty < Y.K; ty++) {
      const wy = Y.w[y * Y.K + ty]; if (!wy) continue;
      const row = Y.at[y * Y.K + ty] * sw;
      for (let tx = 0; tx < X.K; tx++) {
        const wx = X.w[x * X.K + tx]; if (!wx) continue;
        const ww = wx * wy, o = (row + X.at[x * X.K + tx]) * 4;
        if (srgb) { r += S2L[src[o]] * ww; g += S2L[src[o + 1]] * ww; b += S2L[src[o + 2]] * ww; }
        else { r += src[o] * ww; g += src[o + 1] * ww; b += src[o + 2] * ww; }
        a += src[o + 3] * ww;
      }
    }
    const o = (y * dw + x) * 4;
    if (srgb) { dst[o] = L2S[Math.round(Math.min(1, r) * 65536)]; dst[o + 1] = L2S[Math.round(Math.min(1, g) * 65536)]; dst[o + 2] = L2S[Math.round(Math.min(1, b) * 65536)]; }
    else { dst[o] = Math.round(r); dst[o + 1] = Math.round(g); dst[o + 2] = Math.round(b); }
    dst[o + 3] = Math.round(a);
  }
  return { width: dw, height: dh, data: dst };
};
onmessage = async (e) => {
  const { id, blob, w, h, raw, mips, snap } = e.data, base = { colorSpaceConversion: "none", premultiplyAlpha: "none" };
  if (snap) {
    // a frame of the view, shrunk to its thumbnail and encoded here (reading it back would hold the page)
    try {
      const c = new OffscreenCanvas(w, h), g = c.getContext("2d");
      g.drawImage(snap, 0, 0, w, h); snap.close();
      postMessage({ id, blob: await c.convertToBlob({ type: "image/webp", quality: 0.82 }) });
    } catch (err) { postMessage({ id, error: String(err) }); }
    return;
  }
  if (raw) {
    try {
      const r = await rgba(blob), levels = [r];
      // mips: 0 none, 1 as stored, 2 sRGB
      if (mips) for (let l = r; l.width > 1 || l.height > 1;) { l = half(l.data, l.width, l.height, mips === 2); levels.push(l); }
      postMessage({ id, ...r, levels }, levels.map((l) => l.data.buffer));
    } catch (err) { postMessage({ id, error: String(err) }); }
    return;
  }
  try {
    const [big, small] = await Promise.all([
      createImageBitmap(blob, w ? { ...base, resizeWidth: w, resizeHeight: h, resizeQuality: "high" } : base),
      createImageBitmap(blob, { ...base, resizeWidth: 64, resizeHeight: 32, resizeQuality: "high" }),
    ]);
    const width = big.width, height = big.height, data = new Uint8Array(read(big).buffer), px = read(small);
    const texels = new Float32Array(64 * 32 * 3);
    for (let i = 0; i < 64 * 32; i++) for (let c = 0; c < 3; c++) {
      const v = px[i * 4 + c] / 255;
      texels[i * 3 + c] = v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    }
    postMessage({ id, data, width, height, texels }, [data.buffer, texels.buffer]);
  } catch (err) { postMessage({ id, error: String(err) }); }
};`;
let decoder: Worker | null = null, nextId = 0;
const waiting = new Map<number, { ok: (p: Pixels) => void; no: (e: Error) => void }>();
export async function pixels(url: string, size?: [number, number]): Promise<Pixels> {
  return decode(await grab(url), { w: size?.[0], h: size?.[1] }) as Promise<Pixels>;
}
/**
 * Any picture (alpha included, exactly as stored) as raw RGBA bytes, decoded in the Worker, with its mip chain made
 * there too if asked; null where the browser can't (no WebCodecs image decoder): the caller then takes the ordinary
 * image path.
 */
export type Level = { data: Uint8Array; width: number; height: number };
export async function rawImage(url: string, mips: "none" | "plain" | "srgb" = "none"): Promise<Level & { levels: Level[] } | null> {
  if (typeof ImageDecoder === "undefined") return null;
  const blob = await grab(url);
  return (decode(blob, { raw: true, mips: mips === "srgb" ? 2 : mips === "plain" ? 1 : 0 }) as Promise<Level & { levels: Level[] }>).catch(() => null);
}
/** a frame (taken with createImageBitmap) as a w x h webp, encoded in the Worker */
export async function thumbnail(frame: ImageBitmap, w: number, h: number): Promise<Blob> {
  return ((await post({ snap: frame, w, h }, [frame])) as { blob: Blob }).blob;
}
function decode(blob: Blob, opt: { w?: number; h?: number; raw?: boolean; mips?: number }): Promise<unknown> {
  return post({ blob, ...opt });
}
function post(msg: Record<string, unknown>, transfer: Transferable[] = []): Promise<unknown> {
  if (!decoder) {
    decoder = new Worker(URL.createObjectURL(new Blob([DECODE], { type: "text/javascript" })));
    decoder.onmessage = (e) => {
      const w = waiting.get(e.data.id); if (!w) return; waiting.delete(e.data.id);
      if (e.data.error) w.no(new Error(e.data.error)); else w.ok(e.data as Pixels);
    };
  }
  const id = ++nextId;
  return new Promise((ok, no) => { waiting.set(id, { ok: ok as (p: Pixels) => void, no }); decoder!.postMessage({ id, ...msg }, transfer); });
}
