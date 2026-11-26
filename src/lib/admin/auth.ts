import "server-only";
import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { kvKeys, mailKeys } from "@/lib/shop/config";
import { sendEmail } from "@/lib/shop/email";
import { clientIp, limited } from "@/lib/shop/guard";
import { SITE_URL } from "@/lib/site";
import { exec, row } from "./db";

/**
 * Who can get into /admin: only the one address in ADMIN_EMAIL. No password anywhere: that address asks for a link,
 * the link (one use, 10 minutes) opens a page whose button signs this browser in. Opening the link alone does
 * nothing, so a mail scanner that fetches links can't use it up or sign anyone in.
 *
 * The session is a random token in an httpOnly, Secure, SameSite=Strict __Host- cookie; the database keeps only its
 * hash, with a CSRF token every write must send back. 12 hours at most, and 2 hours without use ends it.
 */
const COOKIE = process.env.NODE_ENV === "production" ? "__Host-sahn_admin" : "sahn_admin";
const LINK_MIN = 10;
const SESSION_H = 12;
const IDLE_H = 2;

const sha = (s: string) => createHash("sha256").update(s).digest("hex");
const env = (k: string) => process.env[k]?.trim() || undefined;

/** the one address allowed in, lower case; the admin is closed without it */
export const adminEmail = () => {
  const e = env("ADMIN_EMAIL")?.toLowerCase();
  return e && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e) ? e : null;
};
/** the admin needs the database (sessions live there) and email (the link goes by it) */
export const adminReady = () => !!(adminEmail() && kvKeys() && mailKeys());

const sameText = (a: string, b: string) => {
  const x = createHash("sha256").update(a).digest(), y = createHash("sha256").update(b).digest();
  return timingSafeEqual(x, y);
};

const site = () => (env("SHOP_SITE_URL") ?? SITE_URL).replace(/\/$/, "");

export type Admin = { email: string; csrf: string };

/**
 * Ask for a sign-in link. Every answer is the same whatever the email, so the page tells no one which address
 * works. Limits: 5 asks per IP in 15 minutes, and at most 3 links in 15 minutes and 10 a day in all.
 */
export async function requestLink(email: string, ip: string) {
  const want = adminEmail();
  if (!adminReady() || !want) return;
  if (await limited(`admin-ask:${ip}`, 5, 900_000)) return;
  if (!sameText(email.trim().toLowerCase(), want)) return;
  if ((await limited("admin-link:15m", 3, 900_000)) || (await limited("admin-link:day", 10, 86_400_000))) return;
  const token = randomBytes(32).toString("base64url");
  await exec("DELETE FROM admin_tokens WHERE expires_at < now() - interval '1 day'");
  await exec(`INSERT INTO admin_tokens (hash, email, expires_at) VALUES ($1, $2, now() + interval '${LINK_MIN} minutes')`, [sha(token), want]);
  const link = `${site()}/admin/login/confirm#${token}`;
  await sendEmail(
    want,
    "sahn admin: your sign-in link",
    `someone (you, we hope) asked to sign in to the sahn admin${ip !== "?" ? ` from ${ip}` : ""}.\n\nsign in: ${link}\n\nthe link works once, for ${LINK_MIN} minutes, and only after you press the button on the page it opens. if you didn't ask for it, ignore this email: nothing happens without it.`,
    `admin-link-${sha(token).slice(0, 16)}`,
  );
  await audit(want, "login.link", null, null, ip);
}

/** the link's token, used once: right → a new session cookie */
export async function useLink(token: string, ip: string, ua: string) {
  if (!adminReady() || !/^[\w-]{40,50}$/.test(token)) return false;
  if (await limited(`admin-use:${ip}`, 10, 900_000)) return false;
  const t = await row<{ email: string }>(
    "UPDATE admin_tokens SET used_at = now() WHERE hash = $1 AND used_at IS NULL AND expires_at > now() RETURNING email",
    [sha(token)],
  );
  if (!t || t.email !== adminEmail()) {
    await audit("?", "login.refused", null, { why: t ? "address changed" : "bad or used link" }, ip);
    return false;
  }
  const session = randomBytes(32).toString("base64url"), csrf = randomBytes(24).toString("base64url");
  await exec("DELETE FROM admin_sessions WHERE expires_at < now() OR seen_at < now() - interval '1 day'");
  await exec(`INSERT INTO admin_sessions (hash, email, csrf, expires_at, ua) VALUES ($1, $2, $3, now() + interval '${SESSION_H} hours', $4)`, [sha(session), t.email, csrf, ua.slice(0, 200)]);
  (await cookies()).set(COOKIE, session, { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", maxAge: SESSION_H * 3600 });
  await audit(t.email, "login", null, { ua: ua.slice(0, 120) }, ip);
  return true;
}

/** the signed-in admin, or null. Checks the session in the database on every call, and that it's still the allowed address. */
export async function currentAdmin(): Promise<Admin | null> {
  if (!adminReady()) return null;
  const t = (await cookies()).get(COOKIE)?.value;
  if (!t || t.length > 100) return null;
  const s = await row<{ email: string; csrf: string }>(
    `UPDATE admin_sessions SET seen_at = now() WHERE hash = $1 AND expires_at > now() AND seen_at > now() - interval '${IDLE_H} hours' RETURNING email, csrf`,
    [sha(t)],
  ).catch(() => null);
  return s && s.email === adminEmail() ? s : null;
}

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
  if (all && a) await exec("DELETE FROM admin_sessions WHERE email = $1", [a.email]);
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
