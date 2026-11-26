import { NextResponse } from "next/server";
import { catalogView } from "@/lib/shop/catalog";

/** Prices and which sizes can be bought, for the buy buttons. Public facts only; cached briefly at the edge. */
export async function GET() {
  try {
    return NextResponse.json(await catalogView(), { headers: { "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300" } });
  } catch (e) {
    console.error("shop catalog:", e instanceof Error ? e.message : e);
    // Shopify not answering reads as not open, never as a button that would fail
    return NextResponse.json({ open: false }, { headers: { "Cache-Control": "no-store" } });
  }
}
