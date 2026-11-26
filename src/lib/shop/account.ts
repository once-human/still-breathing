import { createHash, createHmac, randomBytes, randomInt, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import { accountsOpen, shopSecret } from "./config";
import { sendEmail } from "./email";
import { ShopError } from "./errors";
import { getJson, kv, setJson } from "./kv";
import type { Details } from "./india";

/**
 * Accounts with no password: an email gets a 6-digit code (10 minutes, 5 tries, at most 3 codes per 15 minutes),
 * the code opens a 30-day session. The session is a random token in an httpOnly cookie; the store keeps only its
 * hash. An account is its email: every order placed with that email is in it, whenever it was placed.
 */
const COOKIE = process.env.NODE_ENV === "production" ? "__Host-sahn_session" : "sahn_session";
const SESSION_DAYS = 30;

export type Address = Omit<Details, "email"> & { id: string };
export type Account = { email: string; name: string; phone: string; addresses: Address[]; createdAt: string };

const sha = (s: string) => createHash("sha256").update(s).digest("hex");
const codeHash = (email: string, code: string) => createHmac("sha256", shopSecret() ?? "").update(`code:${email}:${code}`).digest("hex");
export const validEmail = (e: string) => e.length <= 120 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e);

/** email a sign-in code; quietly does nothing past the limits (the page says the same either way) */
export async function sendCode(email: string) {
  if (!accountsOpen()) throw new ShopError("accounts not set up", 503);
  const sent = await kv<number>("INCR", `otp-sent:${email}`);
  if (sent === 1) await kv("EXPIRE", `otp-sent:${email}`, 900);
  if (sent > 3) return;
  const code = String(randomInt(0, 1_000_000)).padStart(6, "0");
  await setJson(`otp:${email}`, { hash: codeHash(email, code), tries: 0 }, 1);
  await kv("EXPIRE", `otp:${email}`, 600);
  await sendEmail(email, `${code} is your sahn sign-in code`, `your code is ${code}\n\nit works for 10 minutes. if you didn't ask for it, ignore this email: nothing happens without it.\n\nsahn`, `otp-${email}-${sha(code).slice(0, 12)}`);
}

/** the code checked in constant time; right → a new session cookie */
export async function verifyCode(email: string, code: string) {
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
  if (!(await getJson<Account>(`user:${email}`))) await setJson(`user:${email}`, { email, name: "", phone: "", addresses: [], createdAt: new Date().toISOString() } satisfies Account, 3650);
  (await cookies()).set(COOKIE, token, { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: SESSION_DAYS * 86400 });
  return true;
}

/** the signed-in email, or null */
export async function sessionEmail(): Promise<string | null> {
  if (!accountsOpen()) return null;
  const t = (await cookies()).get(COOKIE)?.value;
  if (!t || t.length > 100) return null;
  return (await kv<string | null>("GET", `sess:${sha(t)}`).catch(() => null)) ?? null;
}

export async function signOut() {
  const jar = await cookies();
  const t = jar.get(COOKIE)?.value;
  if (t) await kv("DEL", `sess:${sha(t)}`).catch(() => {});
  jar.delete(COOKIE);
}

export const loadAccount = (email: string) => getJson<Account>(`user:${email}`);
export const saveAccount = (a: Account) => setJson(`user:${a.email}`, a, 3650);

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
