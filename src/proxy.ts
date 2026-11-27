import { NextResponse, type NextFetchEvent, type NextRequest } from "next/server";
import { isBotAgent } from "@/lib/visits/bots";
import { recordBot } from "@/lib/visits/server";

/**
 * Two jobs, each on its own paths (the matcher keeps it off everything else):
 *
 * The admin's front door. Without the admin cookie a page goes to the sign-in page and an API call gets 401 before
 * anything renders. This is the first check, not the only one: every admin page and route checks the session in the
 * database itself. Every admin answer is noindex, never cached, never framed.
 *
 * Programs (crawlers, link previews, curl) don't run the page's JavaScript, so the visitor log sees them here: only
 * requests whose user agent looks like a program (or that have none) reach this, so people's page loads never do.
 */
const COOKIE = process.env.NODE_ENV === "production" ? "__Host-sahn_admin" : "sahn_admin";
const OPEN = ["/admin/login", "/admin/login/confirm", "/api/admin/login"];

export function proxy(req: NextRequest, event: NextFetchEvent) {
  const path = req.nextUrl.pathname.replace(/\/$/, "") || "/";
  if (!(path === "/admin" || path.startsWith("/admin/") || path === "/api/admin" || path.startsWith("/api/admin/"))) {
    if (isBotAgent(req.headers.get("user-agent")) && process.env.DATABASE_URL) event.waitUntil(recordBot(req, path).catch(() => {}));
    return NextResponse.next();
  }
  const has = !!req.cookies.get(COOKIE)?.value;
  let res: NextResponse;
  if (has || OPEN.includes(path)) res = NextResponse.next();
  else if (path.startsWith("/api/")) res = NextResponse.json({ error: "signed out" }, { status: 401 });
  else res = NextResponse.redirect(new URL("/admin/login", req.url));
  res.headers.set("X-Robots-Tag", "noindex, nofollow");
  res.headers.set("Cache-Control", "no-store, private");
  res.headers.set("X-Frame-Options", "DENY");
  res.headers.set("Referrer-Policy", "no-referrer");
  return res;
}

// (These have to be written out: Next reads them before the code runs.)
export const config = {
  matcher: [
    "/admin",
    "/admin/:path*",
    "/api/admin",
    "/api/admin/:path*",
    {
      source: "/((?!api|_next|admin|.*\\..*).*)",
      has: [
        {
          type: "header",
          key: "user-agent",
          value:
            ".*([Bb]ot|[Cc]rawl|[Ss]pider|[Ss]lurp|[Hh]eadless|[Ll]ighthouse|[Pp]age[Ss]peed|facebookexternalhit|meta-externalagent|[Uu]ptime|[Pp]ingdom|curl/|[Ww]get|[Pp]ython|node-fetch|axios|[Gg]o-http|Java/|okhttp|[Pp]hantom|[Pp]uppeteer|[Pp]laywright|[Ss]elenium|WhatsApp/|[Ss]kype|HTTPie|xh/|[Pp]review|[Aa]nthropic|[Pp]erplexity|[Ss]crapy|libwww|[Hh]ttp[Cc]lient|[Hh]ttp-client|[Rr]eqwest|aiohttp|httpx|[Bb]ytespider|[Aa]hrefs|[Ss]emrush|MJ12|[Yy]andex|[Bb]aidu|[Ss]ogou|[Aa]pplebot|ia_archiver|[Mm]onitor|[Ss]canner|[Ff]etcher|[Cc]hecker|[Vv]alidator|\\+http).*",
        },
      ],
    },
    { source: "/((?!api|_next|admin|.*\\..*).*)", missing: [{ type: "header", key: "user-agent" }] },
  ],
};
