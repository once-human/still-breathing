// Photo mode: the exact view on screen, path traced at story or post size, developed and signed.
import type { PathTracer } from "./pathtracer";
import { ASPECT, VFOV } from "./scene";

export const FORMATS = {
  story: { label: "story 9:16", w: 1080, h: 1920 },
  post: { label: "post 4:5", w: 1080, h: 1350 },
} as const;
export type Format = keyof typeof FORMATS;
export type Look = "clean" | "film";
export type Caption = { title: string; line: string; foot: string };

export type PhotoJob = {
  format: Format;
  look: Look;
  spp: number;
  caption: Caption;
  onProgress?: (done: number, total: number) => void;
  signal?: AbortSignal;
};

/**
 * Renders on the viewer's own tracer. The camera does not move: a taller frame only shows more floor and wall,
 * because the lens is widened from the same spot (perspective depends on position, never on the crop).
 */
export async function renderPhoto(pt: PathTracer, job: PhotoJob): Promise<Blob> {
  const f = FORMATS[job.format], aspect = f.w / f.h;
  const tan0 = Math.tan(VFOV / 2);
  // keep the tee's width in frame: a narrower frame gets a taller view, a wider one keeps the height
  const tanHalf = aspect < ASPECT ? (tan0 * ASPECT) / aspect : tan0;
  pt.optics = { aspect, tanHalf };
  pt.resize(f.w, f.h);
  pt.reset();
  try {
    let lastYield = performance.now();
    while (pt.frame < job.spp) {
      if (job.signal?.aborted) throw new DOMException("stopped", "AbortError");
      const n = pt.lastMs > 0 ? Math.max(1, Math.min(8, Math.floor(120 / pt.lastMs), job.spp - pt.frame)) : 1;
      await pt.step(n, false);
      job.onProgress?.(pt.frame, job.spp);
      // let the page breathe between batches
      if (performance.now() - lastYield > 200) { await new Promise((r) => setTimeout(r, 0)); lastYield = performance.now(); }
    }
    await pt.denoise(false);
    const img = await pt.toImageData();
    return await develop(img, job.look, job.caption);
  } finally {
    pt.optics = null;
  }
}

/** The darkroom step: film grain and fall-off if asked, then the caption in the house type. */
async function develop(img: ImageData, look: Look, cap: Caption): Promise<Blob> {
  const { width: W, height: H } = img;
  if (look === "film") film(img);
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = H;
  const g = cv.getContext("2d")!;
  g.putImageData(img, 0, 0);

  const face = getComputedStyle(document.body).fontFamily || "sans-serif";
  try { await document.fonts.load(`800 64px ${face}`); } catch { /* the fallback face is fine */ }
  const pad = Math.round(W * 0.06);
  const inkOn = (y0: number, y1: number) => (luma(img, y0, y1) > 0.55 ? "rgba(13,13,12,0.92)" : "rgba(239,236,228,0.95)");
  const quietOn = (y0: number, y1: number) => (luma(img, y0, y1) > 0.55 ? "rgba(13,13,12,0.6)" : "rgba(239,236,228,0.62)");

  // top: the brand, small
  g.textBaseline = "top";
  g.fillStyle = inkOn(0, pad * 2);
  g.font = `800 ${Math.round(W * 0.04)}px ${face}`;
  g.fillText("sahn", pad, pad);
  g.font = `500 ${Math.round(W * 0.028)}px ${face}`;
  g.fillStyle = quietOn(0, pad * 2);
  const lu = "lineup 01";
  g.fillText(lu, W - pad - g.measureText(lu).width, pad + Math.round(W * 0.008));

  // bottom: what it is
  const big = Math.round(W * 0.075), mid = Math.round(W * 0.03);
  const yFoot = H - pad, yLine = yFoot - mid * 1.45, yTitle = yLine - mid * 1.75;
  const band0 = Math.round(yTitle - big * 1.1);
  g.textBaseline = "alphabetic";
  g.fillStyle = inkOn(band0, H);
  g.font = `800 ${big}px ${face}`;
  g.fillText(cap.title, pad, yTitle);
  g.font = `500 ${mid}px ${face}`;
  g.fillText(cap.line, pad, yLine);
  g.fillStyle = quietOn(band0, H);
  g.fillText(cap.foot, pad, yFoot);

  return await new Promise<Blob>((res, rej) => cv.toBlob((b) => (b ? res(b) : rej(new Error("could not encode"))), "image/jpeg", 0.93));
}

/** Mean luminance (0..1) of a horizontal band, so the caption picks ink or paper. */
function luma(img: ImageData, y0: number, y1: number) {
  const { width: W, data: d } = img;
  let s = 0, n = 0;
  for (let y = Math.max(0, y0 | 0); y < Math.min(img.height, y1); y += 4)
    for (let x = 0; x < W; x += 4) { const i = (y * W + x) * 4; s += 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2]; n++; }
  return n ? s / n / 255 : 0;
}

/** A gentle 400-speed look: soft toe, warm shadows, luminance grain strongest in the mids, a little fall-off. */
function film(img: ImageData) {
  const { width: W, height: H, data: d } = img;
  let seed = 0x9e3779b9;
  const rnd = () => { seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5; return (seed >>> 0) / 4294967296; };
  const gauss = () => { const u = rnd() || 1e-7, v = rnd(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
  const cx = W / 2, cy = H * 0.46, rr = Math.hypot(cx, H * 0.54);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = (y * W + x) * 4;
    const r = d[i] / 255, gr = d[i + 1] / 255, b = d[i + 2] / 255;
    const L = 0.2126 * r + 0.7152 * gr + 0.0722 * b;
    const v = 1 - 0.2 * Math.pow(Math.hypot(x - cx, y - cy) / rr, 2.2);
    const n = gauss() * (0.018 + 0.03 * (1 - Math.abs(2 * L - 1)));
    const lift = 0.035 * (1 - L);
    d[i] = 255 * clamp01((r * 0.96 + lift * 1.15) * v + n);
    d[i + 1] = 255 * clamp01((gr * 0.96 + lift) * v + n);
    d[i + 2] = 255 * clamp01((b * 0.95 + lift * 0.8) * v + n);
  }
}
const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);
