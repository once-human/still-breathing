import { RATES } from "@/content/shop";
import { kvKeys, shopOpen } from "./config";
import { ShopError } from "./errors";
import { query } from "./kv";

/**
 * The shop's switches, kept in the database so the admin can change them without a deploy:
 *   open    whether new orders are taken (orders already paid are always carried through)
 *   margin  rupees added to the partner's cost, before rounding up to the next ₹10 (a product's own margin or fixed
 *           price beats it)
 *   notice  the quiet line over every page, in place of the usual one (empty: the usual one)
 *   closed  what checkout says while orders are off (empty: the usual words)
 * Server only. Read through a 30-second cache per instance; with no database it's the code's values.
 */
export type Settings = { open: boolean; margin: number; notice: string; closed: string };
export const DEFAULT_SETTINGS: Settings = { open: true, margin: RATES.margin, notice: "", closed: "" };
/** site words from the admin: one line, no markup, capped */
export const cleanLine = (v: unknown, max: number) => (typeof v === "string" ? v.replace(/[\u0000-\u001f\u007f<>]/g, " ").replace(/\s+/g, " ").trim().slice(0, max) : null);

let made: Promise<unknown> | null = null;
const table = () =>
  (made ??= query("CREATE TABLE IF NOT EXISTS settings (key text PRIMARY KEY, value jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(), updated_by text)").catch((e) => {
    made = null;
    throw e;
  }));

const okMargin = (x: unknown): x is number => Number.isInteger(x) && (x as number) >= 0 && (x as number) <= 5000;

let cache: { v: Settings; at: number } | null = null;

/** `fresh` skips this instance's 30-second cache (a page being regenerated after a save must see the save) */
export async function getSettings(opts: { fresh?: boolean } = {}): Promise<Settings> {
  if (!kvKeys()) return DEFAULT_SETTINGS;
  if (!opts.fresh && cache && Date.now() - cache.at < 30_000) return cache.v;
  try {
    await table();
    const v = { ...DEFAULT_SETTINGS };
    for (const [k, raw] of await query("SELECT key, value::text FROM settings")) {
      const x = JSON.parse(raw ?? "null") as unknown;
      if (k === "open" && typeof x === "boolean") v.open = x;
      if (k === "margin" && okMargin(x)) v.margin = x;
      if (k === "notice" && typeof x === "string") v.notice = cleanLine(x, 140) ?? "";
      if (k === "closed" && typeof x === "string") v.closed = cleanLine(x, 200) ?? "";
    }
    cache = { v, at: Date.now() };
    return v;
  } catch (e) {
    console.error("settings:", e instanceof Error ? e.message : e);
    return cache?.v ?? DEFAULT_SETTINGS;
  }
}

/** the admin's change; `by` is who made it (kept on the row) */
export async function saveSettings(patch: Partial<Settings>, by: string) {
  if (patch.open !== undefined && typeof patch.open !== "boolean") throw new ShopError("open must be true or false", 400);
  if (patch.margin !== undefined && !okMargin(patch.margin)) throw new ShopError("margin must be whole rupees, 0 to 5000", 400);
  if (patch.notice !== undefined) patch.notice = cleanLine(patch.notice, 140) ?? "";
  if (patch.closed !== undefined) patch.closed = cleanLine(patch.closed, 200) ?? "";
  await table();
  for (const [k, v] of Object.entries(patch)) {
    if (v === undefined) continue;
    await query(
      "INSERT INTO settings (key, value, updated_at, updated_by) VALUES ($1, $2::jsonb, now(), $3) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now(), updated_by = EXCLUDED.updated_by",
      [k, JSON.stringify(v), by.slice(0, 120)],
    );
  }
  cache = null;
  return getSettings();
}

/** taking new orders: every key set and the admin's switch on */
export const shopAccepting = async () => shopOpen() && (await getSettings()).open;
