import { revalidateTag } from "next/cache";
import { NextResponse } from "next/server";
import { webhookSecret } from "@/lib/shop/config";
import { CATALOG_TAG } from "@/lib/shop/catalog";
import { firstTime, verifyShopify } from "@/lib/shop/webhook";

export const dynamic = "force-dynamic";

/** the topics we act on: anything that changes what a shirt costs or whether a size can be bought */
const CATALOG_TOPICS = new Set(["products/update", "products/delete", "products/create", "inventory_levels/update"]);

/**
 * Shopify → us. Only signed deliveries count; anything else gets a 401 and changes nothing. A good delivery refreshes
 * the cached catalog. Orders, payment, printing and the emails never pass through here: Shopify, Razorpay and the
 * print partner's app handle those among themselves.
 */
export async function POST(req: Request) {
  const secret = webhookSecret();
  if (!secret) return new NextResponse(null, { status: 503 });
  const raw = await req.text();
  if (raw.length > 1_000_000) return new NextResponse(null, { status: 413 });
  if (!verifyShopify(raw, req.headers.get("x-shopify-hmac-sha256"), secret)) return new NextResponse(null, { status: 401 });
  const topic = req.headers.get("x-shopify-topic") ?? "";
  if (firstTime(req.headers.get("x-shopify-webhook-id")) && CATALOG_TOPICS.has(topic)) revalidateTag(CATALOG_TAG, { expire: 0 });
  return new NextResponse(null, { status: 200 });
}
