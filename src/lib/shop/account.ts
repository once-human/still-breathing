import { createHash, createHmac, randomBytes, randomInt, timingSafeEqual } from "node:crypto";
import { hash as argonHash, verify as argonVerify, type Algorithm } from "@node-rs/argon2";
import { cookies } from "next/headers";
import { after } from "next/server";
import { cache } from "react";
import { accountsOpen, shopSecret } from "./config";
import { sendEmail } from "./email";
import { box } from "@/content/mail";
import { ShopError } from "./errors";
import { ensure, kv, query } from "./kv";
import { DESIGNS, SIZE_ORDER, type Design, type Size } from "@/content/tee";
import type { Details } from "./india";
import { forget, subscribe, subscribed, unsubscribe } from "./drops";
import { SITE_URL } from "@/lib/site";

/**
 * Accounts. An account is its email: every order placed with it is in it, whenever it was placed. Three ways in, the
 * buyer's pick: a 6-digit code by email (10 minutes, 5 tries, at most 3 codes per 15 minutes), a password if they set
 * one (Argon2id), or Google. Any of them opens a session that lasts as long as they keep coming back (90 days away
 * ends it). Everything is in the Neon database: sessions, passwords and activity in their own tables below.
 */
const COOKIE = process.env.NODE_ENV === "production" ? "__Host-sahn_session" : "sahn_session";
/** days away before a session ends; each visit starts the count again */
const SESSION_DAYS = 90;
/** the cookie outlives any gap; the store decides when the session is over */
const COOKIE_DAYS = 400;

export type Address = Omit<Details, "email"> & { id: string };
export type Account = {
  email: string; name: string; phone: string; addresses: Address[]; createdAt: string;
  /** when Google was first used to sign in, and whether the buyer has turned Google sign-in off */
  google?: string; googleOff?: boolean;
};
/** how a session was opened */
export type Way = "code" | "password" | "google";
/** one signed-in device, as the profile lists it */
export type Device = { id: string; device: string; way: Way; at: string; seen: string; current: boolean };
/** one thing the buyer did with their account */
export type Did = { at: string; what: string; detail?: string };
const HINT = "sahn_in";

const sha = (s: string) => createHash("sha256").update(s).digest("hex");
const codeHash = (email: string, code: string) => createHmac("sha256", shopSecret() ?? "").update(`code:${email}:${code}`).digest("hex");
export const validEmail = (e: string) => e.length <= 120 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e);

/**
 * Email a sign-in code; quietly does nothing past the limits (the page says the same either way). The code's HMAC
 * (never the code) waits in user_codes for 10 minutes, with its tries and how many were sent this quarter hour.
 */
export async function sendCode(email: string, from = "") {
  if (!accountsOpen()) throw new ShopError("accounts not set up", 503);
  const code = String(randomInt(0, 1_000_000)).padStart(6, "0");
  // one statement: a new code, unless 3 have gone out in the last 15 minutes
  const r = await db(
    `INSERT INTO user_codes (email, hash, tries, expires_at, sent, window_at) VALUES ($1, $2, 0, now() + interval '10 minutes', 1, now())
     ON CONFLICT (email) DO UPDATE SET
       hash = CASE WHEN user_codes.window_at < now() - interval '15 minutes' OR user_codes.sent < 3 THEN $2 ELSE user_codes.hash END,
       tries = CASE WHEN user_codes.window_at < now() - interval '15 minutes' OR user_codes.sent < 3 THEN 0 ELSE user_codes.tries END,
       expires_at = CASE WHEN user_codes.window_at < now() - interval '15 minutes' OR user_codes.sent < 3 THEN now() + interval '10 minutes' ELSE user_codes.expires_at END,
       sent = CASE WHEN user_codes.window_at < now() - interval '15 minutes' THEN 1 ELSE user_codes.sent + 1 END,
       window_at = CASE WHEN user_codes.window_at < now() - interval '15 minutes' THEN now() ELSE user_codes.window_at END
     RETURNING sent`,
    [email, codeHash(email, code)],
  );
  if (Number(r[0]?.[0] ?? 9) > 3) return;
  await sendEmail(email, `${code} is your sahn sign-in code`, `your code is ${code}\n\nasked at ${new Date().toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" })}${from ? ` from ${from}` : ""}. it works for 10 minutes. if you didn't ask for it, ignore this email: nothing happens without it.`, `otp-${email}-${sha(code).slice(0, 12)}`, "security");
}

