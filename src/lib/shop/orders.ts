import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { OPERATOR } from "@/content/policies";
import { SHOP } from "@/content/shop";
import { DESIGNS, type Design, type Size } from "@/content/tee";
import { SITE_URL } from "@/lib/site";
import { linkOrder, rememberAddress } from "./account";
import { ownerEmail, shopSecret } from "./config";
import { sendEmail } from "./email";
import { ShopError } from "./errors";
import { getJson, kv, once, query, setJson, withLock } from "./kv";
import { partnerStatus, sendToPrint, type ShipTo } from "./partner";
import { prices } from "./products";
import { createPayment, fetchPayment, fetchPayments, fetchRefund, refundPayment, type RzpPayment } from "./razorpay";

/**
 * An order, from the moment the buyer goes to pay to the shirt in their hands:
 *   paying → paid (Razorpay confirms) → printing (the partner has it) → shipped → out → delivered
 *                         ↘ cancelled (before it goes to print: by the buyer in the first hour, or by sahn)
 * A paid order waits an hour before it goes to print, so the buyer can still cancel it or fix the address themselves.
 * Every step is taken at most once (a lock per order, and each email sent once), so the checkout's answer, the
 * webhook, the order page, the sync job and the admin can all push an order on without ever doubling anything.
 * The admin changes orders only through the functions here.
 */
export type Stage = "paying" | "paid" | "printing" | "shipped" | "out" | "delivered" | "attention" | "cancelled";

/** the change-of-mind hour: after paying, the order waits this long before going to print */
export const HOLD_MS = 3600_000;

/** one thing that happened to an order, when it happened (or when we first saw it). admin and note are sahn's own,
 *  never shown to the buyer. */
export type EventKind = "placed" | "paid" | "address" | "printing" | "partner" | "shipped" | "out" | "delivered" | "trouble" | "cancelled" | "refunded" | "admin" | "note";
export type OrderEvent = { at: string; kind: EventKind; note?: string };
const PRIVATE: EventKind[] = ["admin", "note"];

export type Line = { design: Design; size: Size; quantity: number; unitPrice: number };
export type Refund = { id: string; amount: number; status: "pending" | "processed" | "failed"; at: string; doneAt?: string; reason?: string };

export type Order = {
  id: string;
  createdAt: string;
  stage: Stage;
  lines: Line[];
  total: number;
  contact: { name: string; email: string; phone: string };
  ship: ShipTo;
  rzpOrderId: string;
  paidAt?: string;
  partnerId?: string;
  partnerRaw?: string | null;
  tracking?: { awb: string | null; courier: string | null; url: string | null };
  shippedAt?: string;
  deliveredAt?: string;
  syncedAt?: string;
  problem?: string;
  /** everything that happened, oldest first */
  events?: OrderEvent[];
  payment?: { id: string; method: string; label: string; at: string };
  /** every refund, oldest first (a cancel is one full refund; the admin can make partial ones) */
  refunds?: Refund[];
};

const now = () => new Date().toISOString();
const note = (o: Order, kind: EventKind, text?: string, at = now()) => (o.events ??= []).push({ at, kind, ...(text ? { note: text } : {}) });

/** how it was paid, in words: "UPI", "card · visa 4242", "net banking · HDFC", "wallet · paytm" */
const paidWith = (p: RzpPayment) =>
  p.method === "upi" ? "UPI"
  : p.method === "card" ? `card${p.card?.network ? ` · ${p.card.network.toLowerCase()}` : ""}${p.card?.last4 ? ` ${p.card.last4}` : ""}`
  : p.method === "netbanking" ? `net banking${p.bank ? ` · ${p.bank}` : ""}`
  : p.method === "wallet" ? `wallet${p.wallet ? ` · ${p.wallet}` : ""}`
  : p.method;

/** when it can still be cancelled or its address fixed: paid, not yet with the partner */
export const changeable = (o: Order) => !o.partnerId && (o.stage === "paid" || o.stage === "attention") && !!o.paidAt;
const released = (o: Order) => !!o.paidAt && Date.now() - Date.parse(o.paidAt) >= HOLD_MS;
/** rupees refunded or on their way back */
export const refunded = (o: Order) => (o.refunds ?? []).filter((r) => r.status !== "failed").reduce((t, r) => t + r.amount, 0);
const pendingRefund = (o: Order) => (o.refunds ?? []).some((r) => r.status === "pending");

const OPEN = "orders:open";
const key = (id: string) => `order:${id}`;

