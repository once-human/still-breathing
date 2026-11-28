import "server-only";
import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import { SITE_URL } from "@/lib/site";
import { googleKeys } from "./config";

/**
 * Sign in with Google: the standard OAuth code flow with PKCE. The start sends the buyer to Google with a random
 * state and a code challenge, both kept in a short httpOnly cookie; Google sends them back with a code, which the
 * server trades for an ID token straight from Google's token endpoint (so it comes from Google itself), checked for
 * this site's client, Google as the issuer, not expired, and a verified email. Only the email and name are used.
 */
const COOKIE = process.env.NODE_ENV === "production" ? "__Host-sahn_g" : "sahn_g";
const site = () => (process.env.SHOP_SITE_URL?.trim() || SITE_URL).replace(/\/$/, "");
export const googleRedirect = () => `${site()}/api/shop/auth/google/callback`;
const b64 = (b: Buffer) => b.toString("base64url");

/** where to send the buyer to choose their Google account */
export async function googleStart(next: string | null) {
  const k = googleKeys();
  if (!k) return null;
  const state = b64(randomBytes(24)), verifier = b64(randomBytes(32));
  const challenge = b64(createHash("sha256").update(verifier).digest());
  (await cookies()).set(COOKIE, JSON.stringify({ state, verifier, next }), {
    httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: 600,
  });
  const u = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  u.search = new URLSearchParams({
    client_id: k.id, redirect_uri: googleRedirect(), response_type: "code", scope: "openid email profile",
    state, code_challenge: challenge, code_challenge_method: "S256", prompt: "select_account",
  }).toString();
  return u.toString();
}

const same = (a: string, b: string) => {
  const x = createHash("sha256").update(a).digest(), y = createHash("sha256").update(b).digest();
  return timingSafeEqual(x, y);
};

/** Google's answer → the verified email and name, and where to go next; null for anything off */
export async function googleFinish(params: URLSearchParams): Promise<{ email: string; name: string; next: string | null } | null> {
  const k = googleKeys();
  const jar = await cookies();
  const raw = jar.get(COOKIE)?.value;
  jar.delete(COOKIE);
  if (!k || !raw) return null;
  let saved: { state?: string; verifier?: string; next?: string | null };
  try { saved = JSON.parse(raw); } catch { return null; }
  const code = params.get("code"), state = params.get("state");
  if (!code || !state || !saved.state || !saved.verifier || !same(state, saved.state)) return null;
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ code, client_id: k.id, client_secret: k.secret, redirect_uri: googleRedirect(), grant_type: "authorization_code", code_verifier: saved.verifier }),
    cache: "no-store",
    signal: AbortSignal.timeout(8000),
  }).catch(() => null);
  const j = r?.ok ? ((await r.json().catch(() => null)) as { id_token?: string } | null) : null;
  const part = j?.id_token?.split(".")[1];
  if (!part) return null;
  let t: { aud?: string; iss?: string; exp?: number; email?: string; email_verified?: boolean; name?: string; given_name?: string };
  try { t = JSON.parse(Buffer.from(part, "base64url").toString()); } catch { return null; }
  if (t.aud !== k.id || !["https://accounts.google.com", "accounts.google.com"].includes(t.iss ?? "") || !t.exp || t.exp * 1000 < Date.now()) return null;
  if (!t.email || t.email_verified !== true) return null;
  return { email: t.email.toLowerCase(), name: (t.name ?? t.given_name ?? "").replace(/[\u0000-\u001f<>]/g, " ").trim().slice(0, 80), next: saved.next ?? null };
}
