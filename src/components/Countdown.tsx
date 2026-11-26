"use client";

import { useSyncExternalStore } from "react";
import { SHOWS } from "@/content/tee";
import { useShowCity } from "@/lib/city";

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

/** the show the page is about: the shirt's city (or the nearest to the visitor), else simply the next one */
export function showFor(city: string | null, t: number) {
  const s = city ? SHOWS.find((x) => x.city === city) : null;
  if (!s) return nextShow(t);
  const done = t >= IST(s.days[s.days.length - 1]) + 6 * 3600_000;
  return done ? null : { ...s, start: IST(s.days[0]) };
}

export function Countdown({ short = false }: { short?: boolean }) {
  const m = useSyncExternalStore(subscribe, now, server);
  const city = useShowCity();
  if (!m) return <span>&nbsp;</span>;
  const t = m * 60_000, s = showFor(city, t);
  if (!s) return <span>{city ? (short ? `${city} done` : `${city} has been.`) : short ? "tour done" : "the india shows are done."}</span>;
  const left = s.start - t;
  if (left <= 0) return <span>● {s.city} {short ? "tonight" : "is on tonight"}</span>;
  const d = Math.floor(left / 86_400_000), h = Math.floor((left % 86_400_000) / 3_600_000);
  return <span>{s.city} in {d > 0 ? `${d}d ${h}h` : `${h}h ${Math.floor((left % 3_600_000) / 60_000)}m`}</span>;
}
