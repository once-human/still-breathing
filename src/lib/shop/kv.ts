import { kvKeys } from "./config";
import { ShopError } from "./errors";

/**
 * The order store: Postgres on Neon, spoken to over Neon's HTTP query endpoint (no driver, no pool, nothing kept open
 * between requests). It keeps the small set of Redis commands the shop was written against (GET, SET with EX/NX, DEL,
 * INCR, EXPIRE, PEXPIRE, ZADD, ZREM, ZRANGE, ZREVRANGE) with the same meaning, so orders, the once-only marks that make
 * webhooks idempotent, sessions and the rate limits read the same as before. Two tables: kv (a value that may expire)
 * and zset (scored members). Each command is one statement, so each is atomic on its own.
 */
type Cmd = (string | number)[];

const SCHEMA = [
  "CREATE TABLE IF NOT EXISTS kv (key text PRIMARY KEY, value text NOT NULL, expires_at timestamptz)",
  "CREATE INDEX IF NOT EXISTS kv_expires ON kv (expires_at) WHERE expires_at IS NOT NULL",
  "CREATE TABLE IF NOT EXISTS zset (key text NOT NULL, member text NOT NULL, score double precision NOT NULL, PRIMARY KEY (key, member))",
  "CREATE INDEX IF NOT EXISTS zset_score ON zset (key, score)",
];

let ready: Promise<void> | null = null;

async function sql(query: string, params: (string | number | null)[] = []): Promise<(string | null)[][]> {
  const k = kvKeys();
  if (!k) throw new ShopError("store not set up", 503);
  const res = await fetch(`https://${k.host}/sql`, {
    method: "POST",
    headers: { "Neon-Connection-String": k.url, "Neon-Raw-Text-Output": "true", "Neon-Array-Mode": "true", "Content-Type": "application/json" },
    body: JSON.stringify({ query, params: params.map((p) => (p === null ? null : String(p))) }),
    cache: "no-store",
    signal: AbortSignal.timeout(8000),
  }).catch(() => null);
  if (!res) throw new ShopError("store unreachable");
  const j = (await res.json().catch(() => null)) as { rows?: (string | null)[][]; message?: string } | null;
  if (!res.ok || !j?.rows) throw new ShopError(`store ${res.status}: ${j?.message ?? ""}`.slice(0, 300));
  return j.rows;
}

/**
 * What the database already has (tables and indexes by name), looked up once per server instance in one query, so a
 * fresh instance doesn't send a CREATE ... IF NOT EXISTS for every table one after another before its first read.
 */
let known: Promise<Set<string>> | null = null;
const existing = () =>
  (known ??= sql("SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = current_schema()")
    .then((r) => new Set(r.map((x) => x[0] ?? "")))
    .catch((e) => {
      known = null;
      throw e;
    }));

/** runs those of these CREATE ... IF NOT EXISTS statements whose table or index isn't there yet, in order */
export async function ensure(statements: string[]) {
  const have = await existing();
  for (const s of statements) {
    const name = /IF NOT EXISTS\s+(\w+)/i.exec(s)?.[1];
    if (name && have.has(name)) continue;
    await sql(s);
    if (name) have.add(name);
  }
}

/**
 * The one SQL client: every table the site keeps (the shop's kv and zset, settings, products, the admin's own) goes
 * through this. Parameters only, never string-built values. Rows come back as arrays of text (or null), in column
 * order. The shop's tables are made first, once per server instance (CREATE ... IF NOT EXISTS, so any may go first).
 */
export const query = (text: string, params: (string | number | null)[] = []) => {
  ready ??= ensure(SCHEMA).catch((e) => {
    ready = null;
    throw e;
  });
  return ready.then(() => sql(text, params));
};

const LIVE = "(expires_at IS NULL OR expires_at > now())";
const num = (v: string | number, what: string) => {
  const n = Number(v);
  if (!Number.isFinite(n)) throw new ShopError(`store: bad ${what}`);
  return n;
};