/** order numbers: S + yymmdd + 4 letters/digits (11 characters, the partner takes at most 15, letters and digits only) */
const ALPHA = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
const newId = () => {
  const d = new Date(Date.now() + 5.5 * 3600_000).toISOString().slice(2, 10).replace(/-/g, "");
  return "S" + d + Array.from(randomBytes(4), (b) => ALPHA[b % ALPHA.length]).join("");
};
export const validId = (v: string) => /^S\d{6}[A-Z0-9]{4}$/.test(v);

/** the secret in an order's link: only the buyer's emails and their browser after paying ever have it */
export function linkKey(id: string) {
  const s = shopSecret();
  if (!s) throw new ShopError("shop not set up", 503);
  return createHmac("sha256", s).update(`order:${id}`).digest("base64url").slice(0, 24);
}
export const keyMatches = (id: string, k: string) => {
  const a = Buffer.from(linkKey(id)), b = Buffer.from(k);
  return a.length === b.length && timingSafeEqual(a, b);
};
export const orderPath = (id: string) => `/order/${id}?k=${linkKey(id)}`;

export const loadOrder = (id: string) => getJson<Order>(key(id));
const save = (o: Order) => setJson(key(o.id), o, o.stage === "paying" ? 3 : 400);

/** The buyer is about to pay: price the bag here (products.ts, the one price rule) and fix that amount on a Razorpay order. */
export async function startOrder(bag: { design: Design; size: Size; quantity: number }[], contact: Order["contact"], ship: ShipTo) {
  const price = await prices();
  const lines: Line[] = bag.map((l) => ({ ...l, unitPrice: price[l.design] }));
  if (lines.some((l) => !Number.isInteger(l.unitPrice) || l.unitPrice <= 0)) throw new ShopError("a shirt has no price");
  const total = lines.reduce((t, l) => t + l.unitPrice * l.quantity, 0);
  const id = newId();
  const rzp = await createPayment(total * 100, id, { order: id });
  if (rzp.amount !== total * 100 || rzp.currency !== "INR") throw new ShopError("payment amount mismatch");
  const o: Order = { id, createdAt: now(), stage: "paying", lines, total, contact, ship, rzpOrderId: rzp.id, events: [] };
  note(o, "placed", undefined, o.createdAt);
  await save(o);
  await linkOrder(contact.email, id);
  await kv("SET", `rzp:${rzp.id}`, id, "EX", 400 * 86400);
  await kv("ZADD", OPEN, Date.now(), id);
  return o;
}

export const orderForPayment = (rzpOrderId: string) => kv<string | null>("GET", `rzp:${rzpOrderId}`);

const site = () => process.env.SHOP_SITE_URL?.replace(/\/$/, "") ?? SITE_URL;
const shirt = (d: Design) => `${DESIGNS[d].no} ${DESIGNS[d].name}${DESIGNS[d].city ? ` ${DESIGNS[d].city}` : ""}`;
const rs = (n: number) => `₹${n.toLocaleString("en-IN")}`;
const itemsText = (o: Order) => o.lines.map((l) => `${shirt(l.design)}, size ${l.size} × ${l.quantity}  ${rs(l.unitPrice * l.quantity)}`).join("\n");
const sign = () => `${SHOP.merchant}${OPERATOR.email ? `\n${OPERATOR.email}` : ""}`;
const istTime = (iso: string) => new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" });

/** the emails a buyer gets; refund:<refund id> is a refund that isn't a cancel */
export type MailKind = "confirmed" | "printing" | "shipped" | "out" | "delivered" | "cancelled" | `refund:${string}` | `address:${number}`;
export const MAIL_KINDS = ["confirmed", "printing", "shipped", "out", "delivered", "cancelled"] as const;

