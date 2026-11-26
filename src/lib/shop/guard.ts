import { NextResponse } from "next/server";
import { kvKeys } from "./config";
import { ShopError } from "./errors";
import { kv } from "./kv";

/**
 * What every shop write checks first: it comes from our own pages (same origin, so another site can't act with a
 * visitor's browser), it's a small JSON body, and this IP hasn't gone over its rate.
 */

/** the visitor's IP. Behind Cloudflare (sahn.in) Vercel's own x-real-ip is Cloudflare's edge; the visitor is in
 *  cf-connecting-ip. A client that skips Cloudflare could set that header itself, but only earns its own bucket. */
export const clientIp = (h: Headers) =>
  h.get("cf-connecting-ip")?.trim() || h.get("x-real-ip")?.trim() || h.get("x-forwarded-for")?.split(",")[0]?.trim() || null;
export const ipOf = (req: Request) => clientIp(req.headers) ?? "?";

/** in this instance's memory: the fallback when the store can't be reached, so a limit always holds */
const hits = new Map<string, number[]>();
function local(key: string, max: number, windowMs: number) {
  const now = Date.now();
  const list = (hits.get(key) ?? []).filter((t) => now - t < windowMs);
  const over = list.length >= max;
  if (!over) list.push(now);
  hits.set(key, list);
  if (hits.size > 5000) for (const [k, v] of hits) if (!v.length || now - v[v.length - 1] > windowMs) hits.delete(k);
  return over;
}

/** true when `key` has been used more than `max` times in this window, across every server instance */
export async function limited(key: string, max: number, windowMs: number) {
  if (!kvKeys()) return local(key, max, windowMs);
  const slot = Math.floor(Date.now() / windowMs);
  try {
    const n = await kv<number>("INCR", `rl:${key}:${slot}`);
    if (n === 1) await kv("PEXPIRE", `rl:${key}:${slot}`, windowMs);
    return n > max;
  } catch {
    return local(key, max, windowMs);
  }
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

const NO_STORE = { "Cache-Control": "no-store" };
export const json = (body: unknown, status = 200) => NextResponse.json(body, { status, headers: NO_STORE });

/** the checks for a write; returns the parsed body, or the answer to send back when a check fails */
export async function guardWrite(req: Request, name: string, max = 20, windowMs = 60_000, maxBytes = 4000): Promise<{ body: unknown } | { fail: Response }> {
  if (!sameOrigin(req)) return { fail: json({ error: "not from this site" }, 403) };
  if (await limited(`${name}:${ipOf(req)}`, max, windowMs)) return { fail: json({ error: "too many tries, wait a minute" }, 429) };
  if (!req.headers.get("content-type")?.startsWith("application/json")) return { fail: json({ error: "json only" }, 415) };
  const text = await req.text();
  if (text.length > maxBytes) return { fail: json({ error: "too big" }, 413) };
  try {
    return { body: JSON.parse(text) };
  } catch {
    return { fail: json({ error: "bad json" }, 400) };
  }
}

/** a shop error as an answer the page can show; anything unexpected is logged and kept vague */
export function failed(e: unknown) {
  if (e instanceof ShopError && e.status >= 500 && e.status !== 503) console.error("shop:", e.message);
  if (e instanceof ShopError) return json({ error: e.status >= 500 && e.status !== 503 ? "something didn't answer, try again" : e.message }, e.status);
  console.error("shop:", e);
  return json({ error: "something went wrong, try again" }, 500);
}
