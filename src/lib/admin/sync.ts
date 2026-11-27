import "server-only";
import { after } from "next/server";
import { shopOpen } from "@/lib/shop/config";
import { kv, once } from "@/lib/shop/kv";
import { syncAll } from "@/lib/shop/orders";
import { foldOld, importOld } from "@/lib/visits/server";

/**
 * The sync job's work: orders moved on (late payments, print hand-offs, tracking, refunds), old visits folded into
 * daily counts, and when it ran noted for the admin. GitHub runs it every 3 hours, but GitHub skips scheduled runs
 * when it's busy, so opening the admin runs it too once the last run is over 3 hours old.
 */
export async function syncNow() {
  await kv("SET", "cron:last", new Date().toISOString()).catch(() => {});
  await importOld().catch((e) => console.error("old visits:", e));
  const visits = await foldOld().catch(() => null);
  if (!shopOpen()) return { open: false, visits };
  return { open: true, orders: await syncAll(), visits };
}

export const lastSync = () => kv<string | null>("GET", "cron:last").catch(() => null);

/** after the admin page is sent, if the last sync is old: at most once every 10 minutes */
export async function syncIfLate() {
  const last = await lastSync();
  if (last && Date.now() - Date.parse(last) < 3 * 3600_000) return;
  if (!(await once("sync:admin", 600).catch(() => false))) return;
  after(() => syncNow().then(() => undefined, (e) => console.error("admin sync:", e)));
}
