import { audit } from "@/lib/admin/auth";
import { exec } from "@/lib/admin/db";
import { adminWrite, failedAction, ok, str } from "@/lib/admin/guard";
import { settlementOf } from "@/lib/admin/razorpay";
import { MAIL_KINDS, addNote, adminCancel, adminRefund, loadOrder, resendEmail, retryPrint, sync, validId, type MailKind } from "@/lib/shop/orders";
import { paymentById } from "@/lib/shop/razorpay";

export const dynamic = "force-dynamic";
export const maxDuration = 30;


/**
 * One action on one order: { action: note | sync | fees | retry | cancel | refund | resend, ... }. The money-moving
 * ones (cancel, refund) go through the shop's own functions under the order's lock, exactly as the buyer's own cancel
 * does, so nothing is ever done twice. Every action, done or failed, is in the audit log.
 */
export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await adminWrite(req);
  if ("fail" in g) return g.fail;
  const { admin, body, ip } = g;
  const { id } = await params;
  if (!validId(id)) return ok({ error: "no such order" }, 404);
  const o = await loadOrder(id);
  if (!o) return ok({ error: "no such order" }, 404);
  const action = str(body.action, 20);
  const log = (what: string, detail: unknown = null) => audit(admin.email, `order.${what}`, id, detail, ip);

  try {
    switch (action) {
      case "note": {
        const text = str(body.text, 2000);
        if (!text) return ok({ error: "empty note" }, 400);
        await addNote(id, text, admin.email);
        await log("note", { length: text.length });
        return ok({ message: "saved" });
      }
      case "sync": {
        const n = await sync(id);
        await log("sync", { stage: n?.stage, status: n?.partnerRaw ?? null });
        return ok({ message: `qikink says: ${n?.partnerRaw ?? "nothing new"}` });
      }
      case "fees": {
        if (!o.payment?.id) return ok({ error: "no payment on this order" }, 409);
        const p = await paymentById(o.payment.id);
        const st = await settlementOf(o.payment.id, p.captured_at ?? p.created_at).catch(() => null);
        const detail = [p.method, p.vpa, p.bank, p.wallet, p.card?.network, p.card?.last4].filter(Boolean).join(" · ");
        await exec(
          `INSERT INTO admin_payments (payment_id, order_id, fee, tax, method, detail, settlement_id, settled_at, fetched_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, now())
           ON CONFLICT (payment_id) DO UPDATE SET fee = EXCLUDED.fee, tax = EXCLUDED.tax, method = EXCLUDED.method, detail = EXCLUDED.detail,
             settlement_id = EXCLUDED.settlement_id, settled_at = EXCLUDED.settled_at, fetched_at = now()`,
          [p.id, id, p.fee == null ? null : p.fee / 100, p.tax == null ? null : p.tax / 100, p.method, detail, st?.id ?? null, st?.at ?? null],
        );
        await log("fees", { fee: p.fee == null ? null : p.fee / 100, settlement: st?.id ?? null });
        return ok({ message: `fee ${p.fee == null ? "not given" : `₹${(p.fee / 100).toFixed(2)}`}${st ? `, settled in ${st.id}` : ", not settled yet"}` });
      }
      case "retry": {
        const n = await retryPrint(id, admin.email);
        await log("send-to-print", { stage: n.stage, qikink: n.partnerId ?? null, problem: n.problem ?? null });
        return n.partnerId ? ok({ message: `with qikink as ${n.partnerId}` }) : ok({ error: n.problem ?? "qikink didn't take it" }, 502);
      }
      case "cancel": {
        const refund = str(body.refund, 20) !== "no refund";
        const n = await adminCancel(id, { refund }, admin.email);
        const r = n.refunds?.[n.refunds.length - 1];
        await log("cancel", { refund, refundId: r?.id ?? null, amount: r?.amount ?? null, status: r?.status ?? null });
        return ok({ message: refund ? `cancelled; refund ${r?.status ?? "?"}` : "cancelled, not refunded" });
      }
      case "refund": {
        const amount = Number(body.amount);
        if (!Number.isInteger(amount) || amount < 1 || amount > o.total) return ok({ error: `whole rupees, ₹1 to ₹${o.total}` }, 400);
        const reason = str(body.reason, 140);
        const n = await adminRefund(id, amount, reason, admin.email);
        const r = n.refunds?.[n.refunds.length - 1];
        await log("refund", { amount, reason: reason || null, refundId: r?.id ?? null, status: r?.status ?? null });
        return ok({ message: `refund ${r?.id ?? ""}: ${r?.status ?? "?"}` });
      }
      case "resend": {
        const kind = str(body.kind, 20).toLowerCase() as MailKind;
        if (!(MAIL_KINDS as readonly string[]).includes(kind)) return ok({ error: `one of: ${MAIL_KINDS.join(", ")}` }, 400);
        await resendEmail(id, kind, admin.email);
        await log("resend", { kind, to: o.contact.email });
        return ok({ message: `sent the ${kind} email to ${o.contact.email}` });
      }
      default:
        return ok({ error: "unknown action" }, 400);
    }
  } catch (e) {
    return failedAction(admin, `order.${action}`, id, e, ip);
  }
}
