// How much of the viewer this device gets. Everyone who can render gets the same live tee: the cloth in the air,
// the person, the place, every view of the carousel. What changes is only what it costs:
//   full    WebGPU on a real graphics card, a desktop or laptop: live view at full sharpness, and the path tracer
//           refining the exact frame whenever it comes to rest
//   lite    WebGL2 on a real graphics card, or a phone, or a machine with 4 GB or less: the same live view at a gentler
//           resolution, no path tracer (it needs WebGPU, and on a phone it would only drain the battery)
//   photos  no usable graphics (a software renderer), Data Saver, or very little memory: the rendered frames,
//           all preloaded, and the 3D code is never downloaded
export type Tier = "full" | "lite" | "photos";

type Nav = Navigator & { deviceMemory?: number; connection?: { saveData?: boolean } };

/** software rasterisers: every drag would be a slideshow and the fan would spin up */
const SOFTWARE = /swiftshader|llvmpipe|softpipe|lavapipe|software|basic render/i;

/** a phone or a tablet: touch only, no hover */
export const handheld = () => typeof window !== "undefined" && matchMedia("(hover: none) and (pointer: coarse)").matches;

export async function pickTier(): Promise<Tier> {
  if (typeof window === "undefined") return "photos";
  const nav = navigator as Nav;
  if (nav.connection?.saveData) return "photos";
  const mem = nav.deviceMemory ?? 8, cores = nav.hardwareConcurrency ?? 8;
  if (mem <= 2) return "photos";
  // a phone, or a machine short of memory or cores (a laptop's 4 cores are plenty: the GPU does the work)
  const small = handheld() || mem <= 4 || cores <= 2;
  let adapter: GPUAdapter | null = null;
  if ("gpu" in navigator) {
    try { adapter = await navigator.gpu.requestAdapter({ powerPreference: "high-performance" }); } catch { adapter = null; }
  }
  const a = adapter as unknown as { isFallbackAdapter?: boolean; info?: { isFallbackAdapter?: boolean; description?: string } } | null;
  const softGPU = !a || !!a.isFallbackAdapter || !!a.info?.isFallbackAdapter || SOFTWARE.test(a.info?.description ?? "");
  // a real GPU answered: nothing more to ask (opening a WebGL context just to read its name costs a beat)
  if (!softGPU) return small ? "lite" : "full";
  let renderer = "", webgl = false;
  try {
    const gl = document.createElement("canvas").getContext("webgl2");
    if (gl) {
      webgl = true;
      const ext = gl.getExtension("WEBGL_debug_renderer_info");
      renderer = String(gl.getParameter(ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER));
      gl.getExtension("WEBGL_lose_context")?.loseContext();
    }
  } catch { webgl = false; }
  return !webgl || SOFTWARE.test(renderer) ? "photos" : "lite";
}
