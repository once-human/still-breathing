import "server-only";
import { createHmac, timingSafeEqual } from "node:crypto";
import { OWNER_BOX } from "@/content/mail";
import { adminEmail } from "@/lib/admin/auth";
import { SITE_URL } from "@/lib/site";
import { mailKeys, ownerEmail, shopSecret } from "./config";
import { esc, sender } from "./email";
import { signature } from "./mailmark";
import { ShopError } from "./errors";
import { ensure, query } from "./kv";

/**
 * The shop's inbox. Every email to any address @sahn.in comes in through Resend (the domain's MX points there), which
 * tells us by webhook; we fetch it by its id with our own key (so a forged webhook can only point at a real email),
 * keep it in a thread, and send a copy to the admin's own inbox so nothing is missed. Replies go out from the admin,
 * from the address it was written to, and are kept in the same thread. Notes from the contact page land here too.
 *
 * Replying from gmail: each copy's Reply-To is reply+<thread>.<code>@sahn.in, the code signed with SHOP_SECRET, so only
 * someone who got the copy knows it. A reply to it from the owner's own address (and not failing its sender checks)
 * goes to the customer from onkar@, quoted part trimmed, in the same thread; anything else is kept as ordinary mail.
 */
const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS mail_threads (id bigserial PRIMARY KEY, box text NOT NULL, email text NOT NULL, name text NOT NULL DEFAULT '',
     subject text NOT NULL DEFAULT '', snippet text NOT NULL DEFAULT '', last_at timestamptz NOT NULL DEFAULT now(), unread int NOT NULL DEFAULT 0,
     archived boolean NOT NULL DEFAULT false, count int NOT NULL DEFAULT 0, order_id text)`,
  "CREATE INDEX IF NOT EXISTS mail_threads_last ON mail_threads (archived, last_at DESC)",
  "CREATE INDEX IF NOT EXISTS mail_threads_email ON mail_threads (email, last_at DESC)",
  `CREATE TABLE IF NOT EXISTS mail_messages (id bigserial PRIMARY KEY, thread_id bigint NOT NULL REFERENCES mail_threads (id) ON DELETE CASCADE,
     dir text NOT NULL, resend_id text UNIQUE, message_id text, from_addr text NOT NULL, from_name text NOT NULL DEFAULT '', to_addrs text[] NOT NULL DEFAULT '{}',
     cc text[] NOT NULL DEFAULT '{}', subject text NOT NULL DEFAULT '', text_body text NOT NULL DEFAULT '', html text, attachments jsonb NOT NULL DEFAULT '[]',
     auth jsonb, at timestamptz NOT NULL DEFAULT now(), who text)`,
  "CREATE INDEX IF NOT EXISTS mail_messages_thread ON mail_messages (thread_id, at)",
  "CREATE INDEX IF NOT EXISTS mail_messages_mid ON mail_messages (message_id)",
];
let ready: Promise<void> | null = null;
const db = async (text: string, params: (string | number | null)[] = []) => {
  await (ready ??= ensure(SCHEMA).catch((e) => { ready = null; throw e; }));
  return query(text, params);
};
const arr = (xs: string[]) => `{${xs.map((e) => `"${e.replace(/["\\]/g, "")}"`).join(",")}}`;
const site = () => (process.env.SHOP_SITE_URL?.trim() || SITE_URL).replace(/\/$/, "");

/** "Name <a@b>" → its parts */
export function parseAddress(v: string) {
  const m = v.match(/^\s*"?([^"<]*?)"?\s*<([^>]+)>\s*$/);
  return m ? { name: m[1].trim(), email: m[2].trim().toLowerCase() } : { name: "", email: v.trim().toLowerCase() };
}
/** "Re: Fwd: hello" → "hello", so replies find their thread */
const bare = (s: string) => s.replace(/^\s*((re|fwd?|aw|wg)\s*(\[\d+\])?\s*:\s*)+/i, "").trim().toLowerCase();
/** a received body's html can come as a data: URI */
function decodeHtml(h: string | null | undefined) {
  if (!h) return null;
  const m = h.match(/^data:text\/html(?:;charset=[^;,]+)?(;base64)?,(.*)$/s);
  if (!m) return h;
  try { return m[1] ? Buffer.from(m[2], "base64").toString("utf8") : decodeURIComponent(m[2]); } catch { return null; }
}
const textOf = (html: string) => html.replace(/<style[\s\S]*?<\/style>|<script[\s\S]*?<\/script>/gi, "").replace(/<br\s*\/?>|<\/p>|<\/div>/gi, "\n").replace(/<[^>]+>/g, "")
  .replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/\n{3,}/g, "\n\n").trim();
const snip = (t: string) => t.replace(/\s+/g, " ").trim().slice(0, 160);

/** which of our addresses it was written to: the first one on our domain */
function boxOf(addrs: string[], domain: string) {
  for (const a of addrs) {
    const e = parseAddress(a).email;
    if (e.endsWith(`@${domain}`) && !e.startsWith("reply+")) return e.split("@")[0];
  }
  return "hello";
}

async function findThread(box: string, email: string, subject: string, refs: string[]) {
  if (refs.length) {
    const r = await db(`SELECT thread_id::text FROM mail_messages WHERE message_id = ANY($1::text[]) ORDER BY at DESC LIMIT 1`, [arr(refs)]);
    if (r[0]?.[0]) return r[0][0];
  }
  const r = await db(`SELECT t.id::text, t.subject, t.box FROM mail_threads t WHERE t.email = $1 AND t.last_at > now() - interval '60 days' ORDER BY t.last_at DESC LIMIT 20`, [email]);
  const same = r.filter((x) => bare(x[1] ?? "") === bare(subject));
  // the same box first; then any box, but only for a "Re:" (an answer to something we sent from another address)
  return same.find((x) => x[2] === box)?.[0] ?? (/^\s*re\s*:/i.test(subject) ? same[0]?.[0] ?? null : null);
}

/* ---------- replying from gmail ---------- */

const replyCode = (thread: string) => {
  const s = shopSecret();
  return s ? createHmac("sha256", s).update(`gmail-reply:${thread}`).digest("hex").slice(0, 20) : null;
};
/** where a gmail reply to this thread's copy goes */
const replyAddress = (thread: string, domain: string) => {
  const c = replyCode(thread);
  return c ? `reply+${thread}.${c}@${domain}` : null;
};
/** the thread a reply+ address names, if its code is right */
function replyThread(addrs: string[], domain: string) {
  for (const a of addrs) {
    const m = parseAddress(a).email.match(/^reply\+(\d{1,18})\.([0-9a-f]{20})@(.+)$/);
    if (!m || m[3] !== domain) continue;
    const want = replyCode(m[1]);
    if (want && timingSafeEqual(Buffer.from(want), Buffer.from(m[2]))) return m[1];
  }
  return null;
}
/** a reply's own words: everything above gmail's "On … wrote:" and the quoted lines */
export function freshPart(text: string, html: string | null) {
  let t = text.replace(/\r\n/g, "\n");
  if (!t.trim() && html) t = textOf(html.replace(/<div[^>]*class="?gmail_quote[\s\S]*$/i, "").replace(/<blockquote[\s\S]*$/i, ""));
  const cuts = [
    t.search(/\n[ \t]*On [^\n]*(\n[^\n]*)?wrote:[ \t]*\n/),
    t.search(/\n[ \t]*-{2,}[ \t]*Original Message[ \t]*-{2,}/i),
    t.search(/^>/m),
    t.search(/\n[ \t]*From: [^\n]*\n[ \t]*(Sent|Date): /),
  ].filter((i) => i >= 0);
  if (cuts.length) t = t.slice(0, Math.min(...cuts));
  return t.replace(/\n-- \n[\s\S]*$/, "").replace(/\n{3,}/g, "\n\n").trim();
}
/** the owner is told when a gmail reply couldn't go out, since the copy-to-owner skips their own mail */
async function replyBounced(to: string, thread: string, why: string) {
  const s = sender("inbox", "sahn inbox");
  const link = `${site()}/admin/mail/${thread}`;
  await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${s.k.key}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: s.from, to: [to], subject: "your reply wasn't sent", text: `${why}\n\nanswer it in the admin instead: ${link}`, headers: { "Auto-Submitted": "auto-generated" } }),
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  }).catch((e) => console.error("reply bounce:", e));
}

type In = { resendId: string | null; messageId: string | null; refs: string[]; box: string; from: { name: string; email: string }; to: string[]; cc: string[];
  subject: string; text: string; html: string | null; attachments: unknown[]; auth: unknown; at: string; order?: string | null };

/** keep an incoming email in its thread; returns the thread, or null if it was already kept */
async function keep(m: In) {
  if (m.resendId) {
    const seen = await db("SELECT 1 FROM mail_messages WHERE resend_id = $1", [m.resendId]);
    if (seen.length) return null;
  }
  let thread = await findThread(m.box, m.from.email, m.subject, m.refs);
  if (!thread) {
    const r = await db("INSERT INTO mail_threads (box, email, name, subject, order_id) VALUES ($1, $2, $3, $4, $5) RETURNING id::text",
      [m.box, m.from.email, m.from.name, m.subject || "(no subject)", m.order ?? null]);
    thread = r[0]![0]!;
  }
  await db(`INSERT INTO mail_messages (thread_id, dir, resend_id, message_id, from_addr, from_name, to_addrs, cc, subject, text_body, html, attachments, auth, at)
    VALUES ($1::bigint, 'in', $2, $3, $4, $5, $6::text[], $7::text[], $8, $9, $10, $11::jsonb, $12::jsonb, $13::timestamptz) ON CONFLICT (resend_id) DO NOTHING`,
    [thread, m.resendId, m.messageId, m.from.email, m.from.name, arr(m.to), arr(m.cc), m.subject, m.text.slice(0, 200_000), m.html?.slice(0, 1_000_000) ?? null,
      JSON.stringify(m.attachments ?? []), JSON.stringify(m.auth ?? null), m.at]);
  await db(`UPDATE mail_threads SET last_at = greatest(last_at, $2::timestamptz), unread = unread + 1, archived = false, count = count + 1, snippet = $3,
    name = CASE WHEN name = '' THEN $4 ELSE name END WHERE id = $1::bigint`, [thread, m.at, snip(m.text), m.from.name]);
  return thread;
}

/** a copy to the admin's own inbox, with a link to answer it in the admin; never for mail from the admin or an auto-reply */
async function tellAdmin(thread: string, m: In, auto: boolean) {
  const to = adminEmail() ?? ownerEmail();
  if (!to || auto || m.from.email === to) return;
  const direct = m.box === "direct";
  const who = m.from.name ? `${m.from.name} <${m.from.email}>` : m.from.email;
  const s = sender("inbox", "sahn inbox");
  const subject = direct ? `straight to you: ${m.from.name || m.from.email}${m.order ? ` · order #${m.order}` : ""}` : `${m.box}@ · ${m.subject || "(no subject)"} · ${m.from.name || m.from.email}`;
  const link = `${site()}/admin/mail/${thread}`;
  const text = `${who} wrote to ${m.box}@${s.address.split("@")[1]}${m.subject ? `: ${m.subject}` : ""}\n\n${m.text.slice(0, 6000)}\n\n—\nreply to this email and it goes to them from ${OWNER_BOX}@, or answer it in the admin: ${link}`;
  await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${s.k.key}`, "Content-Type": "application/json", "Idempotency-Key": `inbox-copy-${m.resendId ?? `${thread}-${m.at}`}`.slice(0, 256) },
    body: JSON.stringify({
      from: s.from, to: [to], subject, text, reply_to: replyAddress(thread, s.address.split("@")[1]!) ?? m.from.email,
      html: `<div style="font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;color:#111;max-width:560px"><p style="color:#666">${esc(who)} wrote to ${esc(m.box)}@</p>${esc(m.text.slice(0, 6000)).split("\n\n").map((p) => `<p>${p.replace(/\n/g, "<br>")}</p>`).join("")}<p style="color:#666;font-size:13px">reply to this email and it goes to them from ${esc(OWNER_BOX)}@, or</p><p><a href="${esc(link)}" style="display:inline-block;background:#111;color:#fff;padding:10px 16px;text-decoration:none;font-weight:600">answer it in the admin →</a></p></div>`,
      headers: { "Auto-Submitted": "auto-generated" },
    }),
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  }).catch((e) => console.error("inbox copy:", e));
}

