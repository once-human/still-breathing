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
onmessage = async (e) => {
  const { id, blob, w, h, raw } = e.data, base = { colorSpaceConversion: "none", premultiplyAlpha: "none" };
  if (raw) {
    try { const r = await rgba(blob); postMessage({ id, ...r }, [r.data.buffer]); } catch (err) { postMessage({ id, error: String(err) }); }
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
 * Any picture (alpha included, exactly as stored) as raw RGBA bytes, decoded in the Worker; null where the browser
 * can't (no WebCodecs image decoder): the caller then takes the ordinary image path.
 */
export async function rawImage(url: string): Promise<{ data: Uint8Array; width: number; height: number } | null> {
  if (typeof ImageDecoder === "undefined") return null;
  const blob = await grab(url);
  return (decode(blob, { raw: true }) as Promise<{ data: Uint8Array; width: number; height: number }>).catch(() => null);
}
function decode(blob: Blob, opt: { w?: number; h?: number; raw?: boolean }): Promise<unknown> {
  if (!decoder) {
    decoder = new Worker(URL.createObjectURL(new Blob([DECODE], { type: "text/javascript" })));
    decoder.onmessage = (e) => {
      const w = waiting.get(e.data.id); if (!w) return; waiting.delete(e.data.id);
      if (e.data.error) w.no(new Error(e.data.error)); else w.ok(e.data as Pixels);
    };
  }
  const id = ++nextId;
  return new Promise((ok, no) => { waiting.set(id, { ok: ok as (p: Pixels) => void, no }); decoder!.postMessage({ id, blob, ...opt }); });
}
