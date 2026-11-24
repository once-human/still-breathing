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
 * Door-to-door hours to a show from inside India, the way people actually go: by road when it's close (roads wind
 * about 1.3x the straight line, at about 55 km/h with stops), by air when it's far (about 3.5 h of getting to the
 * airport, waiting and getting into the city, plus the flight at about 750 km/h). Whichever is quicker.
 */
const KM_PER_DEG = 111.2;
const hours = (km: number) => Math.min((km * 1.3) / 55, 3.5 + km / 750);

/**
 * From abroad it's a flight into one of the two international gateways on the tour, Mumbai or Bengaluru (Delhi NCR
 * is one night only, and far from most of the city's own crowd). Long-haul hours: about 4 h at both ends plus the
 * flight at about 820 km/h, and an extra 3 h for a connection when the trip is long. Mumbai has the most direct
 * routes from abroad (the Gulf, Europe, North America, Africa), so from the west, past the Gulf, it's an hour quicker in practice;
 * from the east (Singapore, Malaysia, Thailand, Sri Lanka, the Maldives, Australia) Bengaluru is simply closer.
 */
const GATEWAYS = ["mumbai", "bengaluru"];
// (west of India: lon under 70)
const abroad = (city: string, km: number, lon: number) => 4 + km / 820 + (km > 6000 ? 3 : 0) - (city === "mumbai" && km > 2500 && lon < 70 ? 1 : 0);

const kmTo = (city: string, lat: number, lon: number) => {
  const [a, b] = WHERE[city];
  // equirectangular distance is plenty at this scale
  return KM_PER_DEG * Math.hypot(a - lat, (b - lon) * Math.cos(((a + lat) / 2) * (Math.PI / 180)));
};

export function GET(req: Request) {
  const lat = round(req.headers.get("x-vercel-ip-latitude")), lon = round(req.headers.get("x-vercel-ip-longitude"));
  const country = req.headers.get("x-vercel-ip-country");
  let city: string | null = null;
  if (lat !== null && lon !== null) {
    const home = !country || country === "IN";
    let best = Infinity;
    for (const s of SHOWS) {
      if (!home && !GATEWAYS.includes(s.city)) continue;
      const km = kmTo(s.city, lat, lon);
      // the cities with two nights are easier to make: a quarter hour's grace a night
      const h = (home ? hours(km) : abroad(s.city, km, lon)) - s.days.length * 0.25;
      if (h < best) { best = h; city = s.city; }
    }
  }
  return Response.json({ city }, { headers: { "Cache-Control": "private, no-store" } });
}
