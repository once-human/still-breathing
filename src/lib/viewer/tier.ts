// How much of the viewer this device should run. Decided once, before any 3D code is downloaded.
//   trace  : real-time view + the browser path tracer (a real GPU with WebGPU)
//   raster : real-time view only; at rest on a 30° angle it shows the offline-traced frame
//   photos : the offline-traced frames only, drag to turn (no GPU worth the name, little memory, or Data Saver)
// The tracer also measures itself once running and steps down if this guess was too generous.
export type Tier = "trace" | "raster" | "photos";

type Nav = Navigator & { deviceMemory?: number; connection?: { saveData?: boolean } };

/** software rasterisers: every drag would be a slideshow and the fan would spin up */
const SOFTWARE = /swiftshader|llvmpipe|softpipe|lavapipe|software|basic render/i;

export async function pickTier(): Promise<Tier> {
  if (typeof window === "undefined") return "photos";
  const nav = navigator as Nav;
  if (nav.connection?.saveData) return "photos";
  if ((nav.deviceMemory ?? 8) <= 2) return "photos";
  let adapter: GPUAdapter | null = null;
  if ("gpu" in navigator) {
    try { adapter = await navigator.gpu.requestAdapter({ powerPreference: "high-performance" }); } catch { adapter = null; }
  }
  const a = adapter as unknown as { isFallbackAdapter?: boolean; info?: { isFallbackAdapter?: boolean; description?: string } } | null;
  const softGPU = !a || !!a.isFallbackAdapter || !!a.info?.isFallbackAdapter || SOFTWARE.test(a.info?.description ?? "");
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
  const softGL = !webgl || SOFTWARE.test(renderer);
  if (softGL && softGPU) return "photos";            // neither API has real hardware behind it
  if (softGPU || (nav.hardwareConcurrency ?? 4) <= 2) return softGL ? "photos" : "raster";
  return "trace";
}