/** an email's subject and words for this order as it is now, or null when there's nothing to say yet */
function emailFor(o: Order, kind: MailKind): [string, string] | null {
  const link = `${site()}${orderPath(o.id)}`;
  const to = `${o.ship.city}, ${o.ship.state} ${o.ship.pin}`;
  const back = (r: Refund) => `${rs(r.amount)} is on its way back${o.payment ? ` to your ${o.payment.label.split(" · ")[0]}` : ""}. banks usually show it within 5–7 working days. refund reference: ${r.id}.`;
  switch (kind) {
    case "confirmed": {
      if (!o.paidAt) return null;
      const until = new Date(Date.parse(o.paidAt) + HOLD_MS).toISOString();
      return [`sahn: order #${o.id} is in`, [
        `hi ${o.contact.name.split(" ")[0]},`,
        `thank you. your order #${o.id} is paid and in. each shirt is made for you from here: ${SHOP.make[0]}–${SHOP.make[1]} days to make, then ${SHOP.road[0]}–${SHOP.road[1]} days on the road. we'll email you the tracking the moment it leaves.`,
        `${itemsText(o)}\npaid ${rs(o.total)}${o.payment ? ` by ${o.payment.label}` : ""}, shipping included`,
        `going to: ${o.ship.name}, ${o.ship.address1}${o.ship.address2 ? `, ${o.ship.address2}` : ""}, ${o.ship.city}, ${o.ship.state} ${o.ship.pin}`,
        ...(changeable(o) && Date.now() < Date.parse(until) ? [`changed your mind, or the address is wrong? until ${istTime(until)} you can cancel (refunded in full) or fix the address yourself on your order's page. after that it goes to print.`] : []),
        `your order, any time: ${link}`,
        sign(),
      ].join("\n\n")];
    }
    case "printing":
      if (!o.partnerId) return null;
      return [`sahn: order #${o.id} is being made`, [
        `your order #${o.id} has gone to print. from here it's printed, checked and packed just for you: about ${SHOP.make[0]}–${SHOP.make[1]} days, then ${SHOP.road[0]}–${SHOP.road[1]} days on the road to ${o.ship.city.toLowerCase()}.`,
        `the address can't be changed from your order's page any more. if something's wrong with it, write back today.`,
        `your order: ${link}`,
        sign(),
      ].join("\n\n")];
    case "out":
      if (!o.events?.some((e) => e.kind === "out")) return null;
      return [`sahn: order #${o.id} is out for delivery`, [
        `your order #${o.id} is out for delivery to ${o.ship.city.toLowerCase()} today.`,
        `keep your phone on: the courier calls before coming.${o.tracking?.url ? ` track it: ${o.tracking.url}` : ""}`,
        sign(),
      ].join("\n\n")];
    case "shipped":
      if (!o.shippedAt || !o.tracking) return null;
      return [`sahn: order #${o.id} is on its way`, [
        `it's left. your order #${o.id} is with the courier${o.tracking.courier ? ` (${o.tracking.courier.toLowerCase()})` : ""}, on its way to ${to}. most parcels get there in ${SHOP.road[0]}–${SHOP.road[1]} days.`,
        o.tracking.url ? `track it: ${o.tracking.url}` : `tracking number: ${o.tracking.awb}`,
        `keep your phone on: the courier calls before delivering. your order: ${link}`,
        sign(),
      ].join("\n\n")];
    case "delivered":
      if (o.stage !== "delivered") return null;
      return [`sahn: order #${o.id} is with you`, [
        `your order #${o.id} has been delivered.`,
        `if anything's wrong with it, write back within 7 days with an unboxing video and photos and we'll put it right.`,
        `wash it cold, inside out, and dry it in the shade. iron on the back, never on the print.`,
        `your order: ${link}`,
        sign(),
      ].join("\n\n")];
    case "cancelled": {
      if (o.stage !== "cancelled" || !o.paidAt) return null;
      const r = o.refunds?.filter((x) => x.status !== "failed").at(-1);
      return [`sahn: order #${o.id} is cancelled`, [
        `your order #${o.id} is cancelled, and nothing will be made or sent.`,
        r ? back(r) : "we'll write to you about your payment.",
        `your order: ${link}`,
        sign(),
      ].join("\n\n")];
    }
    default: {
      if (kind.startsWith("address:")) {
        if (!o.events?.some((e) => e.kind === "address")) return null;
        return [`sahn: a new address for order #${o.id}`, [
          `the address on your order #${o.id} is now:\n${o.ship.name}, ${o.ship.phone}\n${o.ship.address1}${o.ship.address2 ? `, ${o.ship.address2}` : ""}\n${to}`,
          `if this isn't right, write back straight away: it hasn't gone to print yet, so it can still be fixed.`,
          `your order: ${link}`,
          sign(),
        ].join("\n\n")];
      }
      const r = o.refunds?.find((x) => `refund:${x.id}` === kind);
      if (!r || r.status === "failed") return null;
      return [`sahn: a refund on order #${o.id}`, [
        `we've refunded part of your order #${o.id}${r.reason ? `: ${r.reason}` : ""}.`,
        back(r),
        `your order: ${link}`,
        sign(),
      ].join("\n\n")];
    }
  }
}

