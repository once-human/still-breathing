// One download per file, shared: the viewer starts fetching its tee, textures and decoder the moment it
// knows it will run, while the 3D code itself is still on its way. Whoever asks later gets the same bytes.
const cache = new Map<string, Promise<Blob>>();

export function grab(url: string): Promise<Blob> {
  let p = cache.get(url);
  if (!p) {
    p = fetch(url, { priority: "high" } as RequestInit).then((r) => {
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
export function prefetchTee(v: { dir: string; size: string; pose: string; body: boolean }, design: string, tee: string) {
  const A = "/tee/fit/";
  const urls = [
    `${A}${v.dir}/${v.pose}.glb`, `${A}tex/print-back-${design}-${tee}.webp`, `${A}tex/print-front-${tee}.webp`,
    `${A}tex/normal-${v.size}.png`, `${A}tex/knit-normal.png`, "/draco/draco_wasm_wrapper.js", "/draco/draco_decoder.wasm",
  ];
  if (v.body) urls.push(`${A}${v.dir}/body-${v.pose}.glb`);
  for (const u of urls) grab(u).catch(() => {});
}
