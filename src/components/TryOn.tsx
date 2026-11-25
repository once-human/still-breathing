"use client";

import { useEffect, useRef, useState } from "react";
import { DESIGNS, SIZE_ORDER, type Colour, type Design, type Size } from "@/content/tee";
import type { TryOn as Engine, TryOnStatus } from "@/lib/tryon/engine";

const SAY: Record<TryOnStatus, string> = {
  model: "getting the body model ready…",
  camera: "allow the camera to see yourself in it",
  look: "step back until your shoulders and chest are in the frame",
  ready: "",
  nobody: "step back until your shoulders and chest are in the frame",
};

/**
 * The tee on you, through your own camera. The pose model runs in this tab, on this device: nothing is
 * recorded and nothing leaves the browser.
 */
export function TryOn({ design, tee, onClose }: { design: Design; tee: Colour; onClose: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const cv = useRef<HTMLCanvasElement>(null);
  const arms = useRef<HTMLCanvasElement>(null);
  const frame = useRef<HTMLCanvasElement>(null);
  const eng = useRef<Engine | null>(null);
  const [status, setStatus] = useState<TryOnStatus>("model");
  const [err, setErr] = useState("");
  const [look, setLook] = useState<Design>(design);
  const [size, setSize] = useState<Size>("M");
  // a photo or a clip, once taken: shown over the try-on to save or share
  const [shot, setShot] = useState<{ url: string; blob: Blob; video: boolean } | null>(null);
  const [rec, setRec] = useState<number | null>(null);   // when the recording started
  const [now, setNow] = useState(0);
  // the frame takes the camera's own shape, so the tee lines up with the picture edge to edge
  const [ar, setAr] = useState(4 / 3);

  useEffect(() => {
    let dead = false;
    (async () => {
      try {
        const { TryOn } = await import("@/lib/tryon/engine");
        if (dead || !video.current || !frame.current || !cv.current || !arms.current) return;
        const e = new TryOn(video.current, frame.current, cv.current, arms.current, (s) => !dead && setStatus(s));
        eng.current = e;
        await e.start(design, DESIGNS[design].colour ?? tee, "M");
      } catch (x) {
        if (dead) return;
        const name = (x as { name?: string })?.name;
        setErr(name === "NotAllowedError" ? "the camera is blocked for this site. allow it in the address bar and try again."
          : name === "NotFoundError" ? "no camera found on this device."
          : "the try-on couldn't start on this browser.");
      }
    })();
    const onResize = () => eng.current?.resize();
    const ro = new ResizeObserver(onResize); if (cv.current) ro.observe(cv.current);
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    addEventListener("resize", onResize); addEventListener("keydown", onKey);
    const html = document.documentElement, prev = html.style.overflow; html.style.overflow = "hidden";
    return () => {
      dead = true; ro.disconnect(); eng.current?.dispose(); eng.current = null;
      removeEventListener("resize", onResize); removeEventListener("keydown", onKey); html.style.overflow = prev;
    };
    // the session starts once; switching designs goes through setLook
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => () => { if (shot) URL.revokeObjectURL(shot.url); }, [shot]);

  const pick = (d: Design) => { setLook(d); eng.current?.setLook(d, DESIGNS[d].colour); };
  const show = (b: Blob, video: boolean) => setShot({ url: URL.createObjectURL(b), blob: b, video });
  const snap = async () => { const b = await eng.current?.snapshot().catch(() => null); if (b) show(b, false); };
  const stop = async () => { setRec(null); const b = await eng.current?.recordStop(); if (b && b.size) show(b, true); };
  const record = () => { if (rec !== null) { stop(); return; } if (eng.current?.recordStart()) { setRec(performance.now()); setNow(performance.now()); } };
  // the clock while recording, and a clip is at most 30 seconds
  useEffect(() => {
    if (rec === null) return;
    const id = setInterval(() => { const t = performance.now(); setNow(t); if (t - rec > 30_000) stop(); }, 250);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rec]);
  const ext = (b: Blob) => (b.type.includes("mp4") ? "mp4" : b.type.includes("webm") ? "webm" : "jpg");
  const file = (b: Blob) => new File([b], `still-breathing-${look}.${ext(b)}`, { type: b.type });
  const canShare = (b: Blob) => typeof navigator !== "undefined" && !!navigator.canShare?.({ files: [file(b)] });
  const share = (b: Blob) => navigator.share({ files: [file(b)] }).catch(() => {});

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black text-white" role="dialog" aria-modal aria-label="Try it on">
      <div className="relative min-h-0 flex-1 overflow-hidden">
        {/* the preview is a mirror, like any selfie camera: the video is flipped, the tee is placed in the
            mirror but not flipped itself, so its print reads the right way round */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="relative" style={{ aspectRatio: ar, width: `min(100%, calc((100dvh - 64px) * ${ar}))` }}>
            <video ref={video} playsInline muted className="absolute inset-0 h-full w-full -scale-x-100"
              onLoadedMetadata={(e) => { const v = e.currentTarget; if (v.videoWidth && v.videoHeight) setAr(v.videoWidth / v.videoHeight); }} />
            {/* the camera frame the pose was read from, shown in the same instant as the tee on it */}
            <canvas ref={frame} className="absolute inset-0 h-full w-full -scale-x-100" />
            {/* a breath of softness so the tee sits in the webcam's own focus */}
            <canvas ref={cv} className="absolute inset-0 h-full w-full" style={{ filter: "blur(0.35px)" }} />
            <canvas ref={arms} className="absolute inset-0 h-full w-full -scale-x-100" />
          </div>
        </div>
        {err || SAY[status] ? (
          <p className="pointer-events-none absolute inset-x-0 bottom-6 mx-auto w-fit max-w-[90%] rounded bg-black/60 px-3 py-1.5 text-center text-[14px]">{err || SAY[status]}</p>
        ) : null}
      </div>
      <div className="flex flex-wrap items-baseline gap-x-5 gap-y-2 px-4 py-3 text-[14px]">
        {(Object.keys(DESIGNS) as Design[]).map((d) => (
          <button key={d} onClick={() => pick(d)} className={`hit ${d === look ? "font-semibold" : "text-white/60 hover:text-white"}`}>
            {DESIGNS[d].no} {DESIGNS[d].name}
          </button>
        ))}
        <span className="flex gap-3" role="group" aria-label="Size">
          {SIZE_ORDER.map((z) => (
            <button key={z} onClick={() => { setSize(z); eng.current?.setSize(z); }} className={`hit ${z === size ? "font-semibold" : "text-white/60 hover:text-white"}`}>{z}</button>
          ))}
        </span>
        <span className="hidden text-white/50 lg:inline">on this device only, nothing is recorded or sent</span>
        <button onClick={snap} disabled={status !== "ready" || rec !== null} className="hit ml-auto font-semibold disabled:text-white/40">take a photo</button>
        <button onClick={record} disabled={status !== "ready"} className="hit font-semibold tabular-nums disabled:text-white/40" aria-pressed={rec !== null}>
          {rec === null ? "record" : <><span className="mr-1.5 inline-block size-2 rounded-full bg-red-500 align-middle" />stop {Math.floor((now - rec) / 1000)}s</>}
        </button>
        <button onClick={onClose} className="hit text-white/70 hover:text-white">close</button>
      </div>
      {shot ? (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/85 p-4" onClick={() => setShot(null)}>
          <div className="flex max-h-full flex-col items-center gap-3" onClick={(e) => e.stopPropagation()}>
            {shot.video ? (
              <video src={shot.url} autoPlay loop playsInline muted controls className="max-h-[80vh] w-auto max-w-full" />
            ) : (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={shot.url} alt="You in the tee" className="max-h-[80vh] w-auto max-w-full" />
            )}
            <div className="flex gap-6">
              {canShare(shot.blob) ? <button onClick={() => share(shot.blob)} className="font-semibold hover:text-white/70">share</button> : null}
              <a href={shot.url} download={`still-breathing-${look}.${ext(shot.blob)}`} className="font-semibold hover:text-white/70">save</a>
              <button onClick={() => setShot(null)} className="text-white/70 hover:text-white">back</button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