/** one email per order and kind, ever (a resend passes its own idempotency suffix) */
async function emailOnce(o: Order, kind: MailKind, suffix = "") {
  const m = emailFor(o, kind);
  if (!m || !(await once(`mail:${o.id}:${kind}`, 400 * 86400))) return false;
  try {
    await sendEmail(o.contact.email, m[0], m[1], `${o.id}-${kind}${suffix}`, OPERATOR.email);
    return true;
  } catch (e) {
    await kv("DEL", `mail:${o.id}:${kind}`); // let the next run try again
    throw e;
  }
}
const quietly = (what: string) => (e: unknown) => console.error(`${what} email:`, e instanceof Error ? e.message : e);

/** something only Onkar can sort out: tell him, at most once a day per order and problem */
async function alert(o: Order, problem: string) {
  const to = ownerEmail();
  if (!to || !(await once(`alert:${o.id}:${problem.slice(0, 40)}`, 86400))) return;
  await sendEmail(to, `sahn: order #${o.id} needs you`, `order #${o.id} (${rs(o.total)}, paid ${o.paidAt ?? "?"})\n\n${problem}\n\n${itemsText(o)}\n\nship to: ${o.ship.name}, ${o.ship.city}, ${o.ship.state} ${o.ship.pin}`, `alert-${o.id}-${Date.now() >> 26}`).catch((e) => console.error("alert:", e));
}

/** a new paid order: Onkar hears at once, once */
async function newOrder(o: Order) {
  const to = ownerEmail();
  if (!to || !(await once(`mail:${o.id}:owner`, 400 * 86400))) return;
  const n = o.lines.reduce((t, l) => t + l.quantity, 0);
  await sendEmail(to, `sahn: new order #${o.id}, ${rs(o.total)}`, [
    `${o.contact.name} in ${o.ship.city.toLowerCase()} just paid ${rs(o.total)}${o.payment ? ` by ${o.payment.label}` : ""} for ${n} shirt${n > 1 ? "s" : ""}.`,
    itemsText(o),
    `it goes to print by itself after the change-of-mind hour. open it: ${site()}/admin/orders/${o.id}`,
  ].join("\n\n"), `owner-${o.id}`);
}

/** hand it to the partner; on a refusal the order waits in attention and is tried again every few hours */
async function toPrint(o: Order) {
  try {
    o.partnerId = await sendToPrint(o.id, o.lines, o.ship, o.total, site());
    o.stage = "printing";
    delete o.problem;
    note(o, "printing");
    await emailOnce(o, "printing").catch(quietly("printing"));
    return true;
  } catch (e) {
    const first = o.stage !== "attention";
    o.stage = "attention";
    o.problem = `the print partner didn't take it: ${(e as Error).message}`;
    if (first) note(o, "trouble", "held up before printing; we're on it");
    await alert(o, `${o.problem}\n\nit's tried again every few hours. if the balance is low, top it up and it goes through on the next try.`);
    return false;
  }
}

/**
 * Push a paid order on: confirm the payment with Razorpay itself (never on the browser's word), send the
 * confirmation, and once the change-of-mind hour is over, hand it to the partner. Safe to call any number of times
 * from anywhere.
 */
export async function advance(id: string): Promise<Order | null> {
  const r = await withLock(id, async () => {
    const o = await loadOrder(id);
    if (!o) return null;
    if (o.stage === "paying") {
      const p = await fetchPayment(o.rzpOrderId);
      if (p.status !== "paid" || p.amount_paid !== o.total * 100) return o;
      const pay = (await fetchPayments(o.rzpOrderId).catch(() => ({ items: [] as RzpPayment[] }))).items.find((x) => x.status === "captured");
      o.stage = "paid";
      o.paidAt = pay ? new Date(pay.created_at * 1000).toISOString() : now();
      if (pay) o.payment = { id: pay.id, method: pay.method, label: paidWith(pay), at: o.paidAt };
      note(o, "paid", o.payment?.label, o.paidAt);
      await save(o);
      await rememberAddress(o.contact.email, { ...o.ship, email: o.contact.email }).catch((e) => console.error("address:", e));
      await emailOnce(o, "confirmed").catch(quietly("confirm"));
      await newOrder(o).catch(quietly("new order"));
    }
    if ((o.stage === "paid" || (o.stage === "attention" && !o.partnerId)) && released(o)) {
      await toPrint(o);
      await save(o);
    }
    return o;
  });
  return r ?? (await loadOrder(id));
}

