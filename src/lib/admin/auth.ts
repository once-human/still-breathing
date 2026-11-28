import "server-only";
import { cache } from "react";
import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { kvKeys, mailKeys } from "@/lib/shop/config";
import { sendEmail } from "@/lib/shop/email";
import { clientIp, limited } from "@/lib/shop/guard";
import { kv } from "@/lib/shop/kv";
import { exec, row } from "./db";

/**
 * Who can get into /admin: whoever has the site key, ADMIN_SECRET in Vercel (the same name the portfolio uses, so
 * one key opens both). The key is typed once; this browser then stays signed in for as long as it keeps coming
 * back, and 30 days without opening the admin ends it. Changing the key ends every session at once.
 *
 * The session is a random token in an httpOnly, Secure, SameSite=Strict __Host- cookie; the database keeps only its
 * hash, with a CSRF token every write must send back, and a tag of the key it was opened with.
 */
const COOKIE = process.env.NODE_ENV === "production" ? "__Host-sahn_admin" : "sahn_admin";
/** days without opening the admin before a session ends */
export const IDLE_DAYS = 30;
/** the cookie itself outlives any idle gap; the database decides when it's over */
const COOKIE_DAYS = 400;

const sha = (s: string) => createHash("sha256").update(s).digest("hex");
const env = (k: string) => process.env[k]?.trim() || undefined;

/** the site key, if it's long enough to be one */
const siteKey = () => {
  const k = env("ADMIN_SECRET");
  return k && k.length >= 16 ? k : null;
};
/** which key a session was opened with: a short tag of its hash, never the key */
const keyTag = (k: string) => `key:${sha(`sahn-admin:${k}`).slice(0, 24)}`;

/** where the sign-in notice goes (ADMIN_EMAIL in Vercel), if anywhere */
export const adminEmail = () => {
  const e = env("ADMIN_EMAIL")?.toLowerCase();
  return e && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e) ? e : null;
};
/** the admin needs the key and the database (sessions live there) */
export const adminReady = () => !!(siteKey() && kvKeys());
/** the name the audit log gives the admin */
const WHO = () => adminEmail() ?? "admin";

const sameText = (a: string, b: string) => {
  const x = createHash("sha256").update(a).digest(), y = createHash("sha256").update(b).digest();
  return timingSafeEqual(x, y);
};

export type Admin = { email: string; csrf: string };

