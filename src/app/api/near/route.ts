import { SHOWS } from "@/content/tee";

/**
 * Which show is nearest to this visitor, for the shirts that belong to the whole lineup rather than one city.
 * Read from the city-level location Vercel already attaches to every request (no permission prompt, nothing
 * precise): rounded to about 10 km, used once for the distance, never stored or logged, and only the show's
 * city name goes back. Without a location (local dev, private relays) the answer is simply "unknown".
 */
export const dynamic = "force-dynamic";

const WHERE: Record<string, [number, number]> = { "delhi ncr": [28.46, 77.03], mumbai: [18.98, 72.82], bengaluru: [13.06, 77.47] };

const round = (v: string | null) => {
  const n = Number(v);
  return v && Number.isFinite(n) ? Math.round(n * 10) / 10 : null;
};

export function GET(req: Request) {
  const lat = round(req.headers.get("x-vercel-ip-latitude")), lon = round(req.headers.get("x-vercel-ip-longitude"));
  let city: string | null = null;
  if (lat !== null && lon !== null) {
    let best = Infinity;
    for (const s of SHOWS) {
      const [a, b] = WHERE[s.city];
      // equirectangular distance is plenty to pick between three cities
      const d = Math.hypot(a - lat, (b - lon) * Math.cos(((a + lat) / 2) * (Math.PI / 180)));
      if (d < best) { best = d; city = s.city; }
    }
  }
  return Response.json({ city }, { headers: { "Cache-Control": "private, no-store" } });
}
