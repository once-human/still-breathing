import "server-only";
import { createHash, randomBytes } from "node:crypto";
import { DESIGNS } from "@/content/tee";
import { kv } from "@/lib/shop/kv";
import { exec, rows } from "./db";

/**
 * The site's own visit log, first party and cookieless. A visitor is counted by a hash of (today's salt, IP, browser),
 * cut to 16 characters. The salt is random, made fresh each day and deleted after two, so a visitor can't be followed
 * from one day to the next, and no IP or browser string is ever stored. Bots and anyone sending Do Not Track or
 * Global Privacy Control are not counted at all.
 */
export type EventKind = "view" | "bag" | "checkout";
const KINDS: EventKind[] = ["view", "bag", "checkout"];
const BOT = /bot|crawl|spider|slurp|preview|headless|lighthouse|pagespeed|facebookexternalhit|whatsapp|telegram|curl|wget|python|axios|node-fetch|go-http|java\//i;

const IST = 5.5 * 3600_000;
const today = () => new Date(Date.now() + IST).toISOString().slice(0, 10);

let salt: { day: string; value: string } | null = null;
async function daySalt(day: string) {
  if (salt?.day === day) return salt.value;
  await kv("SET", `asalt:${day}`, randomBytes(16).toString("hex"), "NX", "EX", 2 * 86400);
  const v = (await kv<string | null>("GET", `asalt:${day}`)) ?? randomBytes(16).toString("hex");
  salt = { day, value: v };
  return v;
}

const device = (ua: string) => (/ipad|tablet/i.test(ua) ? "tablet" : /mobi|android|iphone/i.test(ua) ? "phone" : "desktop");

/** the referrer's host, or the utm_source, or direct; our own pages don't count as a source */
function source(ref: string, utm: string, self: string) {
  if (utm) return utm.toLowerCase().replace(/[^\w.-]/g, "").slice(0, 40) || null;
  try {
    const h = new URL(ref).hostname.replace(/^www\./, "").replace(/^(l|lm|m)\.facebook\.com$/, "facebook.com").replace(/^l\.instagram\.com$/, "instagram.com");
    return h && h !== self.replace(/^www\./, "") ? h.slice(0, 80) : null;
  } catch {
    return null;
  }
}

const hits = new Map<string, number[]>();
function tooMany(key: string, max: number, windowMs: number) {
  const now = Date.now();
  const l = (hits.get(key) ?? []).filter((t) => now - t < windowMs);
  l.push(now);
  hits.set(key, l);
  if (hits.size > 5000) hits.clear();
  return l.length > max;
}

export async function record(req: Request, body: unknown, ip: string) {
  const h = req.headers;
  const ua = h.get("user-agent") ?? "";
  if (!ua || BOT.test(ua) || h.get("dnt") === "1" || h.get("sec-gpc") === "1") return;
  if (tooMany(ip, 120, 60_000)) return;
  const b = (body ?? {}) as Record<string, unknown>;
  const kind = KINDS.find((k) => k === b.k);
  const path = typeof b.p === "string" && b.p.startsWith("/") ? b.p.split("?")[0].slice(0, 200) : null;
  if (!kind || !path || path.startsWith("/admin") || path.startsWith("/api")) return;
  const day = today();
  const visitor = createHash("sha256").update(`${await daySalt(day)}|${ip}|${ua}`).digest("hex").slice(0, 16);
  const self = h.get("host") ?? "";
  // a shirt's page counts for that shirt; a bag event names its own
  const slug = path.split("/")[2];
  const design = typeof b.d === "string" && /^[a-z0-9-]{1,40}$/.test(b.d) ? b.d : (slug && Object.entries(DESIGNS).find(([, x]) => x.slug === slug)?.[0]) || null;
  const size = typeof b.s === "string" && /^[A-Z0-9]{1,4}$/.test(b.s) ? b.s : null;
  const region = [h.get("x-vercel-ip-country"), h.get("x-vercel-ip-country-region")].filter(Boolean).join("-").slice(0, 12) || null;
  await exec(
    "INSERT INTO events (day, kind, path, ref, source, device, region, visitor, design, size) VALUES ($1::date, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
    [day, kind, path, null, source(String(b.r ?? ""), String(b.u ?? ""), self), device(ua), region, visitor, design, size],
  );
  if (Math.random() < 0.002) exec("DELETE FROM events WHERE day < current_date - 400").catch(() => {});
}

export type DayRow = { day: string; visitors: number; views: number; bags: number; checkouts: number };
export type Count = { key: string | null; views: number; visitors: number };

/** the last `days` days in one go */
export async function activity(days = 30) {
  const since = `current_date - ${Math.max(1, Math.min(400, Math.floor(days))) - 1}`;
  const [perDay, pages, sources, devices, regions, bag, totals] = await Promise.all([
    rows<DayRow>(`SELECT day::text, count(DISTINCT visitor) FILTER (WHERE kind = 'view')::int AS visitors, count(*) FILTER (WHERE kind = 'view')::int AS views,
      count(*) FILTER (WHERE kind = 'bag')::int AS bags, count(DISTINCT visitor) FILTER (WHERE kind = 'checkout')::int AS checkouts
      FROM events WHERE day >= ${since} GROUP BY day ORDER BY day`),
    rows<Count>(`SELECT path AS key, count(*)::int AS views, count(DISTINCT visitor || day)::int AS visitors FROM events WHERE kind = 'view' AND day >= ${since} GROUP BY path ORDER BY views DESC LIMIT 25`),
    rows<Count>(`SELECT coalesce(source, 'direct') AS key, count(*)::int AS views, count(DISTINCT visitor || day)::int AS visitors FROM events WHERE kind = 'view' AND day >= ${since} GROUP BY 1 ORDER BY visitors DESC LIMIT 20`),
    rows<Count>(`SELECT device AS key, count(*)::int AS views, count(DISTINCT visitor || day)::int AS visitors FROM events WHERE kind = 'view' AND day >= ${since} GROUP BY 1 ORDER BY visitors DESC`),
    rows<Count>(`SELECT coalesce(region, '?') AS key, count(*)::int AS views, count(DISTINCT visitor || day)::int AS visitors FROM events WHERE kind = 'view' AND day >= ${since} GROUP BY 1 ORDER BY visitors DESC LIMIT 15`),
    rows<{ design: string; size: string | null; n: number }>(`SELECT design, size, count(*)::int AS n FROM events WHERE kind = 'bag' AND design IS NOT NULL AND day >= ${since} GROUP BY design, size ORDER BY n DESC`),
    rows<{ visitors: number; shirt: number; bag: number; checkout: number }>(`SELECT count(DISTINCT visitor || day) FILTER (WHERE kind = 'view')::int AS visitors,
      count(DISTINCT visitor || day) FILTER (WHERE kind = 'view' AND design IS NOT NULL)::int AS shirt,
      count(DISTINCT visitor || day) FILTER (WHERE kind = 'bag')::int AS bag, count(DISTINCT visitor || day) FILTER (WHERE kind = 'checkout')::int AS checkout
      FROM events WHERE day >= ${since}`),
  ]);
  return { perDay, pages, sources, devices, regions, bag, totals: totals[0] ?? { visitors: 0, shirt: 0, bag: 0, checkout: 0 } };
}