/** the order, under its lock, for a change; a busy lock is "try again", never a silent skip */
async function changing(id: string, fn: (o: Order) => Promise<Order>): Promise<Order> {
  const r = await withLock(id, async () => {
    const o = await loadOrder(id);
    if (!o) throw new ShopError("no such order", 404);
    return fn(o);
  });
  if (!r) throw new ShopError("one moment, it's being updated: try again", 409);
  return r;
}

/** a refund through Razorpay, recorded on the order; a refusal (usually a low balance) changes nothing and tells Onkar */
async function refundNow(o: Order, rupees: number, receipt: string, reason?: string) {
  const payId = o.payment?.id ?? (await fetchPayments(o.rzpOrderId)).items.find((x) => x.status === "captured")?.id;
  if (!payId) throw new ShopError("couldn't find the payment to refund, try again in a minute");
  const ref = await refundPayment(payId, rupees * 100, receipt).catch(async (e) => {
    await alert(o, `a refund of ${rs(rupees)} didn't go through: ${(e as Error).message}\n\nrefund it from the Razorpay dashboard, or top up the balance and try again.`);
    throw new ShopError("the refund didn't go through just now, so nothing's changed. try again in a few minutes, or write to us and we'll do it by hand", 409);
  });
  const r: Refund = { id: ref.id, amount: ref.amount / 100, status: ref.status, at: now(), ...(ref.status === "processed" ? { doneAt: now() } : {}), ...(reason ? { reason } : {}) };
  (o.refunds ??= []).push(r);
  if (r.status === "processed") note(o, "refunded", rs(r.amount));
  if (r.status === "pending") await kv("ZADD", OPEN, Date.now(), o.id);
  return r;
}

async function cancelNow(o: Order, who: "you" | "sahn", refund: boolean) {
  if (o.stage === "cancelled") return o;
  if (o.stage !== "paying" && !changeable(o)) {
    throw new ShopError(who === "you" ? "it's gone to print, so it can't be cancelled here any more: write to us" : "it's with the print partner, who can't cancel it: refund it instead", 409);
  }
  const left = o.total - refunded(o);
  if (refund && o.paidAt && left > 0) await refundNow(o, left, `${o.id}-cancel`, "cancelled");
  o.stage = "cancelled";
  delete o.problem;
  note(o, "cancelled", who === "you" ? "by you" : "by sahn");
  await save(o);
  if (!pendingRefund(o)) await kv("ZREM", OPEN, o.id);
  await emailOnce(o, "cancelled").catch(quietly("cancel"));
  return o;
}

/** The buyer cancels in the change-of-mind hour: refunded in full, back the way they paid. */
export const cancel = (id: string) => changing(id, (o) => cancelNow(o, "you", true));

/** The buyer fixes where it goes, while it hasn't gone to print. The email stays: it's whose order this is. */
export const changeAddress = (id: string, d: Omit<ShipTo, "email">) =>
  changing(id, async (o) => {
    if (!changeable(o)) throw new ShopError("it's gone to print, so the address can't be changed here any more: write to us", 409);
    o.ship = { ...d, email: o.contact.email };
    o.contact = { ...o.contact, name: d.name, phone: d.phone };
    note(o, "address", `${d.city}, ${d.state} ${d.pin}`);
    await save(o);
    await rememberAddress(o.contact.email, { ...o.ship }).catch(() => {});
    await emailOnce(o, `address:${o.events?.filter((e) => e.kind === "address").length ?? 1}`).catch(quietly("address"));
    return o;
  });

/* ---------- the admin's actions: each under the order's lock, each written into its events ---------- */

const by = (who: string) => (who ? ` (${who.slice(0, 80)})` : "");

/** an email sent again, as the order is now (the buyer gets it even if they had it already) */
export const resendEmail = (id: string, kind: MailKind, who = "") =>
  changing(id, async (o) => {
    if (!emailFor(o, kind)) throw new ShopError(`there's no ${kind} email for this order yet`, 409);
    await kv("DEL", `mail:${o.id}:${kind}`);
    if (!(await emailOnce(o, kind, `-resend-${Date.now()}`))) throw new ShopError("it was just sent, try again in a moment", 409);
    note(o, "admin", `sent the ${kind} email again${by(who)}`);
    await save(o);
    return o;
  });

