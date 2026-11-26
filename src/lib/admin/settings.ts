import "server-only";
import { DEFAULT_SETTINGS, getSettings as shopSettings, saveSettings as saveShop, type Settings as ShopSettings } from "@/lib/shop/settings";
import { exec, rows } from "./db";

/**
 * Settings, as the admin sees them: the shop's own (open, margin: read by checkout and the catalog, saved through the
 * shop's settings.ts) and the admin's few for working out margins (kept in the same table under admin.* keys, read
 * by nothing else). Server only.
 */
type AdminOnly = {
  /** Razorpay's fee as a share of the order (2% + 18% GST), for orders whose actual fee isn't fetched yet */
  feeRate: number;
  /** what the partner charges to send one parcel (air, under 500 g: ₹54 + 18%) */
  shipPerParcel: number;
  /** how many shirts go in one 500 g parcel */
  shirtsPerParcel: number;
  /** the least to keep in the partner's wallet, for the reminder */
  lowWallet: number;
};
export type Settings = ShopSettings & AdminOnly;

const ADMIN_DEFAULTS: AdminOnly = { feeRate: 0.0236, shipPerParcel: 63.72, shirtsPerParcel: 2, lowWallet: 2000 };
export const DEFAULTS: Settings = { ...DEFAULT_SETTINGS, ...ADMIN_DEFAULTS };

const BOUNDS: Record<keyof AdminOnly, [number, number]> = { feeRate: [0, 0.1], shipPerParcel: [0, 1000], shirtsPerParcel: [1, 20], lowWallet: [0, 100000] };

let cache: { at: number; s: AdminOnly } | null = null;

export async function getSettings(fresh = false): Promise<Settings> {
  const shop = await shopSettings();
  if (fresh || !cache || Date.now() - cache.at > 30_000) {
    const r = await rows<{ key: string; value: unknown }>("SELECT key, value FROM settings WHERE key LIKE 'admin.%'").catch(() => []);
    const s = { ...ADMIN_DEFAULTS };
    for (const { key, value } of r) {
      const k = key.slice(6) as keyof AdminOnly;
      if (k in BOUNDS && typeof value === "number") s[k] = value;
    }
    cache = { at: Date.now(), s };
  }
  return { ...shop, ...cache.s };
}

/** checked key by key; returns what changed (from → to) */
export async function saveSettings(patch: Record<string, unknown>, by: string) {
  const now = await getSettings(true);
  const changed: Record<string, [unknown, unknown]> = {};
  const shop: Partial<ShopSettings> = {};
  for (const [k, v] of Object.entries(patch)) {
    if (!(k in DEFAULTS)) throw Object.assign(new Error(`unknown setting ${k}`), { status: 400 });
    if (now[k as keyof Settings] === v) continue;
    if (k === "open" || k === "margin") {
      (shop as Record<string, unknown>)[k] = v;
    } else {
      const [min, max] = BOUNDS[k as keyof AdminOnly];
      if (typeof v !== "number" || !Number.isFinite(v) || v < min || v > max) throw Object.assign(new Error(`${k}: a number from ${min} to ${max}`), { status: 400 });
      await exec(
        "INSERT INTO settings (key, value, updated_at, updated_by) VALUES ($1, $2::jsonb, now(), $3) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now(), updated_by = EXCLUDED.updated_by",
        [`admin.${k}`, JSON.stringify(v), by],
      );
    }
    changed[k] = [now[k as keyof Settings], v];
  }
  if (Object.keys(shop).length) await saveShop(shop, by);
  cache = null;
  return changed;
}
