"use client";

import { useEffect, useRef, useState } from "react";
import type { Colour, Design } from "@/content/tee";

type Engine = {
  setLook: (d: Design, t: Colour) => void;
  turnTo: (deg: number) => void;
  setMagnify: (on: boolean) => void;
  setScene: (id: string) => void;
  dispose: () => void;
};

const VIEWS = [
  { label: "front", yaw: 0 },
  { label: "¾", yaw: 30 },
  { label: "side", yaw: 90 },
  { label: "back", yaw: 180 },
];
const MAX_SPP = 256;
// labels only; the rigs live in lib/viewer/scene.ts (kept out of the page bundle until the viewer loads)
const SCENE_LIST = [
  { id: "studio", label: "studio" }, { id: "window", label: "window" }, { id: "overcast", label: "overcast" },
  { id: "tube", label: "tube light" }, { id: "flash", label: "phone flash" }, { id: "concert", label: "the show" },
];

/**
 * The tee on a seamless sweep. Drag to turn it; let go and the browser path-traces the exact view
 * (same cotton, ink and softboxes as the offline renders), sharpening over a few seconds.
 */
export function Viewer({ design, tee }: { design: Design; tee: Colour }) {
  const stage = useRef<HTMLDivElement>(null);
  const rasterCv = useRef<HTMLCanvasElement>(null);
  const traceCv = useRef<HTMLCanvasElement>(null);
  const still = useRef<HTMLImageElement>(null);
  const engine = useRef<Engine | null>(null);
  const [status, setStatus] = useState("loading the tee");
  const [view, setView] = useState(0);
  const [magnify, setMagnify] = useState(false);
  const lookRef = useRef({ design, tee });
  const sceneRef = useRef("studio");
  const [sceneId, setSceneId] = useState("studio");

  useEffect(() => {
    let dead = false;
    (async () => {
      const [{ Raster, FABRIC }, { PathTracer }, { SCENES }] = await Promise.all([
        import("@/lib/viewer/raster"), import("@/lib/viewer/pathtracer"), import("@/lib/viewer/scene"),
      ]);
      if (dead || !stage.current || !rasterCv.current || !traceCv.current) return;
      const st = stage.current, img = still.current!, tc = traceCv.current;
      const raster = new Raster(rasterCv.current);
      await raster.init();
      let scene = SCENES.find((x) => x.id === sceneRef.current) ?? SCENES[0];
      raster.setScene(scene, lookRef.current.tee === "cream");

      let pt: InstanceType<typeof PathTracer> | null = null;
      if (PathTracer.supported()) {
        try { pt = new PathTracer(); await pt.init(tc); } catch (e) { console.warn("path tracer off", e); pt = null; }
      }
      const s = { design: lookRef.current.design, tee: lookRef.current.tee, yaw: 0, goal: null as number | null, vel: 0, drag: false, crop: [0, 0, 1] as [number, number, number], magnify: false, moving: true, dirty: true };

      setStatus("loading the tee");
      const geo = await raster.load(s.design, s.tee);
      if (dead) return;

      const bitmap = async (url: string) => createImageBitmap(await (await fetch(url)).blob(), { colorSpaceConversion: "none", premultiplyAlpha: "none" });
      const maps: Record<string, Promise<[ImageBitmap, ImageBitmap]>> = {};
      const colourMaps = (d: Design, t: Colour) => (maps[`${d}-${t}`] ??= Promise.all([bitmap(`/tee/fred/color-${d}-${t}.jpg`), bitmap(`/tee/fred/orm-${d}-${t}.png`)]));
      if (pt) {
        setStatus("indexing 2,52,056 triangles");
        const [[c, o], nrm, knit] = await Promise.all([colourMaps(s.design, s.tee), bitmap("/tee/fred/normal.png"), bitmap("/tee/fred/knit-normal.png")]);
        pt.imgNormal = nrm; pt.imgKnit = knit;
        await pt.setGeometry(geo);
        pt.setImages({ color: c, orm: o, normal: nrm, knit });
        pt.setScene(scene, FABRIC[s.tee], s.tee === "cream");
      }
      if (dead) return;

      // ---------- sizing ----------
      const size = () => {
        const w = st.clientWidth, h = st.clientHeight;
        raster.resize(w, h, Math.min(devicePixelRatio, 2));
        const k = Math.min(devicePixelRatio, 1.5);
        tc.width = Math.round(w * k); tc.height = Math.round(h * k);
        pt?.resize(tc.width, tc.height);
        s.dirty = true;
      };
      const ro = new ResizeObserver(size); ro.observe(st); size();

      // ---------- interaction ----------
      let lx = 0, ly = 0, lt = 0;
      const down = (e: PointerEvent) => { s.drag = true; st.setPointerCapture(e.pointerId); lx = e.clientX; ly = e.clientY; lt = performance.now(); s.vel = 0; s.goal = null; s.dirty = true; };
      const move = (e: PointerEvent) => {
        if (!s.drag) return;
        const dx = e.clientX - lx, dy = e.clientY - ly, now = performance.now();
        if (s.magnify) {
          const z = s.crop[2];
          s.crop[0] = clamp(s.crop[0] - (dx / st.clientWidth) * 2 / z, -1 + 1 / z, 1 - 1 / z);
          s.crop[1] = clamp(s.crop[1] + (dy / st.clientHeight) * 2 / z, -1 + 1 / z, 1 - 1 / z);
        } else {
          s.yaw += dx * 0.45; s.vel = ((dx * 0.45) / Math.max(1, now - lt)) * 16;
        }
        lx = e.clientX; ly = e.clientY; lt = now; s.dirty = true;
      };
      const up = () => { if (!s.drag) return; s.drag = false; if (!s.magnify && Math.abs(s.vel) > 0.3) s.goal = s.yaw + s.vel * 8; s.dirty = true; };
      const wheel = (e: WheelEvent) => {
        if (!s.magnify) return;
        e.preventDefault();
        const r = st.getBoundingClientRect();
        const nx = ((e.clientX - r.left) / r.width) * 2 - 1, ny = 1 - ((e.clientY - r.top) / r.height) * 2;
        const z0 = s.crop[2], z = clamp(z0 * Math.exp(-e.deltaY * 0.002), 1, 12);
        // keep the point under the cursor still
        const px = s.crop[0] + nx / z0, py = s.crop[1] + ny / z0;
        s.crop = [clamp(px - nx / z, -1 + 1 / z, 1 - 1 / z), clamp(py - ny / z, -1 + 1 / z, 1 - 1 / z), z];
        s.dirty = true;
      };
      const click = (e: MouseEvent) => {
        if (!s.magnify || s.crop[2] > 1.01) return;
        const r = st.getBoundingClientRect(), z = 4;
        const nx = ((e.clientX - r.left) / r.width) * 2 - 1, ny = 1 - ((e.clientY - r.top) / r.height) * 2;
        s.crop = [clamp(nx, -1 + 1 / z, 1 - 1 / z), clamp(ny, -1 + 1 / z, 1 - 1 / z), z]; s.dirty = true;
      };
      st.addEventListener("pointerdown", down); st.addEventListener("pointermove", move);
      st.addEventListener("pointerup", up); st.addEventListener("pointercancel", up);
      st.addEventListener("wheel", wheel, { passive: false }); st.addEventListener("click", click);

      // ---------- loop ----------
      let raf = 0, busy = false, shown = -1, lastSig = "";
      const STILL = (t: Colour, a: number) => `/tee/fred-b-${t}/turntable/a${a}.png`;
      const loop = () => {
        raf = requestAnimationFrame(loop);
      if (process.env.NODE_ENV !== "production") Object.assign(window, { __sb: { pt, raster, s, SCENES } });
        if (!s.drag && s.goal !== null) {
          const d = s.goal - s.yaw; s.yaw += d * 0.14;
          if (Math.abs(d) < 0.02) { s.yaw = s.goal; s.goal = null; }
          s.dirty = true;
        }
        const sig = `${s.design}|${s.tee}|${s.yaw.toFixed(3)}|${s.crop.join(",")}`;
        const moving = s.drag || s.goal !== null;
        if (s.dirty || sig !== lastSig) {
          raster.setView(s.yaw, s.crop, st.clientWidth, st.clientHeight);
          raster.render();
          if (sig !== lastSig) pt?.setView({ yaw: s.yaw, crop: [...s.crop], knit: true });
          lastSig = sig; s.dirty = false;
          tc.style.opacity = "0"; shown = -1;
          setStatus(moving ? (s.magnify ? "moving the loupe" : "turning") : pt ? "tracing light" : "real-time");
        }
        if (!pt) {
          // no WebGPU: show the offline path-traced frame whenever the view lands on one
          const y = ((s.yaw % 360) + 360) % 360, near = (Math.round(y / 30) * 30) % 360;
          const ok = s.design === "b" && !moving && Math.abs(y - near) < 0.5 && s.crop[2] === 1;
          img.style.opacity = ok ? "1" : "0";
          if (ok && !img.src.endsWith(STILL(s.tee, near))) img.src = STILL(s.tee, near);
          return;
        }
        if (moving || busy || pt.frame >= MAX_SPP) return;
        busy = true;
        // as many samples as fit in ~20 ms, so the page stays responsive while the light settles
        const n = pt.lastMs > 0 ? clamp(Math.floor(20 / pt.lastMs), 1, 8) : 1;
        pt.step(n).then(() => {
          busy = false;
          if (pt!.frame >= 6) tc.style.opacity = "1";
          if (pt!.frame !== shown) {
            shown = pt!.frame;
            setStatus(pt!.frame >= MAX_SPP ? `path traced · ${MAX_SPP} samples` : `tracing light · ${pt!.frame} of ${MAX_SPP}`);
          }
        });
      };
      raf = requestAnimationFrame(loop);

      engine.current = {
        setLook: async (d, t) => {
          const [c, o] = await Promise.all([pt ? colourMaps(d, t) : Promise.resolve(null), raster.setLook(d, t)]).then(([m]) => m ?? [null, null]);
          s.design = d; s.tee = t; raster.setScene(scene, t === "cream");
          if (pt && c && o) { pt.setColourway(c, o); pt.setScene(scene, FABRIC[t], t === "cream"); }
          s.dirty = true; lastSig = "";
        },
        turnTo: (deg) => { const d = ((((deg - s.yaw) % 360) + 540) % 360) - 180; s.goal = s.yaw + d; s.crop = [0, 0, 1]; },
        setScene: (id) => {
          scene = SCENES.find((x) => x.id === id) ?? SCENES[0];
          raster.setScene(scene, s.tee === "cream"); pt?.setScene(scene, FABRIC[s.tee], s.tee === "cream");
          s.dirty = true; lastSig = "";
        },
        setMagnify: (on) => { s.magnify = on; if (!on) s.crop = [0, 0, 1]; s.dirty = true; },
        dispose: () => {
          cancelAnimationFrame(raf); ro.disconnect();
          st.removeEventListener("pointerdown", down); st.removeEventListener("pointermove", move);
          st.removeEventListener("pointerup", up); st.removeEventListener("pointercancel", up);
          st.removeEventListener("wheel", wheel); st.removeEventListener("click", click);
          raster.renderer.dispose(); pt?.device.destroy();
        },
      };
      const want = lookRef.current;
      if (want.tee !== s.tee || want.design !== s.design) engine.current.setLook(want.design, want.tee);
    })().catch((e) => { console.error(e); setStatus("the 3D view could not start"); });
    return () => { dead = true; engine.current?.dispose(); engine.current = null; };
  }, []);

  useEffect(() => { lookRef.current = { design, tee }; engine.current?.setLook(design, tee); }, [design, tee]);

  return (
    <div>
      <div
        ref={stage}
        data-lenis-prevent
        className={`relative aspect-[880/1120] w-full touch-none overflow-hidden bg-studio select-none ${magnify ? "cursor-zoom-in" : "cursor-grab active:cursor-grabbing"}`}
        aria-label="The tee in 3D. Drag to turn it."
        role="img"
      >
        <canvas ref={rasterCv} className="absolute inset-0 h-full w-full" />
        <canvas ref={traceCv} className="absolute inset-0 h-full w-full opacity-0 transition-opacity duration-500" />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img ref={still} alt="" className="pointer-events-none absolute inset-0 h-full w-full opacity-0" />
        <p className="pointer-events-none absolute bottom-3 left-3 text-[12px] text-black/60 tnum">{status}</p>
      </div>
      <div className="mt-2 flex flex-wrap items-baseline gap-x-5 gap-y-1 text-[13px]">
        {VIEWS.map((v, i) => (
          <button key={v.label} onClick={() => { setView(i); engine.current?.turnTo(v.yaw); }} className={i === view && !magnify ? "font-semibold" : "text-quiet hover:text-ink"}>
            {v.label}
          </button>
        ))}
        <button onClick={() => { const on = !magnify; setMagnify(on); engine.current?.setMagnify(on); }} className={`ml-auto ${magnify ? "font-semibold" : "text-quiet hover:text-ink"}`}>
          {magnify ? "close loupe" : "loupe"}
        </button>
      </div>
      <div className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1 border-t border-line pt-1.5 text-[13px]" role="group" aria-label="Light">
        <span className="text-quiet">light</span>
        {SCENE_LIST.map((x) => (
          <button key={x.id} onClick={() => { sceneRef.current = x.id; setSceneId(x.id); engine.current?.setScene(x.id); }} className={x.id === sceneId ? "font-semibold" : "text-quiet hover:text-ink"}>
            {x.label}
          </button>
        ))}
      </div>
      {magnify ? <p className="mt-1 text-[12px] text-quiet">click to look close, scroll to zoom up to 12×, drag to move. it re-renders the cloth at that size, nothing is stretched.</p> : null}
    </div>
  );
}

function clamp(v: number, a: number, b: number) { return Math.min(b, Math.max(a, v)); }