/** to print now: skips what's left of the hour, or tries again after the partner refused it */
export const retryPrint = (id: string, who = "") =>
  changing(id, async (o) => {
    if (o.partnerId) throw new ShopError("it's with the print partner already", 409);
    if (!o.paidAt || (o.stage !== "paid" && o.stage !== "attention")) throw new ShopError("only a paid order waiting to print can go to print", 409);
    note(o, "admin", `sent to print by hand${by(who)}`);
    const ok = await toPrint(o);
    await save(o);
    if (!ok) throw new ShopError(o.problem ?? "the print partner didn't take it", 502);
    return o;
  });

/** sahn cancels: before print only (the partner has no cancel), with a full refund unless refund is false */
export const adminCancel = (id: string, opts: { refund: boolean }, who = "") =>
  changing(id, async (o) => {
    note(o, "admin", `cancelled${opts.refund ? " with a full refund" : " without a refund"}${by(who)}`);
    return cancelNow(o, "sahn", opts.refund);
  });

/** a refund of any part of a paid order, at any stage, up to what's left of what was paid */
export const adminRefund = (id: string, rupees: number, reason: string, who = "") =>
  changing(id, async (o) => {
    if (!o.paidAt) throw new ShopError("it isn't paid", 409);
    const left = o.total - refunded(o);
    if (!Number.isInteger(rupees) || rupees < 1 || rupees > left) throw new ShopError(`whole rupees, 1 to ${rs(left)}`, 400);
    const clean = reason.replace(/[\u0000-\u001f<>]/g, " ").trim().slice(0, 140);
    const r = await refundNow(o, rupees, `${o.id}-r${(o.refunds?.length ?? 0) + 1}`, clean || undefined);
    note(o, "admin", `refunded ${rs(rupees)}${clean ? `: ${clean}` : ""}${by(who)}`);
    await save(o);
    await emailOnce(o, `refund:${r.id}`).catch(quietly("refund"));
    return o;
  });

/** Onkar's own note on an order (never shown to the buyer) */
export const addNote = (id: string, text: string, who = "") =>
  changing(id, async (o) => {
    const t = text.replace(/[\u0000-\u0008\u000b-\u001f]/g, " ").trim().slice(0, 1000);
    if (!t) throw new ShopError("an empty note", 400);
    note(o, "note", `${t}${by(who)}`);
    await save(o);
    return o;
  });

/** the emails this order has had: kind → when (the first send; a resend moves it) */
export async function emailsSent(id: string): Promise<Record<string, string>> {
  if (!validId(id)) return {};
  const rows = await query("SELECT substring(key from $2::int), (expires_at - interval '400 days')::text FROM kv WHERE key LIKE $1 AND (expires_at IS NULL OR expires_at > now())", [`mail:${id}:%`, `mail:${id}:`.length + 1]);
  return Object.fromEntries(rows.map(([k, at]) => [k ?? "", at ?? ""]));
}

/** every order, newest first, for the admin: by stage, by email, or a search over number, name, email, phone, city, pin */
export async function listOrders(opts: { limit?: number; offset?: number; stage?: Stage; email?: string; q?: string } = {}): Promise<Order[]> {
  const limit = Math.min(Math.max(1, opts.limit ?? 50), 200), offset = Math.max(0, opts.offset ?? 0);
  const q = opts.q?.trim() ? `%${opts.q.trim().slice(0, 80).replace(/[\\%_]/g, (c) => `\\${c}`)}%` : null;
  const rows = await query(
    `SELECT value FROM kv
     WHERE key LIKE 'order:%' AND (expires_at IS NULL OR expires_at > now())
       AND ($1::text IS NULL OR value::jsonb->>'stage' = $1)
       AND ($2::text IS NULL OR value::jsonb->'contact'->>'email' = $2)
       AND ($3::text IS NULL OR value::jsonb->>'id' ILIKE $3 OR value::jsonb->'contact'->>'name' ILIKE $3 OR value::jsonb->'contact'->>'email' ILIKE $3
            OR value::jsonb->'contact'->>'phone' ILIKE $3 OR value::jsonb->'ship'->>'city' ILIKE $3 OR value::jsonb->'ship'->>'pin' ILIKE $3)
     ORDER BY value::jsonb->>'createdAt' DESC OFFSET $4::int LIMIT $5::int`,
    [opts.stage ?? null, opts.email?.toLowerCase() ?? null, q, offset, limit],
  );
  return rows.map((r) => JSON.parse(r[0] ?? "null") as Order).filter(Boolean);
}

/**
 * An order wiped from the store, for test orders only: one that was never paid, or one cancelled with its refund
 * done. A paid order that's still going has to be cancelled (and refunded) first, so no real sale disappears.
 */