/** the code checked in constant time (5 tries); right → a new session cookie, and whether the account is new (no name yet) */
export async function verifyCode(email: string, code: string, device = ""): Promise<false | { fresh: boolean }> {
  if (!accountsOpen()) throw new ShopError("accounts not set up", 503);
  if (!/^\d{6}$/.test(code)) return false;
  const r = await db("UPDATE user_codes SET tries = tries + 1 WHERE email = $1 AND expires_at > now() AND tries < 5 RETURNING hash", [email]);
  const h = r[0]?.[0];
  if (!h) return false;
  const x = Buffer.from(h, "hex"), y = Buffer.from(codeHash(email, code), "hex");
  if (x.length !== y.length || !timingSafeEqual(x, y)) return false;
  await db("UPDATE user_codes SET expires_at = now() WHERE email = $1", [email]);
  return openSession(email, "code", device);
}

/* ---------- the tables (Neon Postgres, beside the shop's own; made the first time they're needed) ---------- */

const SCHEMA = [
  // the account: one row per email
  `CREATE TABLE IF NOT EXISTS users (email text PRIMARY KEY, name text NOT NULL DEFAULT '', phone text NOT NULL DEFAULT '',
     created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), google_at timestamptz, google_off boolean NOT NULL DEFAULT false)`,
  // its saved addresses, in the order they're offered at checkout (0 first)
  `CREATE TABLE IF NOT EXISTS user_addresses (id text NOT NULL, email text NOT NULL REFERENCES users (email) ON DELETE CASCADE, position int NOT NULL,
     name text NOT NULL, phone text NOT NULL, address1 text NOT NULL, address2 text NOT NULL DEFAULT '', city text NOT NULL, state text NOT NULL, pin text NOT NULL,
     PRIMARY KEY (email, id))`,
  // which orders were placed with each email
  "CREATE TABLE IF NOT EXISTS user_orders (email text NOT NULL, order_id text NOT NULL, at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (email, order_id))",
  "CREATE INDEX IF NOT EXISTS user_orders_at ON user_orders (email, at DESC)",
  // the sign-in code waiting for each email: its HMAC, tries, and how many went out this quarter hour
  `CREATE TABLE IF NOT EXISTS user_codes (email text PRIMARY KEY, hash text NOT NULL, tries int NOT NULL DEFAULT 0, expires_at timestamptz NOT NULL,
     sent int NOT NULL DEFAULT 1, window_at timestamptz NOT NULL DEFAULT now())`,
  // one row per signed-in device: the token's hash (never the token), whose it is, which device, how it was opened, when last used
  `CREATE TABLE IF NOT EXISTS user_sessions (hash text PRIMARY KEY, email text NOT NULL, device text NOT NULL DEFAULT '', way text NOT NULL,
     created_at timestamptz NOT NULL DEFAULT now(), seen_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL)`,
  "CREATE INDEX IF NOT EXISTS user_sessions_email ON user_sessions (email)",
  // a password, for those who want one: its Argon2id hash (salt and settings inside), never the password
  "CREATE TABLE IF NOT EXISTS user_passwords (email text PRIMARY KEY, hash text NOT NULL, set_at timestamptz NOT NULL DEFAULT now())",
  // everything the buyer did with their account, for their own activity list
  `CREATE TABLE IF NOT EXISTS user_events (id bigserial PRIMARY KEY, email text NOT NULL, at timestamptz NOT NULL DEFAULT now(), what text NOT NULL, detail text)`,
  "CREATE INDEX IF NOT EXISTS user_events_email ON user_events (email, at DESC)",
  // which browsers' visits belong to whom: written while someone is signed in, so the admin sees a name, not a code
  "CREATE TABLE IF NOT EXISTS visitor_people (visitor text PRIMARY KEY, email text NOT NULL, at timestamptz NOT NULL DEFAULT now())",
  "CREATE INDEX IF NOT EXISTS visitor_people_email ON visitor_people (email)",
  // what the person likes to have set: their size, and whether new drops may be emailed (off until they turn it on, with when)
  `CREATE TABLE IF NOT EXISTS user_prefs (email text PRIMARY KEY, size text, drops boolean NOT NULL DEFAULT false, drops_at timestamptz,
     updated_at timestamptz NOT NULL DEFAULT now())`,
  // shirts they saved for later
  "CREATE TABLE IF NOT EXISTS user_saved (email text NOT NULL, design text NOT NULL, at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (email, design))",
];
/**
 * Accounts kept before these tables (JSON rows in kv) moved across, in one statement each, the first time a server
 * instance reaches them: each kv row is deleted as its table rows are written, so it happens once and loses nothing.
 */
