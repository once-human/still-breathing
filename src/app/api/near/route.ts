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

/**
 * Door-to-door hours to a show, the way people actually go: by road when it's close (roads wind about 1.3x the
 * straight line, at about 55 km/h with stops), by air when it's far (about 3.5 h of getting to the airport, waiting
 * and getting into the city, plus the flight at about 750 km/h). Whichever is quicker.
 */
const KM_PER_DEG = 111.2;
const hours = (km: number) => Math.min((km * 1.3) / 55, 3.5 + km / 750);

export function GET(req: Request) {
  const lat = round(req.headers.get("x-vercel-ip-latitude")), lon = round(req.headers.get("x-vercel-ip-longitude"));
  let city: string | null = null;
  if (lat !== null && lon !== null) {
    let best = Infinity;
    for (const s of SHOWS) {
      const [a, b] = WHERE[s.city];
      // equirectangular distance is plenty at this scale
      const km = KM_PER_DEG * Math.hypot(a - lat, (b - lon) * Math.cos(((a + lat) / 2) * (Math.PI / 180)));
      // the cities with two nights are easier to make: half an hour's grace
      const h = hours(km) - s.days.length * 0.25;
      if (h < best) { best = h; city = s.city; }
    }
  }
  return Response.json({ city }, { headers: { "Cache-Control": "private, no-store" } });
}
