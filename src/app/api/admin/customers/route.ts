import { audit } from "@/lib/admin/auth";
import { adminWrite, failedAction, ok, str } from "@/lib/admin/guard";
import { addNote } from "@/lib/admin/log";
import { deleteAccount, loadAccount, saveAccount, signOutEverywhere, validEmail } from "@/lib/shop/account";
import { deleteOrder, listOrders } from "@/lib/shop/orders";

export const dynamic = "force-dynamic";

/**
 * One action on one customer: { email, action: note | edit | signout | delete, ... }. Delete takes the account (details,
 * saved addresses, sessions) and every order of theirs that can go: never paid, or cancelled with the refund done. A
 * paid order still going blocks it, so no real sale is wiped.
 */
export async function POST(req: Request) {
  const g = await adminWrite(req);
  if ("fail" in g) return g.fail;
  const email = str(g.body.email, 120).toLowerCase();
  if (!validEmail(email)) return ok({ error: "no such customer" }, 400);
  const action = str(g.body.action, 20) || "note";
  const target = `customer:${email}`;
  try {
    switch (action) {
      case "note": {
        const text = str(g.body.text, 2000);
        if (!text) return ok({ error: "empty note" }, 400);
        await addNote(target, g.admin.email, text);
        await audit(g.admin.email, "customer.note", target, { length: text.length }, g.ip);
        return ok({ message: "saved" });
      }
      case "edit": {
        const a = await loadAccount(email);
        if (!a) return ok({ error: "no account to edit (a guest's details live on their orders)" }, 404);
        const name = str(g.body.name, 80), phone = str(g.body.phone, 10).replace(/\D/g, "");
        if (!name) return ok({ error: "a name" }, 400);
        if (phone && !/^[6-9]\d{9}$/.test(phone)) return ok({ error: "phone: 10 digits, starting 6 to 9" }, 400);
        const before = { name: a.name, phone: a.phone };
        await saveAccount({ ...a, name, phone });
        await audit(g.admin.email, "customer.edit", target, { before, after: { name, phone } }, g.ip);
        return ok({ message: "saved" });
      }
      case "signout": {
        const n = await signOutEverywhere(email);
        await audit(g.admin.email, "customer.signout", target, { sessions: n }, g.ip);
        return ok({ message: `signed out of ${n} session${n === 1 ? "" : "s"}` });
      }
      case "delete": {
        const orders = await listOrders({ email, limit: 200 });
        const live = orders.filter((o) => !(o.stage === "paying" || o.stage === "cancelled"));
        if (live.length) return ok({ error: `${live.length} paid order${live.length > 1 ? "s are" : " is"} still going (${live.map((o) => o.id).join(", ")}): cancel first` }, 409);
        const gone: string[] = [];
        for (const o of orders) gone.push((await deleteOrder(o.id)).id);
        const { sessions } = await deleteAccount(email);
        await audit(g.admin.email, "customer.delete", target, { orders: gone, sessions }, g.ip);
        return ok({ message: `deleted, with ${gone.length} order${gone.length === 1 ? "" : "s"}` });
      }
      default:
        return ok({ error: "unknown action" }, 400);
    }
  } catch (e) {
    return failedAction(g.admin, `customer.${action}`, target, e, g.ip);
  }
}
