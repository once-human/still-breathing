import { SHOP } from "@/content/shop";
import { cleanBag } from "@/lib/shop/catalog";
import { razorpayKeys, shopOpen } from "@/lib/shop/config";
import { failed, guardWrite, json } from "@/lib/shop/guard";
import { checkDetails } from "@/lib/shop/india";
import { startOrder } from "@/lib/shop/orders";
import type { PayStart } from "@/lib/shop/types";

export const dynamic = "force-dynamic";

/**
 * { bag: [{ design, size, quantity }], details }: the bag is checked against what's for sale and priced here, the
 * amount is fixed on a Razorpay order, and the page gets only what it needs to open Razorpay's payment window.
 */
export async function POST(req: Request) {
  if (!shopOpen()) return json({ error: "the shop isn't taking orders right now" }, 503);
  const g = await guardWrite(req, "checkout", 8);
  if ("fail" in g) return g.fail;
  const b = g.body as { bag?: unknown; details?: unknown };
  const bag = cleanBag(b?.bag);
  if (!bag) return json({ error: "the bag changed: open it again and check it" }, 400);
  const d = checkDetails(b?.details);
  if ("error" in d) return json({ error: d.error, field: d.field }, 400);
  const x = d.ok;
  try {
    const o = await startOrder(bag, { name: x.name, email: x.email, phone: x.phone }, x);
    const start: PayStart = {
      orderId: o.id,
      keyId: razorpayKeys()!.id,
      rzpOrderId: o.rzpOrderId,
      amount: o.total * 100,
      name: SHOP.merchant,
      prefill: { name: x.name, email: x.email, contact: `+91${x.phone}` },
    };
    return json(start);
  } catch (e) {
    return failed(e);
  }
}
