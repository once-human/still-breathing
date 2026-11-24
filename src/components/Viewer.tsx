"use client";

import { useEffect, useRef, useState } from "react";
import { COLOURS, DESIGNS, type Colour, type Design } from "@/content/tee";
import type { Format, Look, PhotoJob } from "@/lib/viewer/photo";
import type { Variant } from "@/lib/viewer/raster";
import { pickTier } from "@/lib/viewer/tier";

type Engine = {
  setLook: (d: Design, t: Colour) => void;
  turnTo: (deg: number) => void;
  setMagnify: (on: boolean) => void;
  setScene: (id: string) => void;
  photo: (job: PhotoJob) => Promise<Blob>;
  setVariant: (v: Variant) => Promise<void>;
  dispose: () => void;
};

const VIEWS = [
  { label: "front", yaw: 0 },
  { label: "¾", yaw: 30 },
  { label: "side", yaw: 90 },
  { label: "back", yaw: 180 },
];
// samples before the denoiser runs and the traced frame replaces the real-time one: enough for clean soft shadows
const MAX_SPP = 40;
// labels only; the rigs live in lib/viewer/scene.ts (kept out of the page bundle until the viewer loads)
const SCENE_LIST = [{ id: "studio", label: "studio" }, { id: "window", label: "window" }, { id: "show", label: "the show" }];
const PHOTO_SPP = 64;
// the tracer checks itself: past this many ms per sample it first traces fewer pixels, then hands over to the frames
const SLOW_MS = 80;
const STILL = (d: string, a: number) => `/tee/still/${d}/a${a}.webp`;
const FORMAT_LIST: { id: Format; label: string }[] = [{ id: "story", label: "story 9:16" }, { id: "post", label: "post 4:5" }];
const LOOK_LIST: Look[] = ["clean", "film"];

/**
 * The tee on a seamless sweep. Drag to turn it; let go and the browser path-traces the exact view
 * (same cotton, ink and softboxes as the offline renders), sharpening over a few seconds.
 */