const MOVE = [
  `WITH moved AS (DELETE FROM kv WHERE key LIKE 'user:%' RETURNING value::jsonb AS v),
   u AS (INSERT INTO users (email, name, phone, created_at, google_at, google_off)
         SELECT v->>'email', coalesce(v->>'name', ''), coalesce(v->>'phone', ''), coalesce((v->>'createdAt')::timestamptz, now()), (v->>'google')::timestamptz, coalesce((v->>'googleOff')::boolean, false)
         FROM moved WHERE v->>'email' IS NOT NULL ON CONFLICT (email) DO NOTHING RETURNING email)
   INSERT INTO user_addresses (id, email, position, name, phone, address1, address2, city, state, pin)
   SELECT coalesce(x->>'id', md5(random()::text)), u.email, n - 1, coalesce(x->>'name', ''), coalesce(x->>'phone', ''), coalesce(x->>'address1', ''), coalesce(x->>'address2', ''), coalesce(x->>'city', ''), coalesce(x->>'state', ''), coalesce(x->>'pin', '')
   FROM moved JOIN u ON u.email = moved.v->>'email', jsonb_array_elements(coalesce(moved.v->'addresses', '[]'::jsonb)) WITH ORDINALITY e(x, n)
   ON CONFLICT DO NOTHING`,
  `WITH moved AS (DELETE FROM zset WHERE key LIKE 'uorders:%' RETURNING substr(key, 9) AS email, member, score)
   INSERT INTO user_orders (email, order_id, at) SELECT email, member, to_timestamp(score / 1000) FROM moved ON CONFLICT DO NOTHING`,
];
let ready: Promise<void> | null = null;
const setUp = async () => {
  await ensure(SCHEMA);
  for (const m of MOVE) await query(m);
};
const db = async (text: string, params: (string | number | null)[] = []) => {
  await (ready ??= setUp().catch((e) => { ready = null; throw e; }));
  return query(text, params);
};
/** read-only questions across profiles (the admin's email groups) */
export const accountsRead = db;

/**
 * A new session for `email` on this device: a random token in an httpOnly cookie (the database keeps its SHA-256,
 * with the device and how it was opened), and a plain "signed in" hint cookie with nothing in it, so the header
 * knows to ask for the name. Makes the account if it's new; `fresh` when it has no name yet.
 */