export async function deleteOrder(id: string) {
  const o = await loadOrder(id);
  if (!o) throw new ShopError("no such order", 404);
  const done = o.stage === "paying" || (o.stage === "cancelled" && !pendingRefund(o));
  if (!done) throw new ShopError(o.stage === "cancelled" ? "its refund is still pending: wait for it to finish" : "a paid order that's still going: cancel it first (that refunds it)", 409);
  await kv("DEL", key(id));
  await kv("ZREM", OPEN, id);
  await kv("ZREM", `uorders:${o.contact.email}`, id);
  await kv("DEL", `rzp:${o.rzpOrderId}`);
  return o;
}

/** how many orders are at each stage */
export async function countOrders(): Promise<Partial<Record<Stage, number>>> {
  const rows = await query("SELECT value::jsonb->>'stage', count(*)::text FROM kv WHERE key LIKE 'order:%' AND (expires_at IS NULL OR expires_at > now()) GROUP BY 1");
  return Object.fromEntries(rows.map(([s, n]) => [s ?? "?", Number(n)]));
}

/** pending refunds, asked again */
export async function syncRefund(id: string) {
  return withLock(id, async () => {
    const o = await loadOrder(id);
    if (!o || !pendingRefund(o)) return o;
    let changed = false;
    for (const r of o.refunds ?? []) {
      if (r.status !== "pending") continue;
      const ref = await fetchRefund(r.id);
      if (ref.status === r.status) continue;
      changed = true;
      r.status = ref.status;
      if (ref.status === "processed") {
        r.doneAt = now();
        note(o, "refunded", rs(r.amount));
      } else if (ref.status === "failed") await alert(o, `the refund ${ref.id} (${rs(r.amount)}) failed: refund it by hand from the Razorpay dashboard`);
    }
    if (changed) await save(o);
    return o;
  });
}

/** where the partner says it is now; emails the buyer when it leaves and when it arrives */
export async function sync(id: string): Promise<Order | null> {
  const r = await withLock(id, async () => {
    const o = await loadOrder(id);
    if (!o?.partnerId || !["printing", "shipped", "out", "attention"].includes(o.stage)) return o;
    const s = await partnerStatus(o.partnerId);
    o.syncedAt = now();
    if (s.status && s.status !== o.partnerRaw) note(o, "partner", s.status, o.syncedAt);
    o.partnerRaw = s.status;
    const t = (s.status ?? "").toLowerCase();
    if (s.awb || s.trackingUrl) o.tracking = { awb: s.awb, courier: s.courier, url: s.trackingUrl };
    let next: Stage = o.stage === "attention" ? "printing" : o.stage;
    if (/rto|return|cancel|lost|undeliver/.test(t)) next = "attention";
    else if (/deliver(ed)?$|^delivered|completed/.test(t)) next = "delivered";
    else if (/out.?for.?delivery/.test(t)) next = "out";
    else if (/transit|ship|dispatch|picked|manifest/.test(t) || o.tracking?.awb) next = o.stage === "out" ? "out" : "shipped";
    if (next === "attention" && o.stage !== "attention") {
      o.problem = `the partner says: ${s.status}`;
      note(o, "trouble", "held up on the way; we're on it", o.syncedAt);
      await alert(o, o.problem);
    }
    if ((next === "shipped" || next === "out" || next === "delivered") && !o.shippedAt) {
      o.shippedAt = o.syncedAt;
      note(o, "shipped", [o.tracking?.courier?.toLowerCase(), o.tracking?.awb].filter(Boolean).join(" · ") || undefined, o.syncedAt);
    }
    if (next === "out" && !o.events?.some((e) => e.kind === "out")) note(o, "out", undefined, o.syncedAt);
    if (next === "delivered" && !o.deliveredAt) {
      o.deliveredAt = o.syncedAt;
      note(o, "delivered", undefined, o.syncedAt);
    }
    o.stage = next;
    await save(o);
    await emailOnce(o, "shipped").catch(quietly("shipped"));
    if (o.stage === "out") await emailOnce(o, "out").catch(quietly("out"));
    if (o.stage === "delivered") {
      await emailOnce(o, "delivered").catch(quietly("delivered"));
      if (!pendingRefund(o)) await kv("ZREM", OPEN, o.id);
    }
    return o;
  });
  return r ?? (await loadOrder(id));
}

