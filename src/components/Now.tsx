"use client";

import { useEffect, useState } from "react";
import { SHOWS } from "@/content/tee";
import { nextShow } from "@/components/Countdown";
import { Label } from "@/components/Label";

/** Where each show is, for the sky over it. */
const PLACES: Record<string, { lat: number; lon: number; name: string }> = {
  "delhi ncr": { lat: 28.46, lon: 77.03, name: "gurugram" },
  mumbai: { lat: 18.98, lon: 72.82, name: "mahalaxmi" },
  bengaluru: { lat: 12.97, lon: 77.59, name: "bengaluru" },
};

const SKY: [number, string][] = [
  [0, "clear"], [1, "mostly clear"], [2, "some cloud"], [3, "overcast"], [45, "hazy"], [48, "foggy"],
  [51, "drizzle"], [61, "light rain"], [63, "rain"], [65, "heavy rain"], [80, "showers"], [95, "thunder"],
];
const skyWord = (code: number) => [...SKY].reverse().find(([c]) => code >= c)?.[1] ?? "";
const clock = (iso: string) => new Date(iso + "+05:30").toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" }).toLowerCase();

type Weather = {
  current: { temperature_2m: number; weather_code: number; relative_humidity_2m: number };
  daily: { time: string[]; sunset: string[] };
  hourly: { time: string[]; temperature_2m: number[]; weather_code: number[] };
};

/**
 * Now: the page writes this part itself, from the clock and the sky over the next show.
 * No keys, nothing about the visitor leaves the browser: it asks a public forecast for three fixed places.
 */
export function Now() {
  const [t, setT] = useState(0);
  const [w, setW] = useState<Weather | null>(null);
  useEffect(() => { setT(Date.now()); const id = setInterval(() => setT(Date.now()), 60_000); return () => clearInterval(id); }, []);
  const show = t ? nextShow(t) : null;
  const place = show ? PLACES[show.city] : null;

  useEffect(() => {
    if (!place) return;
    const u = `https://api.open-meteo.com/v1/forecast?latitude=${place.lat}&longitude=${place.lon}&current=temperature_2m,weather_code,relative_humidity_2m&hourly=temperature_2m,weather_code&daily=sunset&timezone=Asia%2FKolkata&forecast_days=16`;
    fetch(u).then((r) => r.json()).then(setW).catch(() => setW(null));
  }, [place]);

  if (!t) return <section className="min-h-[9rem] px-4" aria-hidden />;
  if (!show || !place) return null;

  const days = Math.max(0, Math.floor((show.start - t) / 86_400_000));
  const showHour = `${show.days[0]}T21:00`;
  const hi = w?.hourly.time.indexOf(showHour) ?? -1;
  const night = hi >= 0 ? `${Math.round(w!.hourly.temperature_2m[hi])}°, ${skyWord(w!.hourly.weather_code[hi])} at 9 pm` : null;
  const sunset = w?.daily.sunset[0] ? clock(w.daily.sunset[0]) : null;
  const cur = w?.current;

  const line = [
    days === 0 ? `${show.city} is tonight.` : `${days} ${days === 1 ? "day" : "days"} to ${show.city}.`,
    cur ? `it's ${Math.round(cur.temperature_2m)}° and ${skyWord(cur.weather_code)} over ${place.name} right now` : null,
    cur && sunset ? `, and the sun goes down there at ${sunset}.` : cur ? "." : null,
  ].filter(Boolean).join(" ").replace(" ,", ",");

  const cells = [
    { k: "next show", v: show.city, d: show.days.map((d) => d.slice(8, 10)).join(" + ") + " december" },
    cur ? { k: `in ${place.name} now`, v: `${Math.round(cur.temperature_2m)}°, ${skyWord(cur.weather_code)}`, d: `${cur.relative_humidity_2m}% humid` } : null,
    { k: "show night", v: night ?? "too far out to forecast", d: night ? "forecast for the first night" : "the forecast reaches 16 days ahead" },
    sunset ? { k: "sunset there", v: sunset, d: "today" } : null,
  ].filter((x): x is { k: string; v: string; d: string } => !!x);

  return (
    <section className="grid grid-cols-1 gap-x-4 px-4 md:grid-cols-12">
      <div className="md:col-span-10 lg:col-span-10 lg:col-start-2">
        <Label note={`${SHOWS.length} cities, december`}>now</Label>
        <p className="max-w-[46ch] text-[clamp(20px,2.4vw,30px)] leading-[1.15] font-semibold tracking-[-0.02em]">{line}</p>
        <dl className="mt-8 grid grid-cols-2 gap-4 text-[14px] md:grid-cols-4">
          {cells.map((c) => (
            <div key={c.k} className="border-t border-line pt-1.5">
              <dt className="text-quiet">{c.k}</dt>
              <dd className="mt-1"><span className="font-semibold">{c.v}</span><span className="block text-quiet">{c.d}</span></dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
