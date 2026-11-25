// Pictures as textures, every texel exactly as the file stores it, without ever holding the page: decoded in a
// Worker (grab.ts) into raw bytes, with the mip chain made there too (box-filtered as light), then written to the
// graphics card a slice at a time between frames. An image upload, or one big buffer copy, can hold the page for
// seconds while the graphics process is busy. The texture is handed back only once every level is in, so what's
// drawn is never part-written. Where the renderer isn't WebGPU it's a plain data texture (the GPU makes its mips),
// and the ordinary image path where the browser can't decode to bytes. Same filters every way, so swapping one
// picture for another never changes a shader.
import * as THREE from "three/webgpu";
import { bitmap, rawImage, type Level } from "./grab";

/** a moment for the page between slices (a message, which a hidden tab doesn't hold back like a timer) */
const breathe = () => new Promise<void>((r) => { const c = new MessageChannel(); c.port1.onmessage = () => { c.port1.close(); r(); }; c.port2.postMessage(0); });
/** bytes written to the graphics card per slice: a few milliseconds of the page's time each */
const SLICE = 1 << 20;

export function gpuDevice(r: THREE.WebGPURenderer): GPUDevice | null {
  const b = r.backend as unknown as { isWebGPUBackend?: boolean; device?: GPUDevice };
  return b.isWebGPUBackend ? b.device ?? null : null;
}

/** levels (largest first) into a texture of the card's own, smallest first, SLICE bytes per task */
export async function streamTexture(dev: GPUDevice, levels: Level[], srgb: boolean) {
  const g = dev.createTexture({
    size: [levels[0].width, levels[0].height], mipLevelCount: levels.length,
    format: srgb ? "rgba8unorm-srgb" : "rgba8unorm", usage: GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST,
  });
  let sent = 0;
  try {
    for (let m = levels.length - 1; m >= 0; m--) {
      const { data, width, height } = levels[m], row = width * 4, rows = Math.max(1, Math.floor(SLICE / row));
      for (let y = 0; y < height; y += rows) {
        const h = Math.min(rows, height - y);
        dev.queue.writeTexture({ texture: g, mipLevel: m, origin: [0, y] }, data as Uint8Array<ArrayBuffer>, { offset: y * row, bytesPerRow: row, rowsPerImage: h }, [width, h]);
        // the next slice only once the card has taken this one in: a write while it's still busy waits on the
        // page's thread (seconds, behind a big picture)
        if ((sent += h * row) >= SLICE) { sent = 0; await dev.queue.onSubmittedWorkDone(); await breathe(); }
      }
    }
  } catch (e) { g.destroy(); throw e; }
  const t = new THREE.ExternalTexture(g);
  // three never frees a texture it didn't make: this one goes when the texture is disposed
  t.addEventListener("dispose", () => g.destroy());
  return t;
}

/**
 * A picture as a texture, ready to set its wrap, repeat and anisotropy on (before anything draws with it: a
 * texture of the card's own is never uploaded again).
 */
export async function picture(url: string, renderer: THREE.WebGPURenderer, srgb: boolean, mips = true) {
  const dev = gpuDevice(renderer);
  const raw = await rawImage(url, dev && mips ? (srgb ? "srgb" : "plain") : "none");
  let t: THREE.Texture;
  if (!raw) t = new THREE.Texture(await bitmap(url));
  else if (dev) t = await streamTexture(dev, mips ? raw.levels : [raw.levels[0]], srgb);
  else t = new THREE.DataTexture(raw.data, raw.width, raw.height, THREE.RGBAFormat, THREE.UnsignedByteType);
  t.flipY = false; t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.magFilter = THREE.LinearFilter; t.minFilter = mips ? THREE.LinearMipmapLinearFilter : THREE.LinearFilter;
  t.generateMipmaps = mips && !(t as THREE.ExternalTexture).isExternalTexture;
  t.needsUpdate = true;
  return t;
}