/** the sync job: every open order a step further; unpaid ones dropped after two days */
export async function syncAll() {
  const ids = await kv<string[]>("ZRANGE", OPEN, 0, 199);
  const out: Record<string, string> = {};
  for (const id of ids) {
    try {
      let o = await loadOrder(id);
      if (!o) {
        await kv("ZREM", OPEN, id);
        continue;
      }
      if (pendingRefund(o)) o = await syncRefund(id);
      if (o && (o.stage === "cancelled" || o.stage === "delivered")) {
        if (!pendingRefund(o)) await kv("ZREM", OPEN, id);
        out[id] = o.stage;
        continue;
      }
      if (o && (o.stage === "paying" || o.stage === "paid" || (o.stage === "attention" && !o.partnerId))) o = await advance(id);
      if (o && o.stage === "paying" && Date.now() - Date.parse(o.createdAt) > 2 * 86400_000) {
        await kv("ZREM", OPEN, id);
        out[id] = "dropped unpaid";
        continue;
      }
      if (o?.partnerId) o = await sync(id);
      out[id] = o?.stage ?? "gone";
    } catch (e) {
      out[id] = `error: ${(e as Error).message.slice(0, 100)}`;
    }
  }
  return out;
}

/** the steps of an order made before the timeline was kept, rebuilt from what it has; never sahn's own notes */
function timeline(o: Order): OrderEvent[] {
  if (o.events?.length) return o.events.filter((e) => !PRIVATE.includes(e.kind));
  const e: OrderEvent[] = [{ at: o.createdAt, kind: "placed" }];
  if (o.paidAt) e.push({ at: o.paidAt, kind: "paid" });
  if (o.partnerId) e.push({ at: o.paidAt ?? o.createdAt, kind: "printing" });
  if (o.shippedAt) e.push({ at: o.shippedAt, kind: "shipped" });
  if (o.deliveredAt) e.push({ at: o.deliveredAt, kind: "delivered" });
  return e;
}

/**
 * What the buyer's page shows. The full address only while it can still be changed (so they can check it) or to the
 * signed-in buyer; otherwise only the city, since an order link can be forwarded.
 */
export type OrderView = {
  id: string;
  placed: string;
  stage: Stage;
  lines: { design: Design; name: string; size: Size; quantity: number; unitPrice: number }[];
  total: number;
  tracking: Order["tracking"] | null;
  shippedAt: string | null;
  deliveredAt: string | null;
  city: string;
  events: OrderEvent[];
  payment: { id: string; label: string; at: string } | null;
  refunds: Refund[];
  /** rupees refunded or on the way back */
  refunded: number;
  /** until when the buyer can cancel or change the address (it goes to print at the first check after this) */
  changeUntil: string | null;
  ship: Omit<ShipTo, "email"> | null;
};
export const view = (o: Order, full = false): OrderView => {
  const open = changeable(o);
  return {
    id: o.id,
    placed: o.createdAt,
    stage: o.stage,
    lines: o.lines.map((l) => ({ design: l.design, name: shirt(l.design), size: l.size, quantity: l.quantity, unitPrice: l.unitPrice })),
    total: o.total,
    tracking: o.tracking ?? null,
    shippedAt: o.shippedAt ?? null,
    deliveredAt: o.deliveredAt ?? null,
    city: o.ship.city,
    events: timeline(o),
    payment: o.payment ? { id: o.payment.id, label: o.payment.label, at: o.payment.at } : o.paidAt ? { id: "", label: "", at: o.paidAt } : null,
    refunds: o.refunds ?? [],
    refunded: refunded(o),
    changeUntil: open && o.paidAt ? new Date(Date.parse(o.paidAt) + HOLD_MS).toISOString() : null,
    ship: open || full ? { name: o.ship.name, address1: o.ship.address1, address2: o.ship.address2, city: o.ship.city, state: o.ship.state, pin: o.ship.pin, phone: o.ship.phone } : null,
  };
};

/**
 * Who may see an order: whoever has its link (the key in every order email), or the signed-in buyer whose email
 * placed it. `full` (the whole address on the page) only for the signed-in buyer.
 */
export async function orderFor(id: string, k: string | null, email: string | null): Promise<{ o: Order; full: boolean } | null> {
  if (!validId(id)) return null;
  const byKey = !!k && k.length <= 64 && keyMatches(id, k);
  if (!byKey && !email) return null;
  const o = await loadOrder(id);
  if (!o) return null;
  const mine = !!email && o.contact.email === email;
  return byKey || mine ? { o, full: mine } : null;
}
