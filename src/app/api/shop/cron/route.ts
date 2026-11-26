import { createHash, timingSafeEqual } from "node:crypto";
import { NextResponse } from "next/server";
import { shopOpen } from "@/lib/shop/config";
import { syncAll } from "@/lib/shop/orders";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

/** The sync job (GitHub Actions every 3 hours, .github/workflows/shop-sync.yml): only with the shared CRON_SECRET. */
export async function POST(req: Request) {
  const secret = process.env.CRON_SECRET?.trim();
  const got = req.headers.get("authorization") ?? "";
  const h = (s: string) => createHash("sha256").update(s).digest();
  if (!secret || secret.length < 32 || !timingSafeEqual(h(got), h(`Bearer ${secret}`))) return new NextResponse(null, { status: 401 });
  if (!shopOpen()) return NextResponse.json({ open: false });
  return NextResponse.json({ open: true, orders: await syncAll() });
}
