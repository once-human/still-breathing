import { NextResponse } from "next/server";
import { ShopError } from "./storefront";

/**
 * What every shop write route checks before it does anything: the request comes from our own pages (same origin,
 * so another site can't add to a visitor's bag with their cookie), it is a small JSON body, and this IP hasn't
 * gone over its rate.
 */

/** A sliding window per key, in this server's memory. Vercel keeps warm instances for many requests, so it stops a
 *  burst; the Vercel firewall rule in the checklist is the limit across all instances. */
const hits = new Map<string, number[]>();
export function limited(key: string, max: number, windowMs: number) {
  const now = Date.now();
  const list = (hits.get(key) ?? []).filter((t) => now - t < windowMs);
  const over = list.length >= max;
  if (!over) list.push(now);
  hits.set(key, list);
  if (hits.size > 5000) for (const [k, v] of hits) if (!v.length || now - v[v.length - 1] > windowMs) hits.delete(k);
  return over;
}

export function sameOrigin(req: Request) {
  const origin = req.headers.get("origin");
  if (!origin) return req.headers.get("sec-fetch-site") === "same-origin";
  try {
    return new URL(origin).host === (req.headers.get("x-forwarded-host") ?? req.headers.get("host"));
  } catch {
    return false;
  }
}

export const ipOf = (req: Request) => req.headers.get("x-real-ip") ?? req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "?";

const NO_STORE = { "Cache-Control": "no-store" };
export const json = (body: unknown, status = 200) => NextResponse.json(body, { status, headers: NO_STORE });

/** the checks for a write; returns a response to send back when one fails */
export async function guardWrite(req: Request, name: string, max = 20, windowMs = 60_000): Promise<{ body: unknown } | { fail: Response }> {
  if (!sameOrigin(req)) return { fail: json({ error: "not from this site" }, 403) };
  if (limited(`${name}:${ipOf(req)}`, max, windowMs)) return { fail: json({ error: "too many tries, wait a minute" }, 429) };
  if (!req.headers.get("content-type")?.startsWith("application/json")) return { fail: json({ error: "json only" }, 415) };
  const text = await req.text();
  if (text.length > 2000) return { fail: json({ error: "too big" }, 413) };
  try {
    return { body: JSON.parse(text) };
  } catch {
    return { fail: json({ error: "bad json" }, 400) };
  }
}

/** a shop error as an answer the page can show; anything else is logged and kept vague */
export function failed(e: unknown) {
  if (e instanceof ShopError && e.status >= 500 && e.status !== 503) console.error("shop:", e.message);
  if (e instanceof ShopError) return json({ error: e.status >= 500 && e.status !== 503 ? "the shop didn't answer, try again" : e.message }, e.status);
  console.error("shop:", e);
  return json({ error: "something went wrong, try again" }, 500);
}