export async function openSession(email: string, way: Way, device: string, name = ""): Promise<{ fresh: boolean }> {
  const token = randomBytes(32).toString("base64url");
  const now = new Date().toISOString();
  await db(`INSERT INTO user_sessions (hash, email, device, way, expires_at) VALUES ($1, $2, $3, $4, now() + interval '${SESSION_DAYS} days')`, [sha(token), email, device.slice(0, 80), way]);
  // the account, made if it's new; a name from Google fills an empty one, never replaces one
  const r = await db(
    `INSERT INTO users (email, name, google_at) VALUES ($1, $2, CASE WHEN $3 = 'google' THEN now() END)
     ON CONFLICT (email) DO UPDATE SET name = CASE WHEN users.name = '' THEN EXCLUDED.name ELSE users.name END,
       google_at = coalesce(users.google_at, EXCLUDED.google_at)
     RETURNING name, (xmax = 0)::text`,
    [email, name.slice(0, 80), way],
  );
  void now;
  const jar = await cookies();
  const prod = process.env.NODE_ENV === "production";
  jar.set(COOKIE, token, { httpOnly: true, secure: prod, sameSite: "lax", path: "/", maxAge: COOKIE_DAYS * 86400 });
  jar.set(HINT, "1", { secure: prod, sameSite: "lax", path: "/", maxAge: COOKIE_DAYS * 86400 });
  await did(email, "signed in", `${device.split(", near")[0]}, ${WAY_WORD[way]}`);
  if (way !== "code") await notice(email, `a new sign-in ${WAY_WORD[way]}`, "someone signed in to your sahn profile.", device);
  return { fresh: !r[0]?.[0] };
}
export const WAY_WORD: Record<Way, string> = { code: "with an email code", password: "with a password", google: "with google" };

/** this device's session hash, if it has one */
const myHash = async () => {
  const t = (await cookies()).get(COOKIE)?.value;
  return t && t.length <= 100 ? sha(t) : null;
};

/**
 * The signed-in email, or null (once per request). Each visit pushes the 90 days on (at most once an hour, after the
 * page is sent). A session from before the tables (kept in kv) is moved across the first time it's seen.
 */
export const sessionEmail = cache(async function sessionEmail(): Promise<string | null> {
  if (!accountsOpen()) return null;
  const h = await myHash();
  if (!h) return null;
  const r = await db(`SELECT email, (seen_at < now() - interval '1 hour')::text FROM user_sessions WHERE hash = $1 AND expires_at > now()`, [h]).catch(() => null);
  if (r?.[0]?.[0]) {
    if (r[0][1] === "true") after(() => db(`UPDATE user_sessions SET seen_at = now(), expires_at = now() + interval '${SESSION_DAYS} days' WHERE hash = $1`, [h]).catch(() => {}));
    return r[0][0];
  }
  const old = await kv<string | null>("GET", `sess:${h}`).catch(() => null);
  if (!old) return null;
  after(async () => {
    await db(`INSERT INTO user_sessions (hash, email, way, expires_at) VALUES ($1, $2, 'code', now() + interval '${SESSION_DAYS} days') ON CONFLICT (hash) DO NOTHING`, [h, old]).catch(() => {});
    await kv("DEL", `sess:${h}`).catch(() => {});
  });
  return old;
});

export async function signOut() {
  const jar = await cookies();
  const h = await myHash();
  if (h) {
    await db("DELETE FROM user_sessions WHERE hash = $1", [h]).catch(() => {});
    await kv("DEL", `sess:${h}`).catch(() => {});
  }
  jar.delete(COOKIE);
  jar.delete(HINT);
}

/** every device signed in to `email`, this one first */
export async function devices(email: string): Promise<Device[]> {
  const me = await myHash();
  const r = await db("SELECT hash, device, way, created_at::text, seen_at::text FROM user_sessions WHERE email = $1 AND expires_at > now() ORDER BY seen_at DESC", [email]);
  return r.map(([h, device, way, at, seen]) => ({ id: (h ?? "").slice(0, 16), device: device || "a device", way: (way ?? "code") as Way, at: at ?? "", seen: seen ?? "", current: h === me }))
    .sort((a, b) => Number(b.current) - Number(a.current));
}

