import "server-only";
import { adminEmail } from "@/lib/admin/auth";
import { ownerEmail } from "./config";
import { sendEmail } from "./email";
import { ensure, query } from "./kv";

/**
 * Notes to the maker: the top of the ladder, for what writing in hasn't put right or what can't wait. Each one is
 * kept (so a failed email never loses it) and emailed at once to the admin's own inbox, with the sender as reply-to,
 * under a subject that starts "for the maker" so it stands out and a mail filter can catch it.
 */
const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS maker_notes (id bigserial PRIMARY KEY, name text NOT NULL, email text NOT NULL, order_id text, body text NOT NULL,
     device text, signed_in boolean NOT NULL DEFAULT false, at timestamptz NOT NULL DEFAULT now(), mailed boolean NOT NULL DEFAULT false)`,
  `CREATE INDEX IF NOT EXISTS maker_notes_at ON maker_notes (at DESC)`,
];
let ready: Promise<void> | null = null;
const db = async (text: string, params: (string | number | null)[] = []) => {
  await (ready ??= ensure(SCHEMA).catch((e) => { ready = null; throw e; }));
  return query(text, params);
};

export async function noteToMaker(n: { name: string; email: string; order: string | null; body: string; device: string; signedIn: boolean }) {
  const r = await db("INSERT INTO maker_notes (name, email, order_id, body, device, signed_in) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id::text",
    [n.name, n.email, n.order, n.body, n.device, n.signedIn ? "true" : "false"]);
  const id = r[0]?.[0] ?? "";
  const to = adminEmail() ?? ownerEmail();
  if (!to) return;
  await sendEmail(
    to,
    `for the maker: ${n.name}${n.order ? ` · order #${n.order}` : ""}`,
    `${n.body}\n\n—\n${n.name}, ${n.email}${n.signedIn ? " (signed in)" : ""}${n.order ? `\norder #${n.order}` : ""}${n.device ? `\nfrom ${n.device}` : ""}\n\nreply to this email to answer them.`,
    `maker-${id}`,
    "maker",
    n.email,
  );
  await db("UPDATE maker_notes SET mailed = true WHERE id = $1::bigint", [id]);
}

export async function makerNotes(limit = 30) {
  const r = await db("SELECT id::text, name, email, order_id, body, at::text, mailed FROM maker_notes ORDER BY at DESC LIMIT $1::int", [limit]).catch(() => []);
  return r.map(([id, name, email, order, body, at, mailed]) => ({ id: id ?? "", name: name ?? "", email: email ?? "", order: order ?? null, body: body ?? "", at: at ?? "", mailed: mailed === "true" || mailed === "t" }));
}
