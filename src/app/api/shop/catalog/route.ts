import { NextResponse } from "next/server";
import { catalogView } from "@/lib/shop/catalog";

export const dynamic = "force-dynamic";

/** Whether the shop is open, each shirt's price and its sizes. Public facts only; cached briefly at the edge. */
export async function GET() {
  return NextResponse.json(catalogView(), { headers: { "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300" } });
}