/** the webhook's email id → fetched from Resend, kept, and copied to the admin. False if Resend doesn't know it. */
export async function receive(emailId: string) {
  const k = mailKeys();
  if (!k) throw new ShopError("email not set up", 503);
  if (!/^[0-9a-f-]{20,64}$/i.test(emailId)) return false;
  const res = await fetch(`https://api.resend.com/emails/receiving/${emailId}`, { headers: { Authorization: `Bearer ${k.readKey}` }, cache: "no-store", signal: AbortSignal.timeout(15000) });
  if (res.status === 404 || res.status === 422) return false;
  if (!res.ok) throw new ShopError(`resend receiving ${res.status}: ${(await res.text().catch(() => "")).slice(0, 200)}`);
  const e = (await res.json()) as {
    id: string; from: string; to?: string[]; cc?: string[]; received_for?: string[]; subject?: string; html?: string | null; text?: string | null;
    headers?: Record<string, string>; message_id?: string; created_at?: string; attachments?: { id: string; filename: string; content_type: string; size?: number; content_disposition?: string | null }[];
    authentication?: unknown;
  };
  const h = Object.fromEntries(Object.entries(e.headers ?? {}).map(([a, b]) => [a.toLowerCase(), String(b)]));
  const from = parseAddress(h.from ?? e.from);
  const html = decodeHtml(e.html);
  const text = (e.text ?? "").trim() || (html ? textOf(html) : "");
  const refs = `${h["in-reply-to"] ?? ""} ${h.references ?? ""}`.match(/<[^>]+>/g) ?? [];
  const auto = /auto-(replied|generated)/i.test(h["auto-submitted"] ?? "") || /bulk|junk|list|auto_reply/i.test(h.precedence ?? "") || !!h["x-autoreply"];
  const m: In = {
    resendId: e.id, messageId: e.message_id ?? h["message-id"] ?? null, refs, box: boxOf([...(e.received_for ?? []), ...(e.to ?? []), ...(e.cc ?? [])], k.domain), from,
    to: e.to ?? [], cc: e.cc ?? [], subject: (e.subject ?? "").slice(0, 300), text, html,
    attachments: (e.attachments ?? []).map((a) => ({ id: a.id, filename: a.filename, type: a.content_type, size: a.size ?? null, inline: a.content_disposition === "inline" })),
    auth: e.authentication ?? null, at: e.created_at ?? new Date().toISOString(),
  };
  const target = replyThread([...(e.received_for ?? []), ...(e.to ?? []), ...(e.cc ?? [])], k.domain);
  const me = (adminEmail() ?? ownerEmail())?.toLowerCase();
  if (target && me && from.email === me && !auto) {
    const failing = /\b(spf|dkim|dmarc)\s*[=:]\s*"?(fail|softfail|permerror)/i.test(`${JSON.stringify(e.authentication ?? "")} ${h["authentication-results"] ?? ""}`)
      || /"(spf|dkim|dmarc)"\s*:\s*"(fail|softfail|permerror)"/i.test(JSON.stringify(e.authentication ?? ""));
    const body = freshPart(text, html);
    if (failing) await replyBounced(me, target, "it didn't pass gmail's sender checks, so it might not have been you.");
    else if (!body) await replyBounced(me, target, "it came through empty once the quoted part was trimmed.");
    else {
      try {
        await reply(target, body, `gmail (${me})`, OWNER_BOX, `gmail-${e.id}`);
      } catch (err) {
        console.error("gmail reply:", err);
        await replyBounced(me, target, "sending it failed on our side.");
      }
    }
    return true;
  }
  const thread = await keep(m);
  if (thread) await tellAdmin(thread, m, auto);
  return true;
}

