import { NextResponse, type NextRequest } from "next/server";

/**
 * The admin's front door, and only that (the matcher keeps it off every other page). Without the admin cookie a page
 * goes to the sign-in page and an API call gets 401 before anything renders. This is the first check, not the only
 * one: every admin page and route checks the session in the database itself. Every admin answer is noindex, never
 * cached, never framed.
 */
const COOKIE = process.env.NODE_ENV === "production" ? "__Host-sahn_admin" : "sahn_admin";
const OPEN = ["/admin/login", "/admin/login/confirm", "/api/admin/login"];

export function proxy(req: NextRequest) {
  const path = req.nextUrl.pathname.replace(/\/$/, "") || "/";
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

export const config = { matcher: ["/admin", "/admin/:path*", "/api/admin", "/api/admin/:path*"] };