const clock = () => new Date().toLocaleString("en-IN", { hour: "numeric", minute: "2-digit", day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).toLowerCase();

/**
 * Wrong keys, counted (only wrong ones: signing in right never uses one up). Any one connection gets 5 in 15 minutes
 * and 20 a day. All connections together get 200 a day, high enough that someone hammering from one place never
 * shuts you out, and only a spread-out attack from many addresses reaches it; then the sign-in shuts for everyone
 * until 5:30 am (the day's turn in UTC), with an email to ADMIN_EMAIL. The key is 16+ random characters, so even with no limit at
 * all it couldn't be guessed; the limits are so nobody gets to try.
 *
 * Locked out yourself? Two ways to clear every count at once: set ADMIN_UNLOCK in Vercel to anything new and redeploy,
 * or have UNLOCK below bumped by one and pushed. Either changes the counters' names, so they all start from zero.
 */
const UNLOCK = 1;
const lock = () => `${UNLOCK}${env("ADMIN_UNLOCK") ? `.${sha(env("ADMIN_UNLOCK")!).slice(0, 8)}` : ""}`;
const WRONG: [scope: (ip: string) => string, max: number, windowMs: number][] = [
  [(ip) => `admin-wrong:${lock()}:${ip}:15m`, 5, 900_000],
  [(ip) => `admin-wrong:${lock()}:${ip}:day`, 20, 86_400_000],
  [() => `admin-wrong:${lock()}:all:day`, 200, 86_400_000],
];
/** the same counter keys guard.ts's limited() writes, read without adding to them */
const used = async (key: string, windowMs: number) => Number((await kv<string | null>("GET", `rl:${key}:${Math.floor(Date.now() / windowMs)}`).catch(() => null)) ?? 0);
const shut = async (ip: string) => (await Promise.all(WRONG.map(([k, max, w]) => used(k(ip), w).then((n) => n >= max)))).some(Boolean);

/** the key, checked in constant time; right → a session cookie */
export async function signInWithKey(key: string, ip: string, ua: string, from = "") {
  const want = siteKey();
  if (!adminReady() || !want) return "closed" as const;
  if (await shut(ip)) return "slow" as const;
  if (!key || key.length > 200 || !sameText(key, want)) {
    await Promise.all(WRONG.map(([k, max, w]) => limited(k(ip), max, w)));
    await audit("?", "login.refused", null, { why: "wrong key" }, ip);
    const all = await used(WRONG[2][0](ip), WRONG[2][2]);
    const to = adminEmail();
    if (all === WRONG[2][1] && to && mailKeys())
      await sendEmail(to, "sahn admin: sign-in shut for today", `${all} wrong keys were tried at the sahn admin today, the last at ${clock()} from ${from || "a device we couldn't name"}${ip !== "?" ? ` (ip ${ip})` : ""}. the sign-in is shut for everyone until 5:30 am. if it wasn't you, change ADMIN_SECRET in vercel and redeploy.`, `admin-shut-${Math.floor(Date.now() / 86_400_000)}`, "security").catch(() => {});
    return "wrong" as const;
  }
  const session = randomBytes(32).toString("base64url"), csrf = randomBytes(24).toString("base64url");
  await exec(`DELETE FROM admin_sessions WHERE expires_at < now() OR seen_at < now() - interval '${IDLE_DAYS} days'`);
  await exec(`INSERT INTO admin_sessions (hash, email, csrf, expires_at, ua) VALUES ($1, $2, $3, now() + interval '${COOKIE_DAYS} days', $4)`, [sha(session), keyTag(want), csrf, ua.slice(0, 200)]);
  (await cookies()).set(COOKIE, session, { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", maxAge: COOKIE_DAYS * 86400 });
  await audit(WHO(), "login", null, { ua: ua.slice(0, 120) }, ip);
  // a sign-in you didn't make should never go unseen
  const to = adminEmail();
  if (to && mailKeys())
    await sendEmail(
      to,
      "sahn admin: you're signed in",
      `the sahn admin was just opened with the key at ${clock()}, on ${from || "a device we couldn't name"}${ip !== "?" ? ` (ip ${ip})` : ""}.\n\nnot you? change ADMIN_SECRET in vercel and redeploy: every session ends with the old key.`,
      `admin-in-${sha(session).slice(0, 16)}`,
      "security",
    ).catch((e) => console.error("admin sign-in email:", e));
  return "ok" as const;
}

/**
 * The signed-in admin, or null, once per request however many parts of the page ask. Each look marks the session
 * as used, which is what keeps it going; a session opened with an older key no longer counts.
 */
export const currentAdmin = cache(async function currentAdmin(): Promise<Admin | null> {
  const k = siteKey();
  if (!k || !kvKeys()) return null;
  const t = (await cookies()).get(COOKIE)?.value;
  if (!t || t.length > 100) return null;
  const s = await row<{ email: string; csrf: string }>(
    `UPDATE admin_sessions SET seen_at = now() WHERE hash = $1 AND email = $2 AND expires_at > now() AND seen_at > now() - interval '${IDLE_DAYS} days' RETURNING email, csrf`,
    [sha(t), keyTag(k)],
  ).catch(() => null);
  return s ? { email: WHO(), csrf: s.csrf } : null;
});

/** for every /admin page: the admin, or off to the sign-in page */
export async function requireAdmin(): Promise<Admin> {
  const a = await currentAdmin();
  if (!a) redirect("/admin/login");
  return a;
}

export async function signOut(all = false) {
  const jar = await cookies();
  const t = jar.get(COOKIE)?.value;
  const a = await currentAdmin();
  if (all && a) await exec("DELETE FROM admin_sessions");
  else if (t) await exec("DELETE FROM admin_sessions WHERE hash = $1", [sha(t)]).catch(() => {});
  jar.delete(COOKIE);
  if (a) await audit(a.email, all ? "logout.all" : "logout", null, null, await ip());
}

export const ip = async () => clientIp(await headers()) ?? "?";

/** one line in the audit log: who did what to which thing, and when (the database's clock) */
export async function audit(who: string, action: string, target: string | null, detail: unknown, from: string | null = null) {
  await exec("INSERT INTO admin_audit (who, action, target, detail, ip) VALUES ($1, $2, $3, $4::jsonb, $5)", [
    who,
    action,
    target,
    detail === null || detail === undefined ? null : JSON.stringify(detail),
    from,
  ]).catch((e) => console.error("audit:", e));
}

/** the CSRF token checked in constant time */
export const csrfOk = (a: Admin, got: string | null) => !!got && got.length < 100 && sameText(got, a.csrf);
