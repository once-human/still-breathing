import "server-only";
import { query } from "@/lib/shop/kv";

/**
 * The admin's own tables, in the same Neon database as the shop's order store, spoken to through the shop's one SQL
 * client. Each read comes back as JSON objects (the row set, or what an UPDATE ... RETURNING gives, wrapped in json_agg on the database), so the types below
 * are what Postgres sends, with numbers as numbers and times as ISO strings.
 */
const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS admin_tokens (hash text PRIMARY KEY, email text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL, used_at timestamptz)`,
  `CREATE TABLE IF NOT EXISTS admin_sessions (hash text PRIMARY KEY, email text NOT NULL, csrf text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL, seen_at timestamptz NOT NULL DEFAULT now(), ua text)`,
  `CREATE TABLE IF NOT EXISTS admin_audit (id bigserial PRIMARY KEY, at timestamptz NOT NULL DEFAULT now(), who text NOT NULL, action text NOT NULL, target text, detail jsonb, ip text)`,
  `CREATE INDEX IF NOT EXISTS admin_audit_at ON admin_audit (at DESC)`,
  `CREATE INDEX IF NOT EXISTS admin_audit_target ON admin_audit (target)`,
  `CREATE TABLE IF NOT EXISTS admin_notes (id bigserial PRIMARY KEY, order_id text NOT NULL, at timestamptz NOT NULL DEFAULT now(), who text NOT NULL, text text NOT NULL)`,
  `CREATE INDEX IF NOT EXISTS admin_notes_order ON admin_notes (order_id, at)`,
  `CREATE TABLE IF NOT EXISTS admin_payments (payment_id text PRIMARY KEY, order_id text NOT NULL, fee numeric, tax numeric, method text, detail text, settlement_id text, settled_at timestamptz, fetched_at timestamptz NOT NULL DEFAULT now())`,
  `CREATE TABLE IF NOT EXISTS events (id bigserial PRIMARY KEY, at timestamptz NOT NULL DEFAULT now(), day date NOT NULL, kind text NOT NULL, path text, ref text, source text, device text, region text, visitor text, design text, size text)`,
  `CREATE INDEX IF NOT EXISTS events_day ON events (day, kind)`,
];

let ready: Promise<void> | null = null;
const schema = () =>
  (ready ??= (async () => {
    for (const s of SCHEMA) await query(s);
  })().catch((e) => {
    ready = null;
    throw e;
  }));

type P = string | number | boolean | null;
const flat = (params: P[]) => params.map((p) => (typeof p === "boolean" ? (p ? "t" : "f") : p));

/** rows as objects */
export async function rows<T>(sql: string, params: P[] = []): Promise<T[]> {
  await schema();
  // a WITH, not a subquery, so UPDATE / INSERT ... RETURNING can be read the same way
  const r = await query(`WITH t AS (${sql}) SELECT coalesce(json_agg(t), '[]'::json)::text FROM t`, flat(params));
  return JSON.parse(r[0]?.[0] ?? "[]") as T[];
}
export const row = async <T>(sql: string, params: P[] = []) => (await rows<T>(sql, params))[0] ?? null;

/** a statement that returns nothing worth reading (INSERT / UPDATE / DELETE without RETURNING) */
export async function exec(sql: string, params: P[] = []) {
  await schema();
  await query(sql, flat(params));
}
