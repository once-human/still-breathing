import { createHash, createHmac, randomBytes, randomInt, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import { after } from "next/server";
import { cache } from "react";
import { accountsOpen, shopSecret } from "./config";
import { sendEmail } from "./email";
import { ShopError } from "./errors";
import { getJson, kv, query, setJson } from "./kv";
import type { Details } from "./india";

/**
 * Accounts with no password: an email gets a 6-digit code (10 minutes, 5 tries, at most 3 codes per 15 minutes),
 * the code opens a session that lasts as long as the buyer keeps coming back (90 days away ends it). The session is a random token in an httpOnly cookie; the store keeps only its
 * hash. An account is its email: every order placed with that email is in it, whenever it was placed.
 */
const COOKIE = process.env.NODE_ENV === "production" ? "__Host-sahn_session" : "sahn_session";
/** days away before a session ends; each visit starts the count again (at most one write a day) */
const SESSION_DAYS = 90;
/** the cookie outlives any gap; the store decides when the session is over */
const COOKIE_DAYS = 400;

export type Address = Omit<Details, "email"> & { id: string };
export type Account = { email: string; name: string; phone: string; addresses: Address[]; createdAt: string };

const sha = (s: string) => createHash("sha256").update(s).digest("hex");
const codeHash = (email: string, code: string) => createHmac("sha256", shopSecret() ?? "").update(`code:${email}:${code}`).digest("hex");
export const validEmail = (e: string) => e.length <= 120 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e);

/** email a sign-in code; quietly does nothing past the limits (the page says the same either way) */
export async function sendCode(email: string, from = "") {
  if (!accountsOpen()) throw new ShopError("accounts not set up", 503);
  const sent = await kv<number>("INCR", `otp-sent:${email}`);
  if (sent === 1) await kv("EXPIRE", `otp-sent:${email}`, 900);
  if (sent > 3) return;
  const code = String(randomInt(0, 1_000_000)).padStart(6, "0");
  await setJson(`otp:${email}`, { hash: codeHash(email, code), tries: 0 }, 1);
  await kv("EXPIRE", `otp:${email}`, 600);
  await sendEmail(email, `${code} is your sahn sign-in code`, `your code is ${code}\n\nasked at ${new Date().toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" })}${from ? ` from ${from}` : ""}. it works for 10 minutes. if you didn't ask for it, ignore this email: nothing happens without it.\n\nsahn`, `otp-${email}-${sha(code).slice(0, 12)}`);
}

/** the code checked in constant time; right → a new session cookie, and whether the account is new (no name yet) */
export async function verifyCode(email: string, code: string): Promise<false | { fresh: boolean }> {
  if (!accountsOpen()) throw new ShopError("accounts not set up", 503);
  const rec = await getJson<{ hash: string; tries: number }>(`otp:${email}`);
  if (!rec || rec.tries >= 5 || !/^\d{6}$/.test(code)) return false;
  const a = Buffer.from(rec.hash, "hex"), b = Buffer.from(codeHash(email, code), "hex");
  if (a.length !== b.length || !timingSafeEqual(a, b)) {
    rec.tries++;
    await setJson(`otp:${email}`, rec, 1);
    await kv("EXPIRE", `otp:${email}`, 600);
    return false;
  }
  await kv("DEL", `otp:${email}`);
  const token = randomBytes(32).toString("base64url");
  await kv("SET", `sess:${sha(token)}`, email, "EX", SESSION_DAYS * 86400);
  const had = await getJson<Account>(`user:${email}`);
  if (!had) await setJson(`user:${email}`, { email, name: "", phone: "", addresses: [], createdAt: new Date().toISOString() } satisfies Account, 3650);
  (await cookies()).set(COOKIE, token, { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: COOKIE_DAYS * 86400 });
  return { fresh: !had?.name };
}

