import { createHmac, timingSafeEqual } from "node:crypto";
import { razorpayKeys } from "./config";
import { ShopError } from "./errors";

/**
 * Payments: Razorpay's Orders API and Standard Checkout. The amount is fixed on Razorpay's order by the server, so
 * what the page shows can't change what's charged. Card and UPI details go from the buyer to Razorpay only.
 */
const API = "https://api.razorpay.com/v1";

async function call<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const k = razorpayKeys();
  if (!k) throw new ShopError("payments not set up", 503);
  const res = await fetch(API + path, {
    method: init.method ?? "GET",
    headers: { Authorization: "Basic " + Buffer.from(`${k.id}:${k.secret}`).toString("base64"), "Content-Type": "application/json" },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  }).catch(() => null);
  if (!res) throw new ShopError("payments unreachable");
  const j = (await res.json().catch(() => ({}))) as T & { error?: { description?: string } };
  if (!res.ok) throw new ShopError(`razorpay ${res.status}: ${j.error?.description ?? ""}`);
  return j;
}

export type RzpOrder = { id: string; amount: number; amount_paid: number; currency: string; receipt: string; status: "created" | "attempted" | "paid" };
export type RzpPayment = {
  id: string; order_id: string; status: "created" | "authorized" | "captured" | "refunded" | "failed"; amount: number; method: string;
  created_at: number; vpa?: string | null; bank?: string | null; wallet?: string | null; card?: { network?: string; last4?: string } | null;
  amount_refunded?: number; refund_status?: "partial" | "full" | null;
  /** Razorpay's fee and the GST on it, in paise (on a captured payment) */
  fee?: number | null; tax?: number | null; captured_at?: number | null; email?: string; contact?: string;
};
export type RzpRefund = { id: string; payment_id: string; amount: number; status: "pending" | "processed" | "failed"; created_at: number; speed_processed?: string };

/** amount in paise; receipt is our order number (unique: Razorpay refuses a second order with the same one) */
export const createPayment = (amountPaise: number, receipt: string, notes: Record<string, string>) =>
  call<RzpOrder>("/orders", { method: "POST", body: { amount: amountPaise, currency: "INR", receipt, notes } });

export const fetchPayment = (rzpOrderId: string) => call<RzpOrder>(`/orders/${encodeURIComponent(rzpOrderId)}`);
export const fetchPayments = (rzpOrderId: string) => call<{ items: RzpPayment[] }>(`/orders/${encodeURIComponent(rzpOrderId)}/payments`);

/** a refund back the way it was paid, at normal speed: free, and banks show it in 5–7 working days (instant refunds
 *  cost a fee each, so they aren't used) */
export const refundPayment = (paymentId: string, amountPaise: number, receipt: string) =>
  call<RzpRefund>(`/payments/${encodeURIComponent(paymentId)}/refund`, { method: "POST", body: { amount: amountPaise, speed: "normal", receipt } });

/** one payment, with Razorpay's fee and tax */
export const paymentById = (paymentId: string) => call<RzpPayment>(`/payments/${encodeURIComponent(paymentId)}`);

/** any read from Razorpay's API (settlements, refunds, disputes), GET only: for the admin's views */
export function rzpGet<T = unknown>(path: string): Promise<T> {
  if (!/^\/[\w\-/]*(\?[\w\-=&[\].%]*)?$/.test(path) || path.includes("..")) throw new ShopError("bad razorpay path", 400);
  return call<T>(path);
}
export const fetchRefund = (refundId: string) => call<RzpRefund>(`/refunds/${encodeURIComponent(refundId)}`);

const sameHex = (a: string, b: string) => {
  const x = Buffer.from(a, "utf8"), y = Buffer.from(b, "utf8");
  return x.length === y.length && timingSafeEqual(x, y);
};

/** the checkout's answer: hex HMAC-SHA256 of "<our razorpay order id>|<payment id>" with the key secret */
export function paymentSigned(rzpOrderId: string, paymentId: string, signature: string) {
  const k = razorpayKeys();
  if (!k) return false;
  return sameHex(createHmac("sha256", k.secret).update(`${rzpOrderId}|${paymentId}`).digest("hex"), signature);
}

/** a webhook: hex HMAC-SHA256 of the raw body with the webhook secret, in X-Razorpay-Signature */
export function webhookSigned(raw: Buffer, signature: string | null) {
  const k = razorpayKeys();
  if (!k || !signature) return false;
  return sameHex(createHmac("sha256", k.webhook).update(raw).digest("hex"), signature);
}
