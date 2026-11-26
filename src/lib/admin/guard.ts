import "server-only";
import { NextResponse } from "next/server";
import { ipOf, limited, sameOrigin } from "@/lib/shop/guard";
import { audit, csrfOk, currentAdmin, type Admin } from "./auth";

const NO_STORE = { "Cache-Control": "no-store, private", "X-Robots-Tag": "noindex" };
export const ok = (body: unknown, status = 200) => NextResponse.json(body, { status, headers: NO_STORE });

/**
 * Every /api/admin write: same origin, a signed-in admin (checked in the database), the session's CSRF token in
 * x-csrf, a JSON body under maxBytes, 60 writes a minute. Returns the admin and the body, or the answer to send.
 */
export async function adminWrite(req: Request, maxBytes = 20_000): Promise<{ admin: Admin; body: Record<string, unknown>; ip: string } | { fail: Response }> {
  if (!sameOrigin(req)) return { fail: ok({ error: "not from this site" }, 403) };
  const admin = await currentAdmin();
  if (!admin) return { fail: ok({ error: "signed out: sign in again" }, 401) };
  if (!csrfOk(admin, req.headers.get("x-csrf"))) return { fail: ok({ error: "the page is stale: reload it" }, 403) };
  const ip = ipOf(req);
  if (await limited(`admin-write:${admin.email}`, 60, 60_000)) return { fail: ok({ error: "too many at once, wait a minute" }, 429) };
  if (!req.headers.get("content-type")?.startsWith("application/json")) return { fail: ok({ error: "json only" }, 415) };
  const text = await req.text();
  if (text.length > maxBytes) return { fail: ok({ error: "too big" }, 413) };
  try {
    const body = JSON.parse(text);
    if (!body || typeof body !== "object" || Array.isArray(body)) throw new Error();
    return { admin, body, ip };
  } catch {
    return { fail: ok({ error: "bad json" }, 400) };
  }
}

/** a read route: a signed-in admin, or 401 */
export async function adminRead(): Promise<{ admin: Admin } | { fail: Response }> {
  const admin = await currentAdmin();
  return admin ? { admin } : { fail: ok({ error: "signed out" }, 401) };
}

/** an action that failed, logged with what was tried, and said plainly */
export async function failedAction(admin: Admin, action: string, target: string | null, e: unknown, ip: string) {
  const msg = e instanceof Error ? e.message : String(e);
  await audit(admin.email, `${action}.failed`, target, { error: msg.slice(0, 300) }, ip);
  return ok({ error: msg.slice(0, 300) }, (e as { status?: number })?.status && (e as { status: number }).status < 600 ? (e as { status: number }).status : 500);
}

export const str = (v: unknown, max = 500) => (typeof v === "string" ? v.trim().slice(0, max) : "");
