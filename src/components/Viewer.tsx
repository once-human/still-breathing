"use client";

import { useEffect, useRef, useState } from "react";
import { COLOURS, DESIGNS, type Colour, type Design } from "@/content/tee";
import type { Format, Look, PhotoJob } from "@/lib/viewer/photo";
import type { Variant } from "@/lib/viewer/raster";
import { pickTier } from "@/lib/viewer/tier";
import { prefetchTee, bitmap } from "@/lib/viewer/grab";
import { printBackURL, printFrontURL } from "@/lib/viewer/print";
import dynamic from "next/dynamic";

// the camera try-on, and the pose model behind it, only download when someone asks for it
const TryOn = dynamic(() => import("@/components/TryOn").then((m) => m.TryOn), { ssr: false });

type Engine = {
  setLook: (d: Design, t: Colour) => void;
  turnTo: (deg: number) => void;
  /** zoom by a factor (around the middle of the view); 0 resets */
  zoomBy: (k: number) => void;
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
const MAX_SPP = 32;
// the turntable's own speed, degrees a second: one turn in about 26 s
const SPIN = 14;
// labels only; the rigs live in lib/viewer/scene.ts (kept out of the page bundle until the viewer loads)
const SCENE_LIST = [{ id: "studio", label: "studio" }, { id: "window", label: "window" }, { id: "show", label: "the show" }];
const PHOTO_SPP = 64;
// GPU time the background tracer may use per frame, and the full-sample cost past which it isn't worth it
const TRACE_MS = 3;
const SLOW_MS = 600;
const STILL = (d: string, a: number) => `/tee/still/${d}/a${a}.webp`;
const FORMAT_LIST: { id: Format; label: string }[] = [{ id: "story", label: "story 9:16" }, { id: "post", label: "post 4:5" }];
const LOOK_LIST: Look[] = ["clean", "film"];

/**
 * The tee on a seamless sweep, turning slowly by itself. Put the pointer on it and it eases to a stop and is
 * yours to turn; the cloth swings with it. At rest the browser path-traces the exact view (same cotton, ink and
 * softboxes as the offline renders) and fades it in.
 */
export function Viewer({ design, tee, variant }: { design: Design; tee: Colour; variant: Variant }) {
  const stage = useRef<HTMLDivElement>(null);
  const rasterCv = useRef<HTMLCanvasElement>(null);
  const traceCv = useRef<HTMLCanvasElement>(null);
  const engine = useRef<Engine | null>(null);
  const [status, setStatus] = useState("");
  const [view, setView] = useState(0);
  const [tryOn, setTryOn] = useState(false);
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
      // the tee, its textures and the decoder start downloading now, alongside the 3D code, not after it
      prefetchTee(variantRef.current, lookRef.current.design, lookRef.current.tee);
      const code = Promise.all([import("@/lib/viewer/raster"), import("@/lib/viewer/scene")]);
      // nothing is drawn until the viewer is about to be seen
      await new Promise<void>((res) => {
        const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { io.disconnect(); res(); } }, { rootMargin: "300px" });
        io.observe(stage.current!);
      });
      if (dead) return;
      const [{ Raster, FABRIC }, { SCENES, CAMERA, BODY_CAMERA }] = await code;
      if (dead || !stage.current || !rasterCv.current || !traceCv.current) return;
      const st = stage.current, tc = traceCv.current;
      const raster = new Raster(rasterCv.current);
      await raster.init();
      let scene = SCENES.find((x) => x.id === sceneRef.current) ?? SCENES[0];
      raster.setScene(scene, lookRef.current.tee === "cream");

      type PathTracer = import("@/lib/viewer/pathtracer").PathTracer;
      let pt: PathTracer | null = null;
      const s = { design: lookRef.current.design, tee: lookRef.current.tee, yaw: angRef.current, goal: null as number | null, vel: 0, drag: false, dirty: true, photo: false, loading: false, variant: variantRef.current };
      // zoom: a crop of the same frame (the lens never moves, so the perspective never changes), eased
      const zm = { z: 1, cx: 0, cy: 0, zt: 1, cxt: 0, cyt: 0 };
      const ZMAX = 5;
      const clampZoom = () => {
        zm.zt = Math.min(ZMAX, Math.max(1, zm.zt));
        const lim = 1 - 1 / zm.zt;
        zm.cxt = Math.min(lim, Math.max(-lim, zm.cxt)); zm.cyt = Math.min(lim, Math.max(-lim, zm.cyt));
      };
      /** zoom to zt keeping the point under (sx, sy) (viewport NDC) where it is */
      const zoomAt = (zt: number, sx: number, sy: number) => {
        const px = zm.cxt + sx / zm.zt, py = zm.cyt + sy / zm.zt;
        zm.zt = Math.min(ZMAX, Math.max(1, zt));
        zm.cxt = px - sx / zm.zt; zm.cyt = py - sy / zm.zt;
        clampZoom(); s.dirty = true; s.goal = null;
        if (zm.zt > 1.5) void sharpen();
      };
      const ndc = (e: { clientX: number; clientY: number }) => {
        const r = st.getBoundingClientRect();
        return [((e.clientX - r.left) / r.width) * 2 - 1, 1 - ((e.clientY - r.top) / r.height) * 2] as const;
      };
      // close in, the back print is swapped for the full source resolution (fetched once per design)
      const sharpened = new Set<string>();
      const sharpen = async () => {
        const key = `${s.design}-${s.tee}`;
        if (sharpened.has(key)) return;
        sharpened.add(key);
        try {
          const url = printBackURL(s.design, s.tee, true);
          const tex = await raster.printTexture(url);
          raster.setBackPrint(s.design, s.tee, tex); s.dirty = true; lastSig = "";
          if (pt) { const [, f] = await colourMaps(s.design, s.tee); pt.setColourway(await bitmap(url), f); }
        } catch { /* the regular print stays */ }
      };

      const maps: Record<string, Promise<[ImageBitmap, ImageBitmap]>> = {};
      // the back and chest prints, at print resolution (the fabric itself is one flat colour)
      const colourMaps = (d: Design, t: Colour) => (maps[`${d}-${t}`] ??= Promise.all([bitmap(printBackURL(d, t)), bitmap(printFrontURL(t))]));
      const normals: Record<string, Promise<ImageBitmap>> = {};
      let knitB: ImageBitmap | null = null;
      let geo: Awaited<ReturnType<typeof raster.load>> | null = null;
      /** hands the current tee to the path tracer (it builds its own acceleration structure in a worker) */
      const ptLoad = async (p: PathTracer, v: Variant) => {
        if (!geo) return;
        const cam = v.body ? BODY_CAMERA[v.pose] : CAMERA;
        const [[c, o], nrm] = await Promise.all([colourMaps(s.design, s.tee), (normals[v.size] ??= bitmap(`/tee/fit/tex/normal-${v.size}.png`))]);
        knitB ??= await bitmap("/tee/fit/tex/knit-normal.png");
        p.imgNormal = nrm; p.imgKnit = knitB;
        await p.setGeometry(geo);
        p.setImages({ back: c, front: o, normal: nrm, knit: knitB });
        if (v.skin) p.skin = v.skin;
        p.setCamera(cam);
        p.setScene(scene, FABRIC[s.tee], s.tee === "cream");
      };
      /** a tee from the fit pipeline (and in fit mode its body) */
      const loadVariant = async (v: Variant) => {
        s.loading = true;
        while (busy) await new Promise((r) => setTimeout(r, 16));
        try {
          geo = await raster.load(s.design, s.tee, v);
          raster.setCamera(v.body ? BODY_CAMERA[v.pose] : CAMERA);
          if (pt) await ptLoad(pt, v);
          s.variant = v;
        } finally { s.loading = false; s.dirty = true; lastSig = ""; }
      };
      let busy = false, lastSig = "";
      await loadVariant(s.variant);
      if (dead) return;
      // every shader compiled before the first frame, off the main thread: the first turn is as smooth as the rest
      await raster.renderer.compileAsync(raster.scene, raster.camera).catch(() => {});
      if (dead) return;

      // ---------- sizing: always full sharpness, never a lower-resolution stand-in while it moves ----------
      const dpr = () => Math.min(devicePixelRatio || 1, 2);
      const traceK = () => Math.min(devicePixelRatio || 1, 1.5);
      const size = () => {
        const w = st.clientWidth, h = st.clientHeight;
        raster.resize(w, h, dpr());
        tc.width = Math.round(w * traceK()); tc.height = Math.round(h * traceK());
        pt?.resize(tc.width, tc.height);
        s.dirty = true; lastSig = "";
      };
      const ro = new ResizeObserver(size); ro.observe(st); size();
      // off screen, nothing runs
      let onScreen = true;
      const vis = new IntersectionObserver((es) => { onScreen = es[0].isIntersecting; if (onScreen) s.dirty = true; });
      vis.observe(st);

      // ---------- interaction: it turns by itself; hover and it eases to a stop and is yours to turn ----------
      const still = matchMedia("(prefers-reduced-motion: reduce)");
      let hover = false, holdUntil = 0, spin = still.matches ? 0 : SPIN;
      let lx = 0, ly = 0, lt = 0;
      const enter = (e: PointerEvent) => { if (e.pointerType !== "touch") hover = true; };
      const leave = (e: PointerEvent) => { if (e.pointerType !== "touch") hover = false; };
      // two fingers: pinch to zoom around their midpoint
      const touches = new Map<number, { x: number; y: number }>();
      let pinch: { d: number; z: number } | null = null;
      const spread = () => { const [a, b] = [...touches.values()]; return { d: Math.hypot(a.x - b.x, a.y - b.y), m: { clientX: (a.x + b.x) / 2, clientY: (a.y + b.y) / 2 } }; };
      const down = (e: PointerEvent) => {
        touches.set(e.pointerId, { x: e.clientX, y: e.clientY });
        st.setPointerCapture(e.pointerId);
        if (touches.size === 2) { s.drag = false; pinch = { d: spread().d, z: zm.zt }; return; }
        s.drag = true; lx = e.clientX; ly = e.clientY; lt = performance.now(); s.vel = 0; s.goal = null; s.dirty = true;
        if (e.pointerType === "touch") holdUntil = Infinity;
      };
      const move = (e: PointerEvent) => {
        if (touches.has(e.pointerId)) touches.set(e.pointerId, { x: e.clientX, y: e.clientY });
        if (pinch && touches.size === 2) { const g = spread(); const [sx, sy] = ndc(g.m); zoomAt(pinch.z * (g.d / Math.max(1, pinch.d)), sx, sy); return; }
        if (!s.drag) return;
        const dx = e.clientX - lx, dy = e.clientY - ly, now = performance.now();
        if (zm.zt > 1.01) {
          // zoomed in: dragging moves around the print
          zm.cxt -= (2 * dx) / (st.clientWidth * zm.zt); zm.cyt += (2 * dy) / (st.clientHeight * zm.zt); clampZoom();
        } else {
          s.yaw += dx * 0.45; s.vel = ((dx * 0.45) / Math.max(1, now - lt)) * 16;
        }
        lx = e.clientX; ly = e.clientY; lt = now; s.dirty = true;
      };
      const up = (e: PointerEvent) => {
        touches.delete(e.pointerId);
        if (touches.size < 2) pinch = null;
        if (!s.drag) return;
        s.drag = false; if (Math.abs(s.vel) > 0.3 && zm.zt <= 1.01) s.goal = s.yaw + s.vel * 8; s.dirty = true;
        if (e.pointerType === "touch") holdUntil = performance.now() + 2500;   // no hover on a phone: a pause, then it turns again
      };
      // double-click: in close where you point, again to step back out
      const dbl = (e: MouseEvent) => { const [sx, sy] = ndc(e); zoomAt(zm.zt > 1.2 ? 1 : 3, sx, sy); };
      // pinch on a trackpad (ctrl+wheel), or the wheel once already zoomed in
      const wheel = (e: WheelEvent) => {
        if (!e.ctrlKey && !e.metaKey && zm.zt <= 1.01) return;
        e.preventDefault();
        const [sx, sy] = ndc(e);
        zoomAt(zm.zt * Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.002)), sx, sy);
      };
      st.addEventListener("dblclick", dbl); st.addEventListener("wheel", wheel, { passive: false });
      st.addEventListener("pointerenter", enter); st.addEventListener("pointerleave", leave);
      st.addEventListener("pointerdown", down); st.addEventListener("pointermove", move);
      st.addEventListener("pointerup", up); st.addEventListener("pointercancel", up);

      // ---------- the path tracer: background work only ----------
      // It never takes a frame from you: it starts once the page has been idle a moment, works only while the tee
      // is at rest, the page is not scrolling, the tab is visible and the viewer is on screen, and then only in
      // strips of about 3 ms of GPU time per frame. Nothing grainy is ever shown: only the finished, denoised frame
      // fades in, and the moment anything moves it steps aside.
      let lastScroll = 0, restSince = 0;
      const onScroll = () => { lastScroll = performance.now(); };
      addEventListener("scroll", onScroll, { passive: true });
      addEventListener("wheel", onScroll, { passive: true });
      const quiet = (now: number) => now - lastScroll > 450 && document.visibilityState === "visible" && onScreen;
      const startTracer = async () => {
        // wait for a calm moment before even creating the device
        for (;;) {
          await new Promise<void>((r) => ("requestIdleCallback" in window ? requestIdleCallback(() => r(), { timeout: 4000 }) : setTimeout(r, 1500)));
          if (dead) return;
          if (quiet(performance.now())) break;
          await new Promise((r) => setTimeout(r, 800));
        }
        const PT = await import("@/lib/viewer/pathtracer");
        if (dead || !PT.PathTracer.supported()) return;
        const p = new PT.PathTracer();
        try { await p.init(tc); size(); p.resize(tc.width, tc.height); await ptLoad(p, s.variant); } catch (e) { console.warn("path tracer off", e); return; }
        if (dead) { p.device.destroy(); return; }
        pt = p; setCanPhoto(true); lastSig = "";
      };

      // ---------- loop ----------
      let raf = 0, shown = -1, firstFrame = true, prevT = 0, traced = false;
      const loop = (now: number) => {
        raf = requestAnimationFrame(loop);
        const dt = prevT ? Math.min(0.1, (now - prevT) / 1000) : 1 / 60;
        prevT = now;
        if (process.env.NODE_ENV !== "production") Object.assign(window, { __sb: { pt, raster, s, SCENES, spin: () => spin } });
        if (!onScreen) { prevT = 0; return; }
        if (firstFrame) s.yaw = angRef.current;   // pick up wherever the photos were turned to while this loaded
        // auto-turn: eases out when the pointer comes over the tee (or it's being turned, or a view was picked)
        const want = still.matches || hover || s.drag || s.goal !== null || s.photo || now < holdUntil || zm.zt > 1.01 ? 0 : SPIN;
        spin += (want - spin) * (1 - Math.exp(-dt / 0.45));
        if (Math.abs(spin) < 0.02 && want === 0) spin = 0;
        if (spin) { s.yaw += spin * dt; s.dirty = true; }
        if (!s.drag && s.goal !== null) {
          const d = s.goal - s.yaw; s.yaw += d * (1 - Math.exp(-dt * 9));
          if (Math.abs(d) < 0.02) { s.yaw = s.goal; s.goal = null; }
          s.dirty = true;
        }
        const ez = 1 - Math.exp(-dt / 0.14);
        const zooming = Math.abs(zm.zt - zm.z) > 1e-4 || Math.abs(zm.cxt - zm.cx) > 1e-5 || Math.abs(zm.cyt - zm.cy) > 1e-5;
        if (zooming) {
          zm.z += (zm.zt - zm.z) * ez; zm.cx += (zm.cxt - zm.cx) * ez; zm.cy += (zm.cyt - zm.cy) * ez;
          if (Math.abs(zm.zt - zm.z) < 1e-4) { zm.z = zm.zt; zm.cx = zm.cxt; zm.cy = zm.cyt; }
          s.dirty = true;
        }
        const moving = s.drag || s.goal !== null || spin !== 0 || zooming;
        raster.setView(s.yaw, [zm.cx, zm.cy, zm.z], st.clientWidth, st.clientHeight);
        const swinging = raster.simulate(dt);
        // every display frame is drawn (60, 120, whatever the screen runs at): a skipped frame in a steady turn
        // reads as a judder
        if (s.dirty || swinging) {
          raster.render();
          s.dirty = false;
          if (firstFrame) {
            firstFrame = false;
            // the photo steps aside only once the 3D has actually reached the screen, textures and all (two
            // frames on): never an empty or half-dressed tee in between
            requestAnimationFrame(() => requestAnimationFrame(() => { if (!dead) { setMode("3d"); setStatus(""); void startTracer(); } }));
          }
        }
        const busyCloth = moving || swinging;
        if (busyCloth) restSince = now;
        if (busyCloth && traced) { tc.style.transition = "opacity 120ms"; tc.style.opacity = "0"; traced = false; shown = -1; }
        if (!pt || busyCloth || s.photo || s.loading || busy || now - restSince < 300 || !quiet(now)) return;
        const sig = `${s.design}|${s.tee}|${s.yaw.toFixed(3)}|${zm.z.toFixed(4)}|${zm.cx.toFixed(4)}|${zm.cy.toFixed(4)}|${JSON.stringify(s.variant)}`;
        if (sig !== lastSig) { pt.setView({ yaw: s.yaw, crop: [zm.cx, zm.cy, zm.z], knit: true }); lastSig = sig; shown = -1; }
        if (pt.clean) return;
        busy = true;
        const p = pt;
        const go = p.frame >= MAX_SPP ? p.denoise(true) : p.work(TRACE_MS);
        go.then(() => {
          busy = false;
          if (p !== pt) return;
          if (p.clean && shown !== p.frame && lastSig === sig) { shown = p.frame; tc.style.transition = "opacity 450ms"; tc.style.opacity = "1"; traced = true; }
          // a GPU this slow would take ages to finish a frame: leave it to the live view
          if (!p.clean && p.lastMs > SLOW_MS) { console.info("path tracer too slow here, live view only"); pt = null; p.device.destroy(); tc.style.opacity = "0"; setCanPhoto(false); }
        }).catch(() => { busy = false; });
      };
      raf = requestAnimationFrame(loop);

      engine.current = {
        setLook: async (d, t) => {
          const [c, o] = await Promise.all([pt ? colourMaps(d, t) : Promise.resolve(null), raster.setLook(d, t)]).then(([m]) => m ?? [null, null]);
          s.design = d; s.tee = t; raster.setScene(scene, t === "cream");
          if (pt && c && o) { pt.setColourway(c, o); pt.setScene(scene, FABRIC[t], t === "cream"); }
          s.dirty = true; lastSig = "";
        },
        zoomBy: (k) => { if (k === 0) zoomAt(1, 0, 0); else zoomAt(zm.zt * k, 0, 0); },
        turnTo: (deg) => { const d = ((((deg - s.yaw) % 360) + 540) % 360) - 180; s.goal = s.yaw + d; holdUntil = performance.now() + 6000; },
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
            pt.setView({ yaw: s.yaw, crop: [0, 0, 1], knit: true });
            s.dirty = true; lastSig = "";
          }
        },
        setVariant: (v) => loadVariant(v),
        dispose: () => {
          cancelAnimationFrame(raf); ro.disconnect(); vis.disconnect();
          st.removeEventListener("pointerenter", enter); st.removeEventListener("pointerleave", leave);
          st.removeEventListener("pointerdown", down); st.removeEventListener("pointermove", move);
          st.removeEventListener("pointerup", up); st.removeEventListener("pointercancel", up);
          st.removeEventListener("dblclick", dbl); st.removeEventListener("wheel", wheel);
          removeEventListener("scroll", onScroll); removeEventListener("wheel", onScroll);
          raster.renderer.dispose(); pt?.device.destroy();
        },
      };
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
        className={`relative aspect-[880/1120] w-full touch-none overflow-hidden bg-studio select-none cursor-grab active:cursor-grabbing`}
        aria-label="The tee in 3D, turning slowly. Point at it to stop it, drag to turn it."
        role="img"
      >
        <canvas ref={rasterCv} className="absolute inset-0 h-full w-full" />
        <canvas ref={traceCv} className="absolute inset-0 h-full w-full opacity-0 transition-opacity duration-500" />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={STILL(design, ang)} alt="" draggable={false} fetchPriority="high"
          className={`absolute inset-0 h-full w-full transition-opacity duration-500 ${mode === "3d" ? "pointer-events-none opacity-0" : ""}`}
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
          <button key={v.label} onClick={() => { setView(i); engine.current?.zoomBy(0); engine.current?.turnTo(v.yaw); if (mode !== "3d") { const a = ((Math.round(v.yaw / 30) * 30) % 360 + 360) % 360; angRef.current = a; setAng(a); } }} className={`hit ${i === view ? "font-semibold" : "text-quiet hover:text-ink"}`}>
            {v.label}
          </button>
        ))}
        <span className="ml-auto flex items-baseline gap-3" role="group" aria-label="Zoom">
          <button onClick={() => engine.current?.zoomBy(1 / 1.6)} className="hit text-quiet hover:text-ink" aria-label="Zoom out">−</button>
          <span className="text-quiet">zoom</span>
          <button onClick={() => engine.current?.zoomBy(1.6)} className="hit text-quiet hover:text-ink" aria-label="Zoom in">+</button>
        </span>
        <button onClick={() => setTryOn(true)} className="hit font-semibold text-blue hover:text-ink">try it on →</button>
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
      {tryOn ? <TryOn design={design} tee={tee} onClose={() => setTryOn(false)} /> : null}
    </div>
  );
}

