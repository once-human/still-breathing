"use client";

import { useEffect, useState } from "react";
import { STEP_WORD, span, type EventRow, type VisitRow } from "@/lib/visits/shared";
import { browserSaysOff, setTracking, trackingOff, visitorCode } from "@/lib/visits/client";

type Mine = { visits: (VisitRow & { events: EventRow[] })[] };

const when = (iso: string) => new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" }).toLowerCase();

/**
 * "Your visit", on the privacy page: everything the site has kept about this browser, read back with the browser's
 * own code; an off switch; and forget-me, which deletes it all at once.
 */
export function YourVisit() {
  const [state, setState] = useState<"loading" | "off" | "browser" | "on">("loading");
  const [mine, setMine] = useState<Mine | null>(null);
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState("");

  const load = async () => {
    const code = visitorCode(false);
    if (!code) return setMine({ visits: [] });
    const r = await fetch("/api/track", { headers: { "x-visitor": code }, cache: "no-store" }).catch(() => null);
    setMine(r?.ok ? ((await r.json()) as Mine) : { visits: [] });
  };
  useEffect(() => {
    setState(browserSaysOff() ? "browser" : trackingOff() ? "off" : "on");
    void load();
  }, []);

  const forget = async (thenOff: boolean) => {
    setBusy(true);
    const code = visitorCode(false);
    let n = 0;
    if (code) {
      const r = await fetch("/api/track", { method: "DELETE", headers: { "x-visitor": code } }).catch(() => null);
      n = r?.ok ? ((await r.json()) as { deleted: number }).deleted : 0;
    }
    // off forgets the code; on again starts a fresh one, so nothing deleted comes back with the next batch
    setTracking(false);
    if (!thenOff) setTracking(true);
    setState(thenOff ? "off" : "on");
    setMine({ visits: [] });
    setBusy(false);
    setSaid(thenOff ? `turned off, and ${n} visit${n === 1 ? "" : "s"} deleted.` : `${n} visit${n === 1 ? "" : "s"} deleted. a new code starts with your next page.`);
  };
  const turnOn = () => {
    setTracking(true);
    setState("on");
    setSaid("counting again, with a new code.");
  };

  const visits = mine?.visits ?? [];
  const btn = "rounded-full px-4 py-2 text-[13px] font-semibold ring-1 ring-line transition hover:ring-ink disabled:opacity-50";
  return (
    <section aria-labelledby="your-visit" className="rounded-2xl border border-line p-5">
      <h2 id="your-visit" className="text-[15px] font-semibold">your visits, as we have them</h2>
      <p className="mt-1 text-[13px] text-quiet">
        {state === "browser" ? "your browser asks sites not to track it, so nothing is counted here. that stays as long as your browser says so."
          : state === "off" ? "counting is off for this browser. nothing is sent."
          : state === "on" ? "read just now with your browser's own random code. only this browser has it."
          : "reading…"}
      </p>

      {mine && visits.length ? (
        <ul className="mt-4 grid gap-3 text-[13px]">
          {visits.slice(0, 10).map((v) => (
            <li key={v.id} className="border-t border-line pt-3">
              <div className="font-medium">{when(v.startedAt)} · {v.pages} page{v.pages === 1 ? "" : "s"} · {span(v.activeMs)}</div>
              <div className="text-[12px] text-quiet">{[v.city, v.country].filter(Boolean).join(", ") || "somewhere"} · {v.device ?? "a device"} · from {v.referrer ?? "direct"}</div>
              <div className="mt-1 text-[12px] text-quiet">
                {v.events.map((e) => (e.type === "page" ? e.path : e.type === "step" && e.step ? STEP_WORD[e.step] : e.type === "click" ? `link out: ${e.detail ?? ""}` : "")).filter(Boolean).slice(0, 14).join(" → ")}
                {(() => {
                  const n = (t: string) => v.events.filter((e) => e.type === t).length;
                  const more = [[n("tap"), "taps"], [n("seen"), "parts seen"], [n("field"), "form boxes (not what you typed)"], [n("vital"), "speed readings"], [n("error"), "errors"]].filter(([k]) => k);
                  return more.length ? <span className="block text-quiet">also: {more.map(([k, w]) => `${k} ${w}`).join(", ")}</span> : null;
                })()}
              </div>
            </li>
          ))}
          {visits.length > 10 ? <li className="text-[12px] text-quiet">and {visits.length - 10} more</li> : null}
        </ul>
      ) : mine ? <p className="mt-4 text-[13px]">nothing kept about this browser.</p> : null}

      <div className="mt-5 flex flex-wrap gap-2">
        {visits.length ? <button type="button" disabled={busy} onClick={() => void forget(false)} className={btn}>delete all of it</button> : null}
        {state === "on" ? <button type="button" disabled={busy} onClick={() => void forget(true)} className={btn}>turn counting off{visits.length ? " and delete" : ""}</button> : null}
        {state === "off" ? <button type="button" onClick={turnOn} className={btn}>turn counting back on</button> : null}
      </div>
      {said ? <p role="status" className="mt-3 text-[12px] text-quiet">{said}</p> : null}
    </section>
  );
}
