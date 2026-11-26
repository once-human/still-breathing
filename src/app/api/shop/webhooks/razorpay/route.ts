import { NextResponse } from "next/server";
import { ipOf, limited } from "@/lib/shop/guard";
import { kv, once } from "@/lib/shop/kv";
import { advance, orderForPayment } from "@/lib/shop/orders";
import { webhookSigned } from "@/lib/shop/razorpay";

export const dynamic = "force-dynamic";

/**
 * Razorpay → us, for a payment whose buyer closed the tab before the page heard back. Signed over the raw bytes
 * (X-Razorpay-Signature); each event acted on once (x-razorpay-event-id); acting means advance(), which re-checks
 * the payment with Razorpay and is itself idempotent. Anything unsigned changes nothing.
 */
export async function POST(req: Request) {
  if (await limited(`rzp-hook:${ipOf(req)}`, 300, 60_000)) return new NextResponse(null, { status: 429 });
  const raw = Buffer.from(await req.arrayBuffer());
  if (raw.length > 200_000) return new NextResponse(null, { status: 413 });
  if (!webhookSigned(raw, req.headers.get("x-razorpay-signature"))) return new NextResponse(null, { status: 401 });
  let ev: { event?: string; payload?: { payment?: { entity?: { order_id?: string } }; order?: { entity?: { id?: string } } } };
  try {
    ev = JSON.parse(raw.toString("utf8"));
  } catch {
    return new NextResponse(null, { status: 400 });
  }
  if (ev.event !== "order.paid" && ev.event !== "payment.captured") return new NextResponse(null, { status: 200 });
  const eventId = req.headers.get("x-razorpay-event-id");
  const rzpOrder = ev.payload?.order?.entity?.id ?? ev.payload?.payment?.entity?.order_id;
  try {
    const id = rzpOrder ? await orderForPayment(rzpOrder) : null;
    if (!id) return new NextResponse(null, { status: 200 }); // not one of ours (a payment link, a test from the dashboard)
    if (eventId && !(await once(`rzp-evt:${eventId}`, 7 * 86400))) return new NextResponse(null, { status: 200 });
    await advance(id);
    return new NextResponse(null, { status: 200 });
  } catch (e) {
    console.error("razorpay webhook:", e instanceof Error ? e.message : e);
    // 5xx: Razorpay retries; the event mark is cleared so the retry is acted on
    if (eventId) await kv("DEL", `rzp-evt:${eventId}`).catch(() => {});
    return new NextResponse(null, { status: 500 });
  }
}