/** a note from the contact page's "straight to the top" form: into the inbox as a thread to direct@, and copied to the admin */
export async function noteDirect(n: { name: string; email: string; order: string | null; body: string; device: string; signedIn: boolean }) {
  const m: In = {
    resendId: null, messageId: null, refs: [], box: "direct", from: { name: n.name, email: n.email }, to: [], cc: [],
    subject: n.order ? `about order #${n.order}` : "from the contact page", text: `${n.body}${n.device ? `\n\n(sent from the contact page${n.signedIn ? ", signed in" : ""}, ${n.device})` : ""}`,
    html: null, attachments: [], auth: null, at: new Date().toISOString(), order: n.order,
  };
  const thread = await keep(m);
  if (thread) await tellAdmin(thread, m, false);
}

/* ---------- the admin's side ---------- */

export type ThreadRow = { id: string; box: string; email: string; name: string; subject: string; snippet: string; at: string; unread: number; archived: boolean; count: number; order: string | null };
const row = (r: (string | null)[]): ThreadRow => ({
  id: r[0] ?? "", box: r[1] ?? "", email: r[2] ?? "", name: r[3] ?? "", subject: r[4] ?? "", snippet: r[5] ?? "", at: r[6] ?? "", unread: Number(r[7] ?? 0),
  archived: r[8] === "true" || r[8] === "t", count: Number(r[9] ?? 0), order: r[10] ?? null,
});
const COLS = "id::text, box, email, name, subject, snippet, last_at::text, unread::text, archived::text, count::text, order_id";

