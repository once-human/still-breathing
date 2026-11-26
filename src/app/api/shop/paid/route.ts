import { failed, guardWrite, json } from "@/lib/shop/guard";
import { advance, loadOrder, orderPath, validId } from "@/lib/shop/orders";
import { paymentSigned } from "@/lib/shop/razorpay";

export const dynamic = "force-dynamic";

/**
 * The payment window's answer. Its signature proves Razorpay sent it for our order; even so the order only moves on
 * once Razorpay's own API says the order is paid in full (advance), and the webhook would move it on anyway.
 */
export async function POST(req: Request) {
  const g = await guardWrite(req, "paid", 10);
  if ("fail" in g) return g.fail;
  const b = g.body as Record<string, unknown>;
  const id = String(b?.orderId ?? ""), pay = String(b?.razorpay_payment_id ?? ""), rzp = String(b?.razorpay_order_id ?? ""), sig = String(b?.razorpay_signature ?? "");
  if (!validId(id) || !/^pay_\w+$/.test(pay) || !/^order_\w+$/.test(rzp) || !/^[a-f0-9]{64}$/.test(sig)) return json({ error: "bad request" }, 400);
  try {
    const o = await loadOrder(id);
    if (!o || o.rzpOrderId !== rzp || !paymentSigned(o.rzpOrderId, pay, sig)) return json({ error: "that payment doesn't match this order" }, 400);
    await advance(id);
    return json({ url: orderPath(id) });
  } catch (e) {
    return failed(e);
  }
}