/** sign one of `email`'s devices out, by the id the profile showed */
export async function endDevice(email: string, id: string) {
  if (!/^[0-9a-f]{16}$/.test(id)) return 0;
  return (await db("DELETE FROM user_sessions WHERE email = $1 AND left(hash, 16) = $2 RETURNING hash", [email, id])).length;
}

/** how long ago this device signed in, in ms (a fresh sign-in may set a new password without the old one) */
export async function sessionAge() {
  const h = await myHash();
  const r = h ? await db("SELECT created_at::text FROM user_sessions WHERE hash = $1", [h]).catch(() => null) : null;
  return r?.[0]?.[0] ? Date.now() - Date.parse(r[0][0]) : Infinity;
}

/** how many devices each email is signed in on now (for the admin) */
export async function deviceCounts(email?: string) {
  const r = await db(
    `SELECT email, count(*)::text FROM user_sessions WHERE expires_at > now() AND ($1::text IS NULL OR email = $1) GROUP BY email
     UNION ALL SELECT value, count(*)::text FROM kv WHERE key LIKE 'sess:%' AND (expires_at IS NULL OR expires_at > now()) AND ($1::text IS NULL OR value = $1) GROUP BY value`,
    [email ?? null],
  ).catch(() => []);
  const m = new Map<string, number>();
  for (const [e, n] of r) if (e) m.set(e, (m.get(e) ?? 0) + Number(n));
  return m;
}

/* ---------- size, saved shirts, drop emails ---------- */

export type Prefs = { size: Size | null; drops: boolean; dropsAt: string | null; saved: Design[] };

export async function prefs(email: string): Promise<Prefs> {
  const [p, sv, on] = await Promise.all([
    db("SELECT size FROM user_prefs WHERE email = $1", [email]).catch(() => []),
    db("SELECT design FROM user_saved WHERE email = $1 ORDER BY at DESC", [email]).catch(() => []),
    subscribed(email),
  ]);
  const size = p[0]?.[0];
  return {
    size: size && (SIZE_ORDER as readonly string[]).includes(size) ? (size as Size) : null,
    drops: !!on, dropsAt: on,
    saved: sv.map((r) => r[0] as Design).filter((d) => d in DESIGNS),
  };
}
export const setSize = (email: string, size: Size | null) =>
  db("INSERT INTO user_prefs (email, size) VALUES ($1, $2) ON CONFLICT (email) DO UPDATE SET size = $2, updated_at = now()", [email, size]);
/** new-drop emails on or off: the one list everyone shares, signed in or not (drops.ts) */
export const setDrops = (email: string, on: boolean, source = "profile") => (on ? subscribe(email, source) : unsubscribe(email));
export const saveShirt = (email: string, d: Design, on: boolean) =>
  on ? db("INSERT INTO user_saved (email, design) VALUES ($1, $2) ON CONFLICT DO NOTHING", [email, d]) : db("DELETE FROM user_saved WHERE email = $1 AND design = $2", [email, d]);

/** the shirts this person looked at lately, from their browsers' visits while signed in, newest first */
export async function lookedAt(email: string, limit = 6): Promise<Design[]> {
  const r = await db(
    `SELECT e.design FROM visitor_people vp JOIN visits v ON v.visitor = vp.visitor JOIN visit_events e ON e.visit = v.id
     WHERE vp.email = $1 AND e.design IS NOT NULL GROUP BY e.design ORDER BY max(e.at) DESC LIMIT $2::int`,
    [email, limit],
  ).catch(() => []);
  return r.map((x) => x[0] as Design).filter((d) => d in DESIGNS);
}

/* ---------- visits, by person ---------- */