export async function threads(o: { box?: string; view?: "inbox" | "unread" | "archived" | "all"; q?: string; email?: string; limit?: number }) {
  const where: string[] = [], p: (string | number | null)[] = [];
  if (o.box) { p.push(o.box); where.push(`box = $${p.length}`); }
  if (o.email) { p.push(o.email); where.push(`email = $${p.length}`); }
  if (o.view === "unread") where.push("unread > 0 AND NOT archived");
  else if (o.view === "archived") where.push("archived");
  else if (o.view !== "all") where.push("NOT archived");
  if (o.q) { p.push(`%${o.q.replace(/[%_\\]/g, "")}%`); where.push(`(email ILIKE $${p.length} OR name ILIKE $${p.length} OR subject ILIKE $${p.length} OR snippet ILIKE $${p.length})`); }
  p.push(o.limit ?? 200);
  const r = await db(`SELECT ${COLS} FROM mail_threads ${where.length ? `WHERE ${where.join(" AND ")}` : ""} ORDER BY last_at DESC LIMIT $${p.length}::int`, p).catch(() => []);
  return r.map(row);
}

export async function inboxCounts() {
  const r = await db("SELECT box, count(*) FILTER (WHERE NOT archived)::text, sum(unread) FILTER (WHERE NOT archived)::text FROM mail_threads GROUP BY box").catch(() => []);
  return r.map(([box, open, unread]) => ({ box: box ?? "", open: Number(open ?? 0), unread: Number(unread ?? 0) }));
}