export async function kv<T = unknown>(...cmd: Cmd): Promise<T> {
  const [op, key, ...a] = cmd.map(String);
  const k = key ?? "";
  // now and then, clear what has expired (reads already skip it)
  if (Math.random() < 0.02) query("DELETE FROM kv WHERE expires_at < now() - interval '1 hour'").catch(() => {});
  switch (op.toUpperCase()) {
    case "GET": {
      const r = await query(`SELECT value FROM kv WHERE key = $1 AND ${LIVE}`, [k]);
      return (r[0]?.[0] ?? null) as T;
    }
    case "SET": {
      const value = a[0] ?? "";
      let ms: number | null = null, nx = false;
      for (let i = 1; i < a.length; i++) {
        const f = a[i].toUpperCase();
        if (f === "EX") ms = num(a[++i], "EX") * 1000;
        else if (f === "PX") ms = num(a[++i], "PX");
        else if (f === "NX") nx = true;
      }
      const exp = ms === null ? "NULL" : "now() + ($3::double precision * interval '1 millisecond')";
      const params = ms === null ? [k, value] : [k, value, ms];
      const r = await query(
        `INSERT INTO kv (key, value, expires_at) VALUES ($1, $2, ${exp})
         ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, expires_at = EXCLUDED.expires_at
         ${nx ? "WHERE kv.expires_at IS NOT NULL AND kv.expires_at <= now()" : ""} RETURNING 1`,
        params,
      );
      return (r.length ? "OK" : null) as T;
    }
    case "DEL": {
      const keys = [k, ...a];
      const r = await query(
        `WITH k AS (SELECT jsonb_array_elements_text($1::jsonb) AS key),
              a AS (DELETE FROM kv WHERE key IN (SELECT key FROM k) RETURNING key),
              b AS (DELETE FROM zset WHERE key IN (SELECT key FROM k) RETURNING key)
         SELECT (SELECT count(*) FROM a) + (SELECT count(DISTINCT key) FROM b)`,
        [JSON.stringify(keys)],
      );
      return Number(r[0]?.[0] ?? 0) as T;
    }
    case "INCR": {
      const r = await query(
        `INSERT INTO kv (key, value, expires_at) VALUES ($1, '1', NULL)
         ON CONFLICT (key) DO UPDATE SET
           value = CASE WHEN kv.expires_at IS NOT NULL AND kv.expires_at <= now() THEN '1' ELSE (kv.value::bigint + 1)::text END,
           expires_at = CASE WHEN kv.expires_at IS NOT NULL AND kv.expires_at <= now() THEN NULL ELSE kv.expires_at END
         RETURNING value`,
        [k],
      );
      return Number(r[0]?.[0]) as T;
    }
    case "EXPIRE":
    case "PEXPIRE": {
      const ms = num(a[0], op) * (op.toUpperCase() === "EXPIRE" ? 1000 : 1);
      const r = await query(`UPDATE kv SET expires_at = now() + ($2::double precision * interval '1 millisecond') WHERE key = $1 AND ${LIVE} RETURNING 1`, [k, ms]);
      return (r.length ? 1 : 0) as T;
    }
    case "ZADD": {
      let n = 0;
      for (let i = 0; i + 1 < a.length; i += 2) {
        const r = await query("INSERT INTO zset (key, member, score) VALUES ($1, $2, $3) ON CONFLICT (key, member) DO UPDATE SET score = EXCLUDED.score RETURNING (xmax = 0)", [k, a[i + 1], num(a[i], "score")]);
        if (r[0]?.[0] === "t") n++;
      }
      return n as T;
    }
    case "ZREM": {
      const r = await query("DELETE FROM zset WHERE key = $1 AND member IN (SELECT jsonb_array_elements_text($2::jsonb)) RETURNING 1", [k, JSON.stringify(a)]);
      return r.length as T;
    }
    case "ZRANGE":
    case "ZREVRANGE": {
      const start = num(a[0], "start"), stop = num(a[1], "stop");
      if (start < 0 || stop < start) throw new ShopError("store: only plain ranges");
      const dir = op.toUpperCase() === "ZRANGE" ? "ASC" : "DESC";
      const r = await query(`SELECT member FROM zset WHERE key = $1 ORDER BY score ${dir}, member ${dir} OFFSET $2 LIMIT $3`, [k, start, stop - start + 1]);
      return r.map((row) => row[0] as string) as T;
    }
    default:
      throw new ShopError(`store: ${op} not supported`);
  }
}

export const getJson = async <T>(key: string) => {
  const v = await kv<string | null>("GET", key);
  return v ? (JSON.parse(v) as T) : null;
};
export const setJson = (key: string, value: unknown, ttlDays = 400) => kv("SET", key, JSON.stringify(value), "EX", ttlDays * 86400);

/** true the first time this mark is set (for `seconds`), false every time after */
export const once = async (key: string, seconds: number) => (await kv<string | null>("SET", key, "1", "NX", "EX", seconds)) === "OK";

/** a short lock so two deliveries of the same news can't act on one order at the same moment */
export async function withLock<T>(key: string, fn: () => Promise<T>): Promise<T | null> {
  if (!(await once(`lock:${key}`, 60))) return null;
  try {
    return await fn();
  } finally {
    await kv("DEL", `lock:${key}`).catch(() => {});
  }
}