export function Viewer({ design, tee, variant }: { design: Design; tee: Colour; variant: Variant }) {
  const stage = useRef<HTMLDivElement>(null);
  const rasterCv = useRef<HTMLCanvasElement>(null);
  const traceCv = useRef<HTMLCanvasElement>(null);
  const still = useRef<HTMLImageElement>(null);
  const engine = useRef<Engine | null>(null);
  const [status, setStatus] = useState("");
  const [view, setView] = useState(0);
  const [magnify, setMagnify] = useState(false);
  const lookRef = useRef({ design, tee });
  const variantRef = useRef(variant);
  const sceneRef = useRef("studio");
  const [sceneId, setSceneId] = useState("studio");
  const [canPhoto, setCanPhoto] = useState(false);
  const [format, setFormat] = useState<Format>("story");
  const [look, setLook] = useState<Look>("film");
  const [developing, setDeveloping] = useState<number | null>(null);
  const [photo, setPhoto] = useState<{ url: string; blob: Blob; name: string } | null>(null);
  const stopPhoto = useRef<AbortController | null>(null);
  // the offline path-traced frames, 12 angles, drag to turn: shown at once while the 3D loads ("poster"),
  // and for good on devices that should not run 3D at all ("flat")
  const [mode, setMode] = useState<"poster" | "3d" | "flat">("poster");
  const [ang, setAng] = useState(0);
  const angRef = useRef(0);
  const flatDrag = useRef<{ x: number; a: number } | null>(null);

  useEffect(() => {
    let dead = false;
    (async () => {
      const tier = await pickTier();
      if (dead) return;
      if (tier === "photos") { setMode("flat"); return; }   // the 3D code is never downloaded
      // nothing 3D is fetched until the viewer is about to be seen
      await new Promise<void>((res) => {
        const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { io.disconnect(); res(); } }, { rootMargin: "300px" });
        io.observe(stage.current!);
      });
      if (dead) return;
      const [{ Raster, FABRIC }, { SCENES, CAMERA, BODY_CAMERA }, PT] = await Promise.all([
        import("@/lib/viewer/raster"), import("@/lib/viewer/scene"), tier === "trace" ? import("@/lib/viewer/pathtracer") : Promise.resolve(null),
      ]);
      if (dead || !stage.current || !rasterCv.current || !traceCv.current) return;
      const st = stage.current, img = still.current!, tc = traceCv.current;
      const raster = new Raster(rasterCv.current);
      await raster.init();
      let scene = SCENES.find((x) => x.id === sceneRef.current) ?? SCENES[0];
      raster.setScene(scene, lookRef.current.tee === "cream");

      type PathTracer = InstanceType<NonNullable<typeof PT>["PathTracer"]>;
      let pt: PathTracer | null = null;
      if (PT && PT.PathTracer.supported()) {
        try { pt = new PT.PathTracer(); await pt.init(tc); } catch (e) { console.warn("path tracer off", e); pt = null; }
      }
      const s = { design: lookRef.current.design, tee: lookRef.current.tee, yaw: angRef.current, goal: null as number | null, vel: 0, drag: false, crop: [0, 0, 1] as [number, number, number], magnify: false, moving: true, dirty: true, photo: false, loading: false, variant: variantRef.current };

      const bitmap = async (url: string) => createImageBitmap(await (await fetch(url)).blob(), { colorSpaceConversion: "none", premultiplyAlpha: "none" });
      const maps: Record<string, Promise<[ImageBitmap, ImageBitmap]>> = {};
      const colourMaps = (d: Design, t: Colour) => (maps[`${d}-${t}`] ??= Promise.all([bitmap(`/tee/fit/tex/color-${d}-${t}.jpg`), bitmap(`/tee/fit/tex/orm-${d}-${t}.png`)]));
      const normals: Record<string, Promise<ImageBitmap>> = {};
      let knitB: ImageBitmap | null = null;
      /** a tee from the fit pipeline (and in fit mode its body); the path tracer re-indexes it */
      const loadVariant = async (v: Variant) => {
        s.loading = true;
        while (busy) await new Promise((r) => setTimeout(r, 16));
        try {
          const geo = await raster.load(s.design, s.tee, v);
          const cam = v.body ? BODY_CAMERA[v.pose] : CAMERA;
          raster.setCamera(cam);
          if (pt) {
            const [[c, o], nrm] = await Promise.all([colourMaps(s.design, s.tee), (normals[v.size] ??= bitmap(`/tee/fit/tex/normal-${v.size}.png`))]);
            knitB ??= await bitmap("/tee/fit/tex/knit-normal.png");
            pt.imgNormal = nrm; pt.imgKnit = knitB;
            await pt.setGeometry(geo);
            pt.setImages({ color: c, orm: o, normal: nrm, knit: knitB });
            if (v.skin) pt.skin = v.skin;
            pt.setCamera(cam);
            pt.setScene(scene, FABRIC[s.tee], s.tee === "cream");
          }
          s.variant = v;
        } finally { s.loading = false; s.dirty = true; lastSig = ""; }
      };
      let busy = false, lastSig = "";
      await loadVariant(s.variant);
      if (dead) return;

      // ---------- sizing ----------
      // rasterK: drops while dragging if frames run slow, back to 1 the moment the view comes to rest
      // traceK : the tracer's resolution, lowered once if this GPU turns out slow
      let rasterK = 1, dragK = 1, traceK = Math.min(devicePixelRatio, 1.5);
      const fullDpr = () => Math.min(devicePixelRatio, 2) * (tier === "trace" ? 1 : 0.75);
      const size = () => {
        const w = st.clientWidth, h = st.clientHeight;
        raster.resize(w, h, fullDpr() * rasterK);
        tc.width = Math.round(w * traceK); tc.height = Math.round(h * traceK);
        pt?.resize(tc.width, tc.height);
        s.dirty = true;
      };
      const setRasterK = (k: number) => { if (k === rasterK) return; rasterK = k; raster.resize(st.clientWidth, st.clientHeight, fullDpr() * k); s.dirty = true; };
      const ro = new ResizeObserver(size); ro.observe(st); size();
      // off screen, nothing runs
      let onScreen = true;
      const vis = new IntersectionObserver((es) => { onScreen = es[0].isIntersecting; if (onScreen) s.dirty = true; });
      vis.observe(st);

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
      let raf = 0, shown = -1, firstFrame = true, lastT = 0, ema = 16.7;
      const loop = () => {
        raf = requestAnimationFrame(loop);
        if (process.env.NODE_ENV !== "production") Object.assign(window, { __sb: { pt, raster, s, SCENES, tier, k: () => ({ rasterK, dragK, traceK }) } });
        if (!onScreen) { lastT = 0; return; }
        if (firstFrame) s.yaw = angRef.current;   // pick up wherever the photos were turned to while this loaded
        if (!s.drag && s.goal !== null) {
          const d = s.goal - s.yaw; s.yaw += d * 0.14;
          if (Math.abs(d) < 0.02) { s.yaw = s.goal; s.goal = null; }
          s.dirty = true;
        }
        const sig = `${s.design}|${s.tee}|${s.yaw.toFixed(3)}|${s.crop.join(",")}`;
        const moving = s.drag || s.goal !== null;
        // frame-time governor: a weak GPU drags at fewer pixels instead of stuttering; full sharpness at rest
        const now = performance.now();
        if (moving) {
          if (lastT && now - lastT < 250) ema = ema * 0.85 + (now - lastT) * 0.15;
          if (ema > 28 && dragK > 0.5) { dragK = Math.max(0.5, dragK * 0.8); ema = 20; }
          setRasterK(dragK);
        } else setRasterK(1);
        lastT = moving ? now : 0;
        if (s.dirty || sig !== lastSig) {
          raster.setView(s.yaw, s.crop, st.clientWidth, st.clientHeight);
          raster.render();
          if (firstFrame) { firstFrame = false; setMode("3d"); }
          if (sig !== lastSig) pt?.setView({ yaw: s.yaw, crop: [...s.crop], knit: true });
          lastSig = sig; s.dirty = false;
          tc.style.opacity = "0"; shown = -1;
          setStatus("");
        }
        if (!pt) {
          // no WebGPU: show the offline path-traced frame whenever the view lands on one
          const y = ((s.yaw % 360) + 360) % 360, near = (Math.round(y / 30) * 30) % 360;
          const ok = !s.variant.body && !moving && Math.abs(y - near) < 0.5 && s.crop[2] === 1;
          if (ok && !img.src.endsWith(STILL(s.design, near))) img.src = STILL(s.design, near);
          img.style.opacity = ok && img.complete && img.naturalWidth > 0 ? "1" : "0";
          return;
        }
        if (s.photo || s.loading || moving || busy || pt.clean) return;
        busy = true;
        // traced out of sight, a few samples per frame so the page stays responsive; the real-time view stays up
        // until the denoised frame is ready, then it fades across. No grain is ever on screen.
        const n = pt.lastMs > 0 ? clamp(Math.floor(24 / pt.lastMs), 1, 8) : 1;
        const go = pt.frame + n >= MAX_SPP ? pt.step(Math.max(1, MAX_SPP - pt.frame), false).then(() => pt!.denoise(true)) : pt.step(n, false);
        const p = pt;
        go.then(() => {
          busy = false;
          if (p !== pt) return;
          if (p.clean && shown !== p.frame) { shown = p.frame; tc.style.opacity = "1"; }
          // too slow here: trace fewer pixels once, then leave it to the offline frames
          if (!p.clean && p.frame >= 4 && p.lastMs > SLOW_MS) {
            if (traceK > 0.75) { traceK = 0.75; size(); p.setView({ yaw: s.yaw, crop: [...s.crop], knit: true }); lastSig = ""; }
            else { console.info("path tracer too slow on this GPU, using the rendered frames"); pt = null; p.device.destroy(); tc.style.opacity = "0"; setCanPhoto(false); s.dirty = true; }
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
        photo: async (job) => {
          if (!pt) throw new Error("photos need WebGPU");
          s.photo = true;
          while (busy) await new Promise((r) => setTimeout(r, 16));
          const { renderPhoto } = await import("@/lib/viewer/photo");
          try { return await renderPhoto(pt, job); }
          finally {
            s.photo = false; size();
            pt.setView({ yaw: s.yaw, crop: [...s.crop], knit: true });
            s.dirty = true; lastSig = "";
          }
        },
        setVariant: (v) => loadVariant(v),
        setMagnify: (on) => { s.magnify = on; if (!on) s.crop = [0, 0, 1]; s.dirty = true; },
        dispose: () => {
          cancelAnimationFrame(raf); ro.disconnect(); vis.disconnect();
          st.removeEventListener("pointerdown", down); st.removeEventListener("pointermove", move);
          st.removeEventListener("pointerup", up); st.removeEventListener("pointercancel", up);
          st.removeEventListener("wheel", wheel); st.removeEventListener("click", click);
          raster.renderer.dispose(); pt?.device.destroy();
        },
      };
      setCanPhoto(!!pt);
      if (JSON.stringify(variantRef.current) !== JSON.stringify(s.variant)) engine.current.setVariant(variantRef.current);
      const want = lookRef.current;
      if (want.tee !== s.tee || want.design !== s.design) engine.current.setLook(want.design, want.tee);
    })().catch((e) => { console.warn("3D view off, showing the rendered frames", e); setStatus(""); setMode("flat"); });
    return () => { dead = true; engine.current?.dispose(); engine.current = null; };
  }, []);

  useEffect(() => { lookRef.current = { design, tee }; engine.current?.setLook(design, tee); }, [design, tee]);
  const vKey = JSON.stringify(variant);
  useEffect(() => { variantRef.current = variant; engine.current?.setVariant(variant); }, [vKey]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => { if (photo) URL.revokeObjectURL(photo.url); }, [photo]);

  const makePhoto = async () => {
    if (!engine.current || developing !== null) return;
    const ac = new AbortController(); stopPhoto.current = ac;
    const d = DESIGNS[design], sc = SCENE_LIST.find((x) => x.id === sceneId)!;
    setDeveloping(0);
    try {
      const blob = await engine.current.photo({
        format, look, spp: PHOTO_SPP, signal: ac.signal,
        caption: { title: "again..", line: `${d.no} ${d.name} · ${COLOURS[tee].name} · ${sc.label}`, foot: "the india shows, december" },
        onProgress: (n, t) => setDeveloping(n / t),
      });
      setPhoto({ url: URL.createObjectURL(blob), blob, name: `still-breathing-${d.name}-${tee}-${sceneId}-${format}.jpg` });
    } catch (e) {
      if ((e as Error).name !== "AbortError") { console.error(e); setStatus("the photo could not be made"); }
    } finally { setDeveloping(null); stopPhoto.current = null; }
  };
  const share = async () => {
    if (!photo) return;
    const file = new File([photo.blob], photo.name, { type: "image/jpeg" });
    if (navigator.canShare?.({ files: [file] })) { try { await navigator.share({ files: [file], title: "still breathing" }); } catch { /* closed */ } }
  };

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
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={STILL(design, ang)} alt="" draggable={false} fetchPriority="high"
          className={`absolute inset-0 h-full w-full transition-opacity duration-300 ${mode === "3d" ? "pointer-events-none opacity-0" : ""}`}
          onPointerDown={(e) => { if (mode === "3d") return; e.currentTarget.setPointerCapture(e.pointerId); flatDrag.current = { x: e.clientX, a: ang }; }}
          onPointerMove={(e) => {
            const d = flatDrag.current; if (!d) return;
            const steps = Math.round((e.clientX - d.x) / 45);
            const a = (((d.a + steps * 30) % 360) + 360) % 360; angRef.current = a; setAng(a);
          }}
          onPointerUp={() => { flatDrag.current = null; }}
        />
        <p className="pointer-events-none absolute bottom-3 left-3 text-[12px] text-black/60 tnum">{status}</p>
      </div>
      <div className="mt-2 flex flex-wrap items-baseline gap-x-5 gap-y-1 text-[13px]">
        {VIEWS.map((v, i) => (
          <button key={v.label} onClick={() => { setView(i); engine.current?.turnTo(v.yaw); if (mode !== "3d") { const a = ((Math.round(v.yaw / 30) * 30) % 360 + 360) % 360; angRef.current = a; setAng(a); } }} className={`hit ${i === view && !magnify ? "font-semibold" : "text-quiet hover:text-ink"}`}>
            {v.label}
          </button>
        ))}
        <button onClick={() => { const on = !magnify; setMagnify(on); engine.current?.setMagnify(on); }} className={`hit ml-auto ${magnify ? "font-semibold" : "text-quiet hover:text-ink"}`}>
          {magnify ? "close loupe" : "loupe"}
        </button>
      </div>
      <div className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1 border-t border-line pt-1.5 text-[13px]" role="group" aria-label="Light">
        <span className="text-quiet">light</span>
        {SCENE_LIST.map((x) => (
          <button key={x.id} onClick={() => { sceneRef.current = x.id; setSceneId(x.id); engine.current?.setScene(x.id); }} className={`hit ${x.id === sceneId ? "font-semibold" : "text-quiet hover:text-ink"}`}>
            {x.label}
          </button>
        ))}
      </div>
      {canPhoto ? (
        <div className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1 border-t border-line pt-1.5 text-[13px]" role="group" aria-label="Photo">
          <span className="text-quiet">photo</span>
          {FORMAT_LIST.map((x) => (
            <button key={x.id} onClick={() => setFormat(x.id)} className={x.id === format ? "font-semibold" : "text-quiet hover:text-ink"}>{x.label}</button>
          ))}
          <span className="text-line" aria-hidden>/</span>
          {LOOK_LIST.map((x) => (
            <button key={x} onClick={() => setLook(x)} className={x === look ? "font-semibold" : "text-quiet hover:text-ink"}>{x}</button>
          ))}
          {developing === null ? (
            <button onClick={makePhoto} className="ml-auto font-semibold text-blue hover:text-ink">make the photo →</button>
          ) : (
            <span className="ml-auto tnum">
              developing · {Math.round(developing * 100)}%{" "}
              <button onClick={() => stopPhoto.current?.abort()} className="text-quiet underline hover:text-ink">stop</button>
            </span>
          )}
        </div>
      ) : null}
      {photo ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" role="dialog" aria-label="Your photo" onClick={() => setPhoto(null)}>
          <div className="flex max-h-full flex-col items-center gap-3" onClick={(e) => e.stopPropagation()}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={photo.url} alt="The tee, path traced" className="max-h-[80vh] w-auto max-w-full" />
            <div className="flex gap-6 text-[14px]">
              <a href={photo.url} download={photo.name} className="font-semibold text-ink hover:text-blue">save</a>
              {typeof navigator !== "undefined" && "share" in navigator ? <button onClick={share} className="text-ink hover:text-blue">share</button> : null}
              <button onClick={() => setPhoto(null)} className="text-quiet hover:text-ink">close</button>
            </div>
          </div>
        </div>
      ) : null}
      {magnify ? <p className="mt-1 text-[12px] text-quiet">click to look close, scroll to zoom up to 12×, drag to move. it re-renders the cloth at that size, nothing is stretched.</p> : null}
    </div>
  );
}

function clamp(v: number, a: number, b: number) { return Math.min(b, Math.max(a, v)); }
