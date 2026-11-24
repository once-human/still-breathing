// Whether this device runs the live 3D view at all. One view for everyone who can: the same smooth real-time
// tee at full sharpness, the path tracer refining it whenever it comes to rest (where WebGPU exists).
// Only a machine with no graphics hardware (or Data Saver on, or very little memory) gets the rendered frames.
export type Tier = "live" | "photos";

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
  return softGL && softGPU ? "photos" : "live";
}