export type Message = { id: string; dir: "in" | "out"; from: string; fromName: string; to: string[]; cc: string[]; subject: string; text: string; html: string | null;
  attachments: { id: string; filename: string; type: string; size: number | null; inline: boolean }[]; at: string; who: string | null; resendId: string | null; messageId: string | null; auth: Record<string, string> | null };

export async function thread(id: string) {
  if (!/^\d{1,18}$/.test(id)) return null;
  const t = await db(`SELECT ${COLS} FROM mail_threads WHERE id = $1::bigint`, [id]);
  if (!t[0]) return null;
  const ms = await db(`SELECT id::text, dir, from_addr, from_name, array_to_json(to_addrs)::text, array_to_json(cc)::text, subject, text_body, html, attachments::text, at::text, who, resend_id, message_id, auth::text
    FROM mail_messages WHERE thread_id = $1::bigint ORDER BY at`, [id]);
  return {
    thread: row(t[0]),
    messages: ms.map((m): Message => ({
      id: m[0] ?? "", dir: m[1] === "out" ? "out" : "in", from: m[2] ?? "", fromName: m[3] ?? "", to: JSON.parse(m[4] ?? "[]"), cc: JSON.parse(m[5] ?? "[]"), subject: m[6] ?? "",
      text: m[7] ?? "", html: m[8], attachments: JSON.parse(m[9] ?? "[]"), at: m[10] ?? "", who: m[11], resendId: m[12], messageId: m[13], auth: m[14] ? JSON.parse(m[14]) : null,
    })),
  };
}

