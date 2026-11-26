import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { OPERATOR } from "@/content/policies";
import { SHOP, priceOf } from "@/content/shop";
import { DESIGNS, type Design, type Size } from "@/content/tee";
import { linkOrder, rememberAddress } from "./account";
import { ownerEmail, shopSecret } from "./config";
import { sendEmail } from "./email";
import { ShopError } from "./errors";
import { getJson, kv, once, setJson, withLock } from "./kv";
import { partnerStatus, sendToPrint, type ShipTo } from "./partner";
import { createPayment, fetchPayment, fetchPayments, fetchRefund, refundPayment, type RzpPayment } from "./razorpay";
import { SITE_URL } from "@/lib/site";

/**
 * An order, from the moment the buyer goes to pay to the shirt in their hands:
 *   paying → paid (Razorpay confirms) → printing (the partner has it) → shipped → out → delivered
 *                         ↘ cancelled (the buyer, in the first hour, before it goes to print: refunded in full)
 * A paid order waits an hour before it goes to print, so the buyer can still cancel it or fix the address themselves.
 * Every step is taken at most once (a lock per order, and each email sent once), so the checkout's answer, the
 * webhook, the order page and the sync job can all push an order on without ever doubling anything.
 */
export type Stage = "paying" | "paid" | "printing" | "shipped" | "out" | "delivered" | "attention" | "cancelled";

/** the change-of-mind hour: after paying, the order waits this long before going to print */
export const HOLD_MS = 3600_000;

/** one thing that happened to an order, when it happened (or when we first saw it) */
export type EventKind = "placed" | "paid" | "address" | "printing" | "partner" | "shipped" | "out" | "delivered" | "trouble" | "cancelled" | "refunded";
export type OrderEvent = { at: string; kind: EventKind; note?: string };

export type Line = { design: Design; size: Size; quantity: number; unitPrice: number };

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
  refund?: { id: string; amount: number; status: "pending" | "processed" | "failed"; at: string; doneAt?: string };
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

/** when it can still be cancelled or its address fixed by the buyer: paid, not yet with the partner */
export const changeable = (o: Order) => !o.partnerId && (o.stage === "paid" || o.stage === "attention") && !!o.paidAt;
const released = (o: Order) => !!o.paidAt && Date.now() - Date.parse(o.paidAt) >= HOLD_MS;

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

/** The buyer is about to pay: price the bag here, from shop.ts, and fix that amount on a Razorpay order. */
export async function startOrder(bag: { design: Design; size: Size; quantity: number }[], contact: Order["contact"], ship: ShipTo) {
  const lines: Line[] = bag.map((l) => ({ ...l, unitPrice: priceOf(l.design) }));
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

/** one email per order and kind, ever */
async function emailOnce(o: Order, kind: string, subject: string, text: string) {
  if (!(await once(`mail:${o.id}:${kind}`, 400 * 86400))) return;
  try {
    await sendEmail(o.contact.email, subject, text, `${o.id}-${kind}`, OPERATOR.email);
  } catch (e) {
    await kv("DEL", `mail:${o.id}:${kind}`); // let the next run try again
    throw e;
  }
}

/** something only Onkar can sort out: tell him, at most once a day per order and problem */
async function alert(o: Order, problem: string) {
  const to = ownerEmail();
  if (!to || !(await once(`alert:${o.id}:${problem.slice(0, 40)}`, 86400))) return;
  await sendEmail(to, `sahn: order #${o.id} needs you`, `order #${o.id} (${rs(o.total)}, paid ${o.paidAt ?? "?"})\n\n${problem}\n\n${itemsText(o)}\n\nship to: ${o.ship.name}, ${o.ship.city}, ${o.ship.state} ${o.ship.pin}`, `alert-${o.id}-${Date.now() >> 26}`).catch((e) => console.error("alert:", e));
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
      const until = new Date(Date.parse(o.paidAt) + HOLD_MS).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" });
      await emailOnce(o, "confirmed", `sahn: order #${o.id} is in`, [
        `hi ${o.contact.name.split(" ")[0]},`,
        `thank you. your order #${o.id} is paid and in. each shirt is made for you from here: ${SHOP.make[0]}–${SHOP.make[1]} days to make, then ${SHOP.road[0]}–${SHOP.road[1]} days on the road. we'll email you the tracking the moment it leaves.`,
        `${itemsText(o)}\npaid ${rs(o.total)}${o.payment ? ` by ${o.payment.label}` : ""}, shipping included`,
        `going to: ${o.ship.name}, ${o.ship.address1}${o.ship.address2 ? `, ${o.ship.address2}` : ""}, ${o.ship.city}, ${o.ship.state} ${o.ship.pin}`,
        `changed your mind, or the address is wrong? until ${until} you can cancel (refunded in full) or fix the address yourself on your order's page. after that it goes to print.`,
        `your order, any time: ${site()}${orderPath(o.id)}`,
        sign(),
      ].join("\n\n")).catch((e) => console.error("confirm email:", e));
    }
    if ((o.stage === "paid" || (o.stage === "attention" && !o.partnerId)) && released(o)) {
      try {
        o.partnerId = await sendToPrint(o.id, o.lines, o.ship, o.total, site());
        o.stage = "printing";
        delete o.problem;
        note(o, "printing");
      } catch (e) {
        const first = o.stage !== "attention";
        o.stage = "attention";
        o.problem = `the print partner didn't take it: ${(e as Error).message}`;
        if (first) note(o, "trouble", "held up before printing; we're on it");
        await alert(o, `${o.problem}\n\nit's tried again every few hours. if the balance is low, top it up and it goes through on the next try.`);
      }
      await save(o);
    }
    return o;
  });
  return r ?? (await loadOrder(id));
}

