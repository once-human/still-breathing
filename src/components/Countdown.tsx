"use client";

import { useSyncExternalStore } from "react";
import { SHOWS } from "@/content/tee";

/** Minutes tick; the server renders nothing so the first paint never disagrees with the clock. */
function subscribe(cb: () => void) { const id = setInterval(cb, 30_000); return () => clearInterval(id); }
const now = () => Math.floor(Date.now() / 60_000);
const server = () => 0;

const IST = (d: string) => new Date(`${d}T19:00:00+05:30`).getTime();

export function nextShow(t: number) {
  for (const s of SHOWS) {
    const last = IST(s.days[s.days.length - 1]) + 6 * 3600_000;
    if (t < last) return { ...s, start: IST(s.days[0]) };
  }
  return null;
}

export function Countdown({ short = false }: { short?: boolean }) {
  const m = useSyncExternalStore(subscribe, now, server);
  if (!m) return <span>&nbsp;</span>;
  const t = m * 60_000, s = nextShow(t);
  if (!s) return <span>{short ? "tour done" : "the india shows are done. still breathing."}</span>;
  const left = s.start - t;
  if (left <= 0) return <span>● {s.city} {short ? "tonight" : "is on tonight"}</span>;
  const d = Math.floor(left / 86_400_000), h = Math.floor((left % 86_400_000) / 3_600_000);
  return <span>{s.city} in {d > 0 ? `${d}d ${h}h` : `${h}h ${Math.floor((left % 3_600_000) / 60_000)}m`}</span>;
}
