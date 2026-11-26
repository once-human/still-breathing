import { sessionEmail } from "@/lib/shop/account";
import { shopOpen } from "@/lib/shop/config";
import { failed, guardWrite, json } from "@/lib/shop/guard";
import { checkDetails } from "@/lib/shop/india";
import { cancel, changeAddress, orderFor } from "@/lib/shop/orders";

export const dynamic = "force-dynamic";

/**
 * The buyer's own changes to an order, by `action`, allowed only before it goes to print (the hour after paying):
 *   cancel {id, k?}             refunded in full, back the way it was paid
 *   address {id, k?, details}   where it goes (the email stays)
 * The order's link key or the signed-in buyer's session proves it's theirs.
 */
export async function POST(req: Request) {
  if (!shopOpen()) return json({ error: "the shop isn't taking changes right now" }, 503);
  const g = await guardWrite(req, "order-change", 10);
  if ("fail" in g) return g.fail;
  const b = (g.body ?? {}) as { action?: string; id?: unknown; k?: unknown; details?: unknown };
  const id = typeof b.id === "string" ? b.id : "";
  const k = typeof b.k === "string" ? b.k : null;
  try {
    const mine = await orderFor(id, k, await sessionEmail());
    if (!mine) return json({ error: "no such order" }, 404);
    if (b.action === "cancel") {
      await cancel(id);
      return json({ ok: true });
    }
    if (b.action === "address") {
      const d = checkDetails({ ...(b.details as object), email: mine.o.contact.email });
      if ("error" in d) return json({ error: d.error, field: d.field }, 400);
      const { email: _e, ...ship } = d.ok;
      void _e;
      await changeAddress(id, ship);
      return json({ ok: true });
    }
    return json({ error: "unknown action" }, 400);
  } catch (e) {
    return failed(e);
  }
}