/** The buyer cancels in the change-of-mind hour: refunded in full, back the way they paid. */
export async function cancel(id: string): Promise<Order> {
  const r = await withLock(id, async () => {
    const o = await loadOrder(id);
    if (!o) throw new ShopError("no such order", 404);
    if (o.stage === "cancelled") return o;
    if (!changeable(o)) throw new ShopError("it's gone to print, so it can't be cancelled here any more: write to us", 409);
    const payId = o.payment?.id ?? (await fetchPayments(o.rzpOrderId)).items.find((x) => x.status === "captured")?.id;
    if (!payId) throw new ShopError("couldn't find the payment to refund, try again in a minute");
    const ref = await refundPayment(payId, o.total * 100, `${o.id}-cancel`).catch(async (e) => {
      // most often the Razorpay balance is too low to refund from: tell Onkar, and the buyer to try again or write
      await alert(o, `the buyer asked to cancel and the refund didn't go through: ${(e as Error).message}\n\nrefund it from the Razorpay dashboard, or top up the balance and they can try again.`);
      throw new ShopError("the refund didn't go through just now, so nothing's changed. try again in a few minutes, or write to us and we'll do it by hand", 409);
    });
    o.stage = "cancelled";
    delete o.problem;
    o.refund = { id: ref.id, amount: ref.amount / 100, status: ref.status, at: now(), ...(ref.status === "processed" ? { doneAt: now() } : {}) };
    note(o, "cancelled", "by you");
    if (ref.status === "processed") note(o, "refunded", rs(o.refund.amount));
    await save(o);
    await emailOnce(o, "cancelled", `sahn: order #${o.id} is cancelled`, [
      `your order #${o.id} is cancelled, and nothing will be made or sent.`,
      `${rs(o.refund.amount)} is on its way back${o.payment ? ` to your ${o.payment.label.split(" · ")[0]}` : ""}. banks usually show it within 5–7 working days, often sooner for UPI.`,
      `refund reference: ${ref.id}. your order: ${site()}${orderPath(o.id)}`,
      sign(),
    ].join("\n\n")).catch((e) => console.error("cancel email:", e));
    return o;
  });
  if (!r) throw new ShopError("one moment, it's being updated: try again", 409);
  return r;
}

/** The buyer fixes where it goes, while it hasn't gone to print. The email stays: it's whose order this is. */
export async function changeAddress(id: string, d: Omit<ShipTo, "email">): Promise<Order> {
  const r = await withLock(id, async () => {
    const o = await loadOrder(id);
    if (!o) throw new ShopError("no such order", 404);
    if (!changeable(o)) throw new ShopError("it's gone to print, so the address can't be changed here any more: write to us", 409);
    o.ship = { ...d, email: o.contact.email };
    o.contact = { ...o.contact, name: d.name, phone: d.phone };
    note(o, "address", `${d.city}, ${d.state} ${d.pin}`);
    await save(o);
    await rememberAddress(o.contact.email, { ...o.ship }).catch(() => {});
    return o;
  });
  if (!r) throw new ShopError("one moment, it's being updated: try again", 409);
  return r;
}

/** a pending refund, asked again */
export async function syncRefund(id: string) {
  return withLock(id, async () => {
    const o = await loadOrder(id);
    if (!o?.refund || o.refund.status !== "pending") return o;
    const ref = await fetchRefund(o.refund.id);
    if (ref.status !== o.refund.status) {
      o.refund.status = ref.status;
      if (ref.status === "processed") {
        o.refund.doneAt = now();
        note(o, "refunded", rs(o.refund.amount));
      } else if (ref.status === "failed") await alert(o, `the refund ${ref.id} failed: refund it by hand from the Razorpay dashboard`);
      await save(o);
    }
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
    const link = `${site()}${orderPath(o.id)}`;
    if (o.shippedAt && o.tracking) {
      await emailOnce(o, "shipped", `sahn: order #${o.id} is on its way`, [
        `it's left. your order #${o.id} is with the courier${o.tracking.courier ? ` (${o.tracking.courier.toLowerCase()})` : ""}.`,
        o.tracking.url ? `track it: ${o.tracking.url}` : `tracking number: ${o.tracking.awb}`,
        `keep your phone on: the courier calls before delivering. your order: ${link}`,
        sign(),
      ].join("\n\n")).catch((e) => console.error("shipped email:", e));
    }
    if (o.stage === "delivered") {
      await emailOnce(o, "delivered", `sahn: order #${o.id} is with you`, [
        `your order #${o.id} has been delivered.`,
        `if anything's wrong with it, write back within 7 days with an unboxing video and photos and we'll put it right.`,
        `wash it cold, inside out, and dry it in the shade.`,
        sign(),
      ].join("\n\n")).catch((e) => console.error("delivered email:", e));
      await kv("ZREM", OPEN, o.id);
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
      if (o.stage === "cancelled") {
        o = await syncRefund(id);
        if (o?.refund?.status !== "pending") await kv("ZREM", OPEN, id);
        out[id] = `cancelled, refund ${o?.refund?.status ?? "?"}`;
        continue;
      }
      if (o.stage === "paying" || o.stage === "paid" || (o.stage === "attention" && !o.partnerId)) o = await advance(id);
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

/** the steps of an order made before the timeline was kept, rebuilt from what it has */
function timeline(o: Order): OrderEvent[] {
  if (o.events?.length) return o.events;
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
  refund: Order["refund"] | null;
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
    refund: o.refund ?? null,
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
