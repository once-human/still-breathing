/** "iPhone, Safari" from a user agent: enough to tell devices apart, nothing more. */
export function deviceName(ua: string | null | undefined): string {
  const s = ua ?? "";
  const device = /iPhone/.test(s) ? "iPhone" : /iPad/.test(s) ? "iPad" : /Android/.test(s) ? "Android" : /Mac OS X/.test(s) ? "Mac" : /Windows/.test(s) ? "Windows" : /CrOS/.test(s) ? "Chromebook" : /Linux/.test(s) ? "Linux" : /curl|Wget|HTTPie|xh\//i.test(s) ? "Terminal" : "Unknown device";
  const browser = /curl\//i.test(s)
    ? "curl"
    : /Edg\//.test(s)
      ? "Edge"
      : /SamsungBrowser/.test(s)
        ? "Samsung Internet"
        : /Instagram/.test(s)
          ? "Instagram"
          : /CriOS|Chrome\//.test(s)
            ? "Chrome"
            : /FxiOS|Firefox\//.test(s)
              ? "Firefox"
              : /Safari\//.test(s)
                ? "Safari"
                : "";
  return browser && device !== "Terminal" ? `${device}, ${browser}` : browser || device;
}

/** Where a request comes from, city level only, from the headers Vercel adds. */
export function geoOf(req: Request) {
  const h = req.headers;
  let city = h.get("x-vercel-ip-city");
  try {
    city = city ? decodeURIComponent(city) : null;
  } catch {
    /* keep as sent */
  }
  return {
    city: city?.replace(/[<>]/g, "").slice(0, 60) || null,
    region: h.get("x-vercel-ip-country-region")?.slice(0, 8) || null,
    country: h.get("x-vercel-ip-country")?.slice(0, 2) || null,
  };
}

const regions = typeof Intl !== "undefined" && "DisplayNames" in Intl ? new Intl.DisplayNames(["en"], { type: "region" }) : null;

/** "Pune, India", or just the country, or "somewhere". */
export function placeName(city: string | null | undefined, country: string | null | undefined): string {
  let c = country ?? null;
  try {
    c = country ? (regions?.of(country) ?? country) : null;
  } catch {
    /* unknown code */
  }
  if (city && c) return `${city}, ${c}`;
  return city || c || "somewhere";
}

/** "Android, Chrome, near Pune, India": who asked, for the sign-in emails (from the request's own headers, kept nowhere) */
export function askedFrom(req: Request): string {
  const g = geoOf(req);
  const where = placeName(g.city, g.country);
  return `${deviceName(req.headers.get("user-agent"))}${where === "somewhere" ? "" : `, near ${where}`}`;
}