/** the signed-in email, or null (once per request) */
export const sessionEmail = cache(async function sessionEmail(): Promise<string | null> {
  if (!accountsOpen()) return null;
  const t = (await cookies()).get(COOKIE)?.value;
  if (!t || t.length > 100) return null;
  const key = `sess:${sha(t)}`;
  const r = await query(`SELECT value, (expires_at < now() + interval '${SESSION_DAYS - 1} days')::text FROM kv WHERE key = $1 AND (expires_at IS NULL OR expires_at > now())`, [key]).catch(() => null);
  const email = r?.[0]?.[0];
  if (!email) return null;
  // back again: the 90 days start over (once a day at most, and never holding the page up)
  if (r[0][1] === "true") after(() => query(`UPDATE kv SET expires_at = now() + interval '${SESSION_DAYS} days' WHERE key = $1`, [key]).catch(() => {}));
  return email;
});

export async function signOut() {
  const jar = await cookies();
  const t = jar.get(COOKIE)?.value;
  if (t) await kv("DEL", `sess:${sha(t)}`).catch(() => {});
  jar.delete(COOKIE);
}

export const loadAccount = (email: string) => getJson<Account>(`user:${email}`);
export const saveAccount = (a: Account) => setJson(`user:${a.email}`, a, 3650);

/** every account, newest first, for the admin, with how many orders each email has placed; `q` searches email, name and phone */
export async function listAccounts(opts: { limit?: number; offset?: number; q?: string } = {}): Promise<(Account & { orders: number })[]> {
  const limit = Math.min(Math.max(1, opts.limit ?? 50), 200), offset = Math.max(0, opts.offset ?? 0);
  const q = opts.q?.trim() ? `%${opts.q.trim().slice(0, 80).replace(/[\\%_]/g, (c) => `\\${c}`)}%` : null;
  const rows = await query(
    `SELECT value, (SELECT count(*) FROM zset z WHERE z.key = 'uorders:' || (kv.value::jsonb->>'email'))::text FROM kv
     WHERE key LIKE 'user:%' AND (expires_at IS NULL OR expires_at > now())
       AND ($1::text IS NULL OR value::jsonb->>'email' ILIKE $1 OR value::jsonb->>'name' ILIKE $1 OR value::jsonb->>'phone' ILIKE $1)
     ORDER BY value::jsonb->>'createdAt' DESC OFFSET $2::int LIMIT $3::int`,
    [q, offset, limit],
  );
  return rows.flatMap(([v, n]) => {
    const a = v ? (JSON.parse(v) as Account) : null;
    return a ? [{ ...a, orders: Number(n ?? 0) }] : [];
  });
}

export async function countAccounts() {
  const r = await query("SELECT count(*)::text FROM kv WHERE key LIKE 'user:%' AND (expires_at IS NULL OR expires_at > now())");
  return Number(r[0]?.[0] ?? 0);
}

/** sign an email out on every device (its sessions are kept by token hash, with the email as the value) */
export async function signOutEverywhere(email: string) {
  const r = await query("DELETE FROM kv WHERE key LIKE 'sess:%' AND value = $1 RETURNING key", [email]);
  return r.length;
}

/** an account gone: its details, saved addresses, order list and every session (its orders are the orders' own business) */
export async function deleteAccount(email: string) {
  const sessions = await signOutEverywhere(email);
  await kv("DEL", `user:${email}`);
  await kv("DEL", `uorders:${email}`);
  return { sessions };
}

/** the account's orders, newest first */
export const accountOrders = (email: string) => kv<string[]>("ZREVRANGE", `uorders:${email}`, 0, 99);
export const linkOrder = (email: string, id: string) => kv("ZADD", `uorders:${email}`, Date.now(), id);

/** an address the buyer used, kept on their account (newest first, at most 5, no duplicates) */
export async function rememberAddress(email: string, d: Details) {
  const a = await loadAccount(email);
  if (!a) return;
  const same = (x: Address) => x.address1 === d.address1 && x.pin === d.pin && x.name === d.name;
  const { email: _e, ...rest } = d;
  void _e;
  a.addresses = [{ ...rest, id: randomBytes(4).toString("hex") }, ...a.addresses.filter((x) => !same(x))].slice(0, 5);
  if (!a.name) a.name = d.name;
  if (!a.phone) a.phone = d.phone;
  await saveAccount(a);
}
