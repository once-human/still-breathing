import { kvKeys } from "./config";
import { ShopError } from "./errors";

/**
 * The order store: Upstash Redis through its REST API (no driver, nothing kept open). Orders, the once-only marks
 * that make webhooks idempotent, and the rate limits all live here, shared by every server instance.
 */
type Cmd = (string | number)[];

export async function kv<T = unknown>(...cmd: Cmd): Promise<T> {
  const keys = kvKeys();
  if (!keys) throw new ShopError("store not set up", 503);
  const res = await fetch(keys.url, {
    method: "POST",
    headers: { Authorization: `Bearer ${keys.token}`, "Content-Type": "application/json" },
    body: JSON.stringify(cmd.map(String)),
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
  }).catch(() => null);
  if (!res?.ok) throw new ShopError(`store ${res?.status ?? "unreachable"}`);
  const j = (await res.json()) as { result?: T; error?: string };
  if (j.error) throw new ShopError(`store: ${j.error}`);
  return j.result as T;
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
