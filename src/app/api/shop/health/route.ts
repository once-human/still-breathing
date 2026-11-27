import { NextResponse } from "next/server";
import { razorpayKeys, shopOpen } from "@/lib/shop/config";
import { partnerCheck } from "@/lib/shop/partner";

export const dynamic = "force-dynamic";

/** Is the shop wired up: payments live or test, and does the print partner accept this deployment's keys.
 *  Says only yes or no and the partner's status code, never a key. Cached five minutes at the edge. */
export async function GET() {
  const rzp = razorpayKeys();
  return NextResponse.json(
    { open: shopOpen(), payments: rzp ? (rzp.test ? "test" : "live") : null, print: await partnerCheck() },
    { headers: { "Cache-Control": "public, s-maxage=300, stale-while-revalidate=600" } },
  );
}
