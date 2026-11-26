import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { OPERATOR } from "@/content/policies";
import { SHOP, priceOf } from "@/content/shop";
import { DESIGNS, type Design, type Size } from "@/content/tee";
import { ownerEmail, shopSecret } from "./config";
import { sendEmail } from "./email";
import { ShopError } from "./errors";
import { getJson, kv, once, setJson, withLock } from "./kv";
import { partnerStatus, sendToPrint, type ShipTo } from "./partner";
import { createPayment, fetchPayment } from "./razorpay";

/**
 * An order, from the moment the buyer goes to pay to the shirt in their hands:
 *   paying → paid (Razorpay confirms) → printing (the partner has it) → shipped → out → delivered
 * Every step is taken at most once (a lock per order, and each email sent once), so the checkout's answer, the
 * webhook, the order page and the sync job can all push an order on without ever doubling anything.
 */
export type Stage = "paying" | "paid" | "printing" | "shipped" | "out" | "delivered" | "attention";

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
};

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
  const o: Order = { id, createdAt: new Date().toISOString(), stage: "paying", lines, total, contact, ship, rzpOrderId: rzp.id };
  await save(o);
  await kv("SET", `rzp:${rzp.id}`, id, "EX", 400 * 86400);
  await kv("ZADD", OPEN, Date.now(), id);
  return o;
}

export const orderForPayment = (rzpOrderId: string) => kv<string | null>("GET", `rzp:${rzpOrderId}`);

const site = () => process.env.SHOP_SITE_URL?.replace(/\/$/, "") ?? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL ?? "still-breathing-studio.vercel.app"}`;
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
 * confirmation, hand it to the partner. Safe to call any number of times from anywhere.
 */
export async function advance(id: string): Promise<Order | null> {
  const r = await withLock(id, async () => {
    const o = await loadOrder(id);
    if (!o) return null;
    if (o.stage === "paying") {
      const p = await fetchPayment(o.rzpOrderId);
      if (p.status !== "paid" || p.amount_paid !== o.total * 100) return o;
      o.stage = "paid";
      o.paidAt = new Date().toISOString();
      await save(o);
    }
    if (o.stage === "paid" || (o.stage === "attention" && !o.partnerId)) {
      await emailOnce(o, "confirmed", `sahn: order #${o.id} is in`, [
        `hi ${o.contact.name.split(" ")[0]},`,
        `thank you. your order #${o.id} is paid and in. each shirt is made for you from here: ${SHOP.make[0]}–${SHOP.make[1]} days to make, then ${SHOP.road[0]}–${SHOP.road[1]} days on the road. we'll email you the tracking the moment it leaves.`,
        `${itemsText(o)}\npaid ${rs(o.total)}, GST and shipping included`,
        `going to: ${o.ship.name}, ${o.ship.address1}${o.ship.address2 ? `, ${o.ship.address2}` : ""}, ${o.ship.city}, ${o.ship.state} ${o.ship.pin}`,
        `your order, any time: ${site()}${orderPath(o.id)}`,
        sign(),
      ].join("\n\n")).catch((e) => console.error("confirm email:", e));
      try {
        o.partnerId = await sendToPrint(o.id, o.lines, o.ship, o.total, site());
        o.stage = "printing";
        delete o.problem;
      } catch (e) {
        o.stage = "attention";
        o.problem = `the print partner didn't take it: ${(e as Error).message}`;
        await alert(o, `${o.problem}\n\nit's tried again every few hours. if the balance is low, top it up and it goes through on the next try.`);
      }
      await save(o);
    }
    return o;
  });
  return r ?? (await loadOrder(id));
}

/** where the partner says it is now; emails the buyer when it leaves and when it arrives */
export async function sync(id: string): Promise<Order | null> {
  const r = await withLock(id, async () => {
    const o = await loadOrder(id);
    if (!o?.partnerId || !["printing", "shipped", "out", "attention"].includes(o.stage)) return o;
    const s = await partnerStatus(o.partnerId);
    o.syncedAt = new Date().toISOString();
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
      await alert(o, o.problem);
    }
    if ((next === "shipped" || next === "out" || next === "delivered") && !o.shippedAt) o.shippedAt = o.syncedAt;
    if (next === "delivered" && !o.deliveredAt) o.deliveredAt = o.syncedAt;
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

/** the order's page: never the address, phone or email, only what it is and where it is */
export type OrderView = {
  id: string;
  placed: string;
  stage: Stage;
  lines: { name: string; size: Size; quantity: number }[];
  total: number;
  tracking: Order["tracking"] | null;
  shippedAt: string | null;
  deliveredAt: string | null;
  city: string;
};
export const view = (o: Order): OrderView => ({
  id: o.id,
  placed: o.createdAt,
  stage: o.stage,
  lines: o.lines.map((l) => ({ name: shirt(l.design), size: l.size, quantity: l.quantity })),
  total: o.total,
  tracking: o.tracking ?? null,
  shippedAt: o.shippedAt ?? null,
  deliveredAt: o.deliveredAt ?? null,
  city: o.ship.city,
});
