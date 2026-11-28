import "server-only";
import { createHmac, timingSafeEqual } from "node:crypto";
import { SITE_URL } from "@/lib/site";
import { shopSecret } from "./config";
import { esc, sender } from "./email";
import { ensure, query } from "./kv";

/**
 * New-drop emails. Anyone can be on the list, signed in or not: they ask for it themselves (a box at checkout, the
 * welcome step, the switch in their profile), it's off until they do, and every email carries a one-tap way off
 * (a link, and the List-Unsubscribe header mail apps show as a button). Who asked, when, and from where is kept, so
 * the consent can be shown. Sending is from the admin, through Resend, a hundred to a call, from drops@.
 *
 * The admin can also write an email of its own (a reply, a thank-you, a note to a few people) from any name@ on the
 * domain. Both kinds are kept in mail_sends, so the admin shows what went out, from whom, and to how many.
 */
const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS subscribers (email text PRIMARY KEY, source text NOT NULL, subscribed_at timestamptz NOT NULL DEFAULT now(),
     unsubscribed_at timestamptz)`,
  `CREATE TABLE IF NOT EXISTS mail_sends (id bigserial PRIMARY KEY, kind text NOT NULL, sender text NOT NULL, recipients text[] NOT NULL DEFAULT '{}',
     subject text NOT NULL, body text NOT NULL, link text, at timestamptz NOT NULL DEFAULT now(), sent int NOT NULL DEFAULT 0, failed int NOT NULL DEFAULT 0, who text)`,
  `CREATE INDEX IF NOT EXISTS mail_sends_at ON mail_sends (at DESC)`,
];
let ready: Promise<void> | null = null;
const db = async (text: string, params: (string | number | null)[] = []) => {
  await (ready ??= ensure(SCHEMA).catch((e) => { ready = null; throw e; }));
  return query(text, params);
};
const site = () => (process.env.SHOP_SITE_URL?.trim() || SITE_URL).replace(/\/$/, "");

/**
 * On the list, from `source`: "checkout", "welcome", "profile", "back on". The checkout and welcome boxes start
 * ticked, so they only add someone who was never on it: a person who once took themselves off stays off until they
 * turn it back on themselves (the profile switch, or "back on" from the unsubscribe page).
 */
export const subscribe = (email: string, source: string) =>
  source === "checkout" || source === "welcome"
    ? db("INSERT INTO subscribers (email, source) VALUES ($1, $2) ON CONFLICT (email) DO NOTHING", [email.toLowerCase(), source])
    : db(`INSERT INTO subscribers (email, source) VALUES ($1, $2)
      ON CONFLICT (email) DO UPDATE SET source = $2, subscribed_at = now(), unsubscribed_at = NULL WHERE subscribers.unsubscribed_at IS NOT NULL`, [email.toLowerCase(), source]);
export const unsubscribe = (email: string) => db("UPDATE subscribers SET unsubscribed_at = now() WHERE email = $1 AND unsubscribed_at IS NULL", [email.toLowerCase()]);
export async function subscribed(email: string) {
  const r = await db("SELECT subscribed_at::text FROM subscribers WHERE email = $1 AND unsubscribed_at IS NULL", [email.toLowerCase()]).catch(() => []);
  return r[0]?.[0] ?? null;
}
export const forget = (email: string) => db("DELETE FROM subscribers WHERE email = $1", [email.toLowerCase()]);

/** the key in each unsubscribe link: proves the link came in that person's email, so nobody can take someone else off */
const token = (email: string) => createHmac("sha256", shopSecret() ?? "").update(`drops-off:${email.toLowerCase()}`).digest("base64url").slice(0, 22);
export const tokenOk = (email: string, t: string) => {
  const a = Buffer.from(token(email)), b = Buffer.from(t);
  return a.length === b.length && timingSafeEqual(a, b);
};
export const offLink = (email: string) => `${site()}/unsubscribe?e=${encodeURIComponent(email)}&t=${token(email)}`;
const oneTap = (email: string) => `${site()}/api/shop/drops?e=${encodeURIComponent(email)}&t=${token(email)}`;

/** for the admin: how many are on the list, how many left, who joined lately, and what was sent */
export async function listStats() {
  const [n, recent, sends] = await Promise.all([
    db("SELECT count(*) FILTER (WHERE unsubscribed_at IS NULL)::text, count(*) FILTER (WHERE unsubscribed_at IS NOT NULL)::text FROM subscribers"),
    db("SELECT email, source, subscribed_at::text FROM subscribers WHERE unsubscribed_at IS NULL ORDER BY subscribed_at DESC LIMIT 50"),
    db("SELECT id::text, kind, sender, array_to_string(recipients[1:3], ', '), cardinality(recipients)::text, subject, at::text, sent::text, failed::text FROM mail_sends ORDER BY at DESC LIMIT 40"),
  ]);
  return {
    on: Number(n[0]?.[0] ?? 0), off: Number(n[0]?.[1] ?? 0),
    recent: recent.map(([email, source, at]) => ({ email: email ?? "", source: source ?? "", at: at ?? "" })),
    sends: sends.map(([id, kind, from, to, count, subject, at, sent, failed]) => ({
      id: id ?? "", kind: kind === "drop" ? ("drop" as const) : ("letter" as const), from: from ?? "", to: to ?? "", count: Number(count), subject: subject ?? "", at: at ?? "", sent: Number(sent), failed: Number(failed),
    })),
  };
}

/** the body as paragraphs, the optional button, the sign-off and, for a drop, the way off */
function render(body: string, link: string | null, signoff: string, off: string | null) {
  const text = `${body}\n\n${link ? `${link}\n\n` : ""}${signoff}${off ? `\n\n—\nyou asked to hear about new drops. off with one tap: ${off}` : ""}`;
  const html = `<div style="font-family:Helvetica,Arial,sans-serif;font-size:16px;line-height:1.5;color:#111;max-width:520px">
    ${body.split("\n\n").map((p) => `<p>${esc(p).replace(/\n/g, "<br>")}</p>`).join("")}
    ${link ? `<p><a href="${esc(link)}" style="display:inline-block;background:#111;color:#fff;padding:12px 18px;text-decoration:none;font-weight:600">see it →</a></p>` : ""}
    <p style="font-weight:700;letter-spacing:-0.02em">${esc(signoff).replace(/\n/g, "<br>")}</p>
    ${off ? `<p style="font-size:12px;color:#777;border-top:1px solid #ddd;padding-top:10px">you asked to hear about new drops. <a href="${esc(off)}" style="color:#777">stop these emails</a>.</p>` : ""}</div>`;
  return { text, html };
}

/** a hundred emails to a Resend call; how many went and how many didn't */
async function batch(key: string, items: object[], idem: string) {
  let sent = 0, failed = 0;
  for (let i = 0; i < items.length; i += 100) {
    const chunk = items.slice(i, i + 100);
    const res = await fetch("https://api.resend.com/emails/batch", {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json", "Idempotency-Key": `${idem}-${i}`.slice(0, 256) },
      body: JSON.stringify(chunk),
      cache: "no-store",
      signal: AbortSignal.timeout(20000),
    }).catch(() => null);
    if (res?.ok) sent += chunk.length;
    else { failed += chunk.length; console.error("mail batch:", res?.status, await res?.text().catch(() => "")); }
  }
  return { sent, failed };
}

/** one drop to `emails`, from drops@, each with its own one-tap way off (a link and the List-Unsubscribe header) */
export async function sendDrop(emails: string[], subject: string, body: string, link: string | null, key: string) {
  const s = sender("drops");
  return batch(s.k.key, emails.map((to) => ({
    from: s.from, to: [to], subject, reply_to: s.address, ...render(body, link, "sahn", offLink(to)),
    headers: { "List-Unsubscribe": `<${oneTap(to)}>`, "List-Unsubscribe-Post": "List-Unsubscribe=One-Click" },
  })), key);
}

/** an email the admin wrote, from any name@ on the domain, to each person on its own (nobody sees the others) */
export async function sendLetter(local: string, name: string, emails: string[], subject: string, body: string, link: string | null, signoff: string, key: string) {
  const s = sender(local, name);
  return { ...(await batch(s.k.key, emails.map((to) => ({ from: s.from, to: [to], subject, reply_to: s.address, ...render(body, link, signoff, null) })), key)), from: s.from };
}

/** everyone on the list now */
export const everyone = async () => (await db("SELECT email FROM subscribers WHERE unsubscribed_at IS NULL ORDER BY subscribed_at")).map((r) => r[0] ?? "").filter(Boolean);

export const logSend = (kind: "drop" | "letter", from: string, to: string[], subject: string, body: string, link: string | null, sent: number, failed: number, who: string) =>
  db("INSERT INTO mail_sends (kind, sender, recipients, subject, body, link, sent, failed, who) VALUES ($1, $2, $3::text[], $4, $5, $6, $7::int, $8::int, $9)",
    [kind, from, `{${to.slice(0, 500).map((e) => `"${e.replace(/["\\]/g, "")}"`).join(",")}}`, subject, body, link, sent, failed, who]);
