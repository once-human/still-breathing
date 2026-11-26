import { NextResponse } from "next/server";
import { payView } from "@/lib/shop/catalog";

export const dynamic = "force-dynamic";

/** Whether the shop can take a payment now, and the sizes each shirt can be paid for in. Cached briefly at the edge. */
export async function GET() {
  return NextResponse.json(await payView(), { headers: { "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300" } });
}
