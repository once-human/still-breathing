import { createHash, timingSafeEqual } from "node:crypto";
import { NextResponse } from "next/server";
import { shopOpen } from "@/lib/shop/config";
import { syncAll } from "@/lib/shop/orders";
import { kv } from "@/lib/shop/kv";
import { foldOld } from "@/lib/visits/server";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

/**
 * The sync job (GitHub Actions every 3 hours, .github/workflows/shop-sync.yml): only with the shared CRON_SECRET.
 * Moves orders on, folds visits older than the kept log into daily counts, and notes when it ran (the admin's status).
 */
export async function POST(req: Request) {
  const secret = process.env.CRON_SECRET?.trim();
  const got = req.headers.get("authorization") ?? "";
  const h = (s: string) => createHash("sha256").update(s).digest();
  if (!secret || secret.length < 32 || !timingSafeEqual(h(got), h(`Bearer ${secret}`))) return new NextResponse(null, { status: 401 });
  await kv("SET", "cron:last", new Date().toISOString()).catch(() => {});
  const visits = await foldOld().catch(() => null);
  if (!shopOpen()) return NextResponse.json({ open: false, visits });
  return NextResponse.json({ open: true, orders: await syncAll(), visits });
}