export const markRead = (id: string, read = true) => db(`UPDATE mail_threads SET unread = ${read ? "0" : "greatest(unread, 1)"} WHERE id = $1::bigint`, [id]);
export const archive = (id: string, on: boolean) => db("UPDATE mail_threads SET archived = $2::boolean WHERE id = $1::bigint", [id, String(on)]);

/** a reply from the admin, from the address the thread was written to, threaded on the last email in it */
export async function reply(id: string, body: string, who: string, local?: string, key?: string) {
  const t = await thread(id);
  if (!t) throw new ShopError("no such conversation", 404);
  const last = [...t.messages].reverse().find((m) => m.dir === "in");
  const box = (local || (t.thread.box === "direct" ? "direct" : t.thread.box)).toLowerCase();
  const s = sender(box);
  const subject = /^re:/i.test(t.thread.subject) ? t.thread.subject : `Re: ${t.thread.subject}`;
  const refs = t.messages.map((m) => m.messageId).filter(Boolean).slice(-10) as string[];
  const quote = last ? `\n\n—\non ${new Date(last.at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" }).toLowerCase()}, ${last.fromName || last.from} wrote:\n${last.text.split("\n").slice(0, 40).map((l) => `> ${l}`).join("\n")}` : "";
  const sig = signature(box, OWNER_BOX);
  const text = `${body}\n\n${sig.text}${quote}`;
  const html = `<div style="font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;color:#111;max-width:560px">${esc(body).split("\n\n").map((p) => `<p>${p.replace(/\n/g, "<br>")}</p>`).join("")}${sig.html}${last ? `<blockquote style="margin:16px 0 0;padding-left:12px;border-left:2px solid #ddd;color:#666">${esc(last.text.slice(0, 4000)).replace(/\n/g, "<br>")}</blockquote>` : ""}</div>`;
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${s.k.key}`, "Content-Type": "application/json", ...(key ? { "Idempotency-Key": key.slice(0, 256) } : {}) },
    body: JSON.stringify({
      from: s.from, to: [t.thread.email], subject, text, html, reply_to: s.address,
      // their answer carries these References, so it finds this thread whichever address it goes to
      ...(last?.messageId ? { headers: { "In-Reply-To": last.messageId, References: refs.join(" ") } } : {}),
    }),
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  }).catch(() => null);
  if (!res?.ok) throw new ShopError(`email ${res?.status ?? "unreachable"}: ${(await res?.text().catch(() => "")) ?? ""}`.slice(0, 300));
  const sent = (await res.json().catch(() => ({}))) as { id?: string };
  const added = await db(`INSERT INTO mail_messages (thread_id, dir, resend_id, from_addr, from_name, to_addrs, subject, text_body, html, who)
    VALUES ($1::bigint, 'out', $2, $3, $4, $5::text[], $6, $7, $8, $9) ON CONFLICT (resend_id) DO NOTHING RETURNING 1`,
    [id, sent.id ?? null, s.address, s.from.split(" <")[0], arr([t.thread.email]), subject, body, html, who]);
  if (added.length) await db("UPDATE mail_threads SET last_at = now(), unread = 0, count = count + 1, snippet = $2 WHERE id = $1::bigint", [id, snip(`you: ${body}`)]);
  return s.address;
}

/** a fresh link to one attachment (Resend's links last an hour) */
export async function attachmentLink(resendId: string, attachmentId: string) {
  const k = mailKeys();
  if (!k) return null;
  const res = await fetch(`https://api.resend.com/emails/receiving/${resendId}/attachments/${attachmentId}`, { headers: { Authorization: `Bearer ${k.readKey}` }, cache: "no-store" }).catch(() => null);
  if (!res?.ok) return null;
  const j = (await res.json().catch(() => ({}))) as { download_url?: string };
  return j.download_url ?? null;
}