/** this browser's visit code belongs to `email` (the last person signed in on it wins) */
export const linkVisitor = (visitor: string, email: string) =>
  db("INSERT INTO visitor_people (visitor, email) VALUES ($1, $2) ON CONFLICT (visitor) DO UPDATE SET email = $2, at = now()", [visitor, email]);

/** for the admin: each linked browser by the visits log's person id (the first 12 hex of its code's SHA-256), with the person's email and name */
export async function linkedPeople(email?: string) {
  const r = await db(
    `SELECT left(encode(sha256(convert_to(vp.visitor, 'UTF8')), 'hex'), 12), vp.email, coalesce(u.name, '') FROM visitor_people vp LEFT JOIN users u ON u.email = vp.email
     WHERE $1::text IS NULL OR vp.email = $1`,
    [email ?? null],
  ).catch(() => []);
  return new Map(r.map(([id, e, n]) => [id ?? "", { email: e ?? "", name: n ?? "" }]));
}

/* ---------- security emails ---------- */

const clock = () => new Date().toLocaleString("en-IN", { hour: "numeric", minute: "2-digit", day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).toLowerCase();

/**
 * Something that matters for the safety of a profile, told to its owner by email, so a change they didn't make never
 * goes unseen: a sign-in by password or Google, a password set, changed or removed, Google turned on or off, every
 * device signed out, the profile deleted. (A sign-in by code needs no notice: the code itself came by email.)
 */
export async function notice(email: string, headline: string, detail: string, device = "") {
  const where = device ? `\n\nfrom: ${device}` : "";
  const help = `write to ${box("security")}`;
  await sendEmail(
    email,
    `sahn: ${headline}`,
    `${headline}, ${clock()}.${where}\n\n${detail}\n\nnot you? sign in at ${(process.env.SHOP_SITE_URL?.trim() || SITE_URL).replace(/\/$/, "")}/profile with a code sent to this email, then sign-in → sign out everywhere, and change or remove the password. or ${help} and we'll help.`,
    `notice-${email}-${headline}-${Date.now()}`.replace(/[^\w@.-]/g, "-").slice(0, 200),
    "security",
  ).catch((e) => console.error("notice:", e));
}

/* ---------- what the buyer did ---------- */

export async function did(email: string, what: string, detail?: string) {
  await db("INSERT INTO user_events (email, what, detail) VALUES ($1, $2, $3)", [email, what.slice(0, 60), detail?.slice(0, 160) ?? null]).catch((e) => console.error("account event:", e));
}
export async function activity(email: string, limit = 200): Promise<Did[]> {
  const r = await db("SELECT at::text, what, detail FROM user_events WHERE email = $1 ORDER BY at DESC LIMIT $2::int", [email, limit]).catch(() => []);
  return r.map(([at, what, detail]) => ({ at: at ?? "", what: what ?? "", ...(detail ? { detail } : {}) }));
}

/* ---------- a password, for those who want one ---------- */

/**
 * Argon2id, the current best for passwords (OWASP's first choice), at OWASP's settings: 19 MiB, 2 passes. Checking
 * one takes the server about 40 ms, only when someone signs in with a password; that cost is what makes a stolen
 * hash useless to guess at. The database keeps only the hash, with its own random salt.
 */
/** 2 is Argon2id in the library's enum (a const enum, so written as its number) */
const ARGON = { algorithm: 2 as Algorithm, memoryCost: 19456, timeCost: 2, parallelism: 1 };

export async function passwordSetAt(email: string) {
  const r = await db("SELECT set_at::text FROM user_passwords WHERE email = $1", [email]).catch(() => []);
  return r[0]?.[0] ?? null;
}

/** a password worth having: 8 to 128 characters, not the email, not an obvious one */
export function weakPassword(pw: string, email: string) {
  if (pw.length < 8) return "at least 8 characters";
  if (pw.length > 128) return "128 characters at most";
  const low = pw.toLowerCase();
  if (low === email || low === email.split("@")[0]) return "not your email";
  if (/^(.)\1+$/.test(pw) || /^(?:0?123456789?0?|12345678|password1?|qwerty(?:123)?|iloveyou|sahn1234|abcd1234)$/.test(low)) return "that one's too easy to guess";
  return null;
}

export async function setPassword(email: string, pw: string) {
  const h = await argonHash(pw.normalize("NFKC"), ARGON);
  await db("INSERT INTO user_passwords (email, hash) VALUES ($1, $2) ON CONFLICT (email) DO UPDATE SET hash = $2, set_at = now()", [email, h]);
}
export const removePassword = (email: string) => db("DELETE FROM user_passwords WHERE email = $1", [email]);

/** a hash of nothing, so an email with no password costs the same check and timing tells nothing */
let decoy: Promise<string> | null = null;

/** the password checked against its hash (the library compares in constant time) */
export async function checkPassword(email: string, pw: string) {
  const r = await db("SELECT hash FROM user_passwords WHERE email = $1", [email]).catch(() => []);
  const h = r[0]?.[0];
  const ok = await argonVerify(h ?? (await (decoy ??= argonHash(randomBytes(16).toString("hex"), ARGON))), pw.normalize("NFKC")).catch(() => false);
  return !!h && ok;
}

/** the account and its addresses, or null */
export async function loadAccount(email: string): Promise<Account | null> {
  const r = await db(
    `SELECT u.name, u.phone, u.created_at::text, u.google_at::text, u.google_off::text,
       coalesce((SELECT json_agg(json_build_object('id', a.id, 'name', a.name, 'phone', a.phone, 'address1', a.address1, 'address2', a.address2, 'city', a.city, 'state', a.state, 'pin', a.pin) ORDER BY a.position)
                 FROM user_addresses a WHERE a.email = u.email), '[]')::text
     FROM users u WHERE u.email = $1`,
    [email],
  );
  const x = r[0];
  if (!x) return null;
  return {
    email, name: x[0] ?? "", phone: x[1] ?? "", createdAt: x[2] ? new Date(x[2]).toISOString() : new Date().toISOString(),
    ...(x[3] ? { google: new Date(x[3]).toISOString() } : {}), ...(x[4] === "true" ? { googleOff: true } : {}),
    addresses: JSON.parse(x[5] ?? "[]") as Address[],
  };
}

/** the account written back whole: its details, and its addresses replaced in their new order, in one statement */
export async function saveAccount(a: Account) {
  const list = a.addresses.slice(0, 5).map((x, i) => ({ ...x, position: i, address2: x.address2 ?? "" }));
  await db(
    `WITH u AS (
       INSERT INTO users (email, name, phone, created_at, google_at, google_off) VALUES ($1, $2, $3, $4::timestamptz, $5::timestamptz, $6::boolean)
       ON CONFLICT (email) DO UPDATE SET name = $2, phone = $3, google_at = $5::timestamptz, google_off = $6::boolean, updated_at = now()
       RETURNING email),
     gone AS (DELETE FROM user_addresses WHERE email = $1 AND NOT (id = ANY(SELECT x->>'id' FROM jsonb_array_elements($7::jsonb) x)))
     INSERT INTO user_addresses (id, email, position, name, phone, address1, address2, city, state, pin)
     SELECT r.id, (SELECT email FROM u), r.position, r.name, r.phone, r.address1, r.address2, r.city, r.state, r.pin
     FROM jsonb_to_recordset($7::jsonb) AS r(id text, position int, name text, phone text, address1 text, address2 text, city text, state text, pin text)
     ON CONFLICT (email, id) DO UPDATE SET position = EXCLUDED.position, name = EXCLUDED.name, phone = EXCLUDED.phone, address1 = EXCLUDED.address1,
       address2 = EXCLUDED.address2, city = EXCLUDED.city, state = EXCLUDED.state, pin = EXCLUDED.pin`,
    [a.email, a.name, a.phone, a.createdAt, a.google ?? null, String(!!a.googleOff), JSON.stringify(list)],
  );
}

/** every account, newest first, for the admin, with how many orders each email has placed; `q` searches email, name and phone */
export async function listAccounts(opts: { limit?: number; offset?: number; q?: string } = {}): Promise<(Account & { orders: number })[]> {
  const limit = Math.min(Math.max(1, opts.limit ?? 50), 200), offset = Math.max(0, opts.offset ?? 0);
  const q = opts.q?.trim() ? `%${opts.q.trim().slice(0, 80).replace(/[\\%_]/g, (c) => `\\${c}`)}%` : null;
  const r = await db(
    `SELECT u.email, u.name, u.phone, u.created_at::text, u.google_at::text, u.google_off::text,
       coalesce((SELECT json_agg(json_build_object('id', a.id, 'name', a.name, 'phone', a.phone, 'address1', a.address1, 'address2', a.address2, 'city', a.city, 'state', a.state, 'pin', a.pin) ORDER BY a.position)
                 FROM user_addresses a WHERE a.email = u.email), '[]')::text,
       (SELECT count(*) FROM user_orders o WHERE o.email = u.email)::text
     FROM users u WHERE ($1::text IS NULL OR u.email ILIKE $1 OR u.name ILIKE $1 OR u.phone ILIKE $1)
     ORDER BY u.created_at DESC OFFSET $2::int LIMIT $3::int`,
    [q, offset, limit],
  );
  return r.map((x) => ({
    email: x[0] ?? "", name: x[1] ?? "", phone: x[2] ?? "", createdAt: x[3] ? new Date(x[3]).toISOString() : "",
    ...(x[4] ? { google: new Date(x[4]).toISOString() } : {}), ...(x[5] === "true" ? { googleOff: true } : {}),
    addresses: JSON.parse(x[6] ?? "[]") as Address[], orders: Number(x[7] ?? 0),
  }));
}

export async function countAccounts() {
  const r = await db("SELECT count(*)::text FROM users");
  return Number(r[0]?.[0] ?? 0);
}

/** sign an email out on every device */
export async function signOutEverywhere(email: string) {
  const r = await db("DELETE FROM user_sessions WHERE email = $1 RETURNING hash", [email]);
  const old = await query("DELETE FROM kv WHERE key LIKE 'sess:%' AND value = $1 RETURNING key", [email]).catch(() => []);
  return r.length + old.length;
}

/** an account gone: its details, saved addresses, order list, password, activity and every session (its orders are the orders' own business) */
export async function deleteAccount(email: string) {
  const sessions = await signOutEverywhere(email);
  // the addresses go with the user row (ON DELETE CASCADE)
  await db("DELETE FROM users WHERE email = $1", [email]);
  await db("DELETE FROM user_orders WHERE email = $1", [email]);
  await db("DELETE FROM user_passwords WHERE email = $1", [email]);
  await db("DELETE FROM user_events WHERE email = $1", [email]);
  await db("DELETE FROM user_codes WHERE email = $1", [email]);
  await db("DELETE FROM visitor_people WHERE email = $1", [email]);
  await db("DELETE FROM user_prefs WHERE email = $1", [email]);
  await db("DELETE FROM user_saved WHERE email = $1", [email]);
  await forget(email);
  return { sessions };
}

/** the account's orders, newest first */
export const accountOrders = async (email: string) =>
  (await db("SELECT order_id FROM user_orders WHERE email = $1 ORDER BY at DESC LIMIT 100", [email])).map((r) => r[0] ?? "").filter(Boolean);
export const linkOrder = (email: string, id: string) => db("INSERT INTO user_orders (email, order_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", [email, id]);
export const unlinkOrder = (email: string, id: string) => db("DELETE FROM user_orders WHERE email = $1 AND order_id = $2", [email, id]);

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
