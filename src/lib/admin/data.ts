import "server-only";
import { DESIGNS, SIZE_ORDER, type Design, type Size } from "@/content/tee";
import { listAccounts, type Account } from "@/lib/shop/account";
import { listOrders, refunded, type Order } from "@/lib/shop/orders";
import { products } from "@/lib/shop/products";
import { rows } from "./db";
import { getSettings, type Settings } from "./settings";

/**
 * The shop's records as the admin reads them: orders and accounts through the shop's listOrders and listAccounts
 * (read only: every change goes through the shop's own functions). A one-person shop has hundreds of orders, not millions, so they're
 * read whole and worked out here.
 */
export async function allOrders(): Promise<Order[]> {
  // through the shop's listOrders (newest first, 200 a page), so the admin never depends on how orders are stored
  const out: Order[] = [];
  for (let offset = 0; offset < 20000; offset += 200) {
    const page = await listOrders({ limit: 200, offset });
    out.push(...page);
    if (page.length < 200) break;
  }
  return out;
}

export async function allAccounts(): Promise<Account[]> {
  // through the shop's listAccounts (newest first, 200 a page)
  const out: Account[] = [];
  for (let offset = 0; offset < 20000; offset += 200) {
    const page = await listAccounts({ limit: 200, offset });
    out.push(...page);
    if (page.length < 200) break;
  }
  return out;
}

export type Fee = { payment_id: string; order_id: string; fee: number | null; tax: number | null; method: string | null; detail: string | null; settlement_id: string | null; settled_at: string | null; fetched_at: string };
export const knownFees = async () => new Map((await rows<Fee>("SELECT * FROM admin_payments")).map((f) => [f.order_id, f]));

/** paid at all (not just started) */
export const isPaid = (o: Order) => o.stage !== "paying" && !!o.paidAt;
const shirts = (o: Order) => o.lines.reduce((t, l) => t + l.quantity, 0);
/** what the partner charges for one of each shirt, from the products (the code's cost until one is saved) */
export type Costs = Record<string, number>;
export const costs = async (): Promise<Costs> => Object.fromEntries((await products()).map((p) => [p.id, p.cost]));
/** money the partner was (or will be) paid: nothing for an order cancelled before it went to print */
const partnerCost = (o: Order, c: Costs) => (o.stage === "cancelled" && !o.partnerId ? 0 : o.lines.reduce((t, l) => t + (c[l.design] ?? 0) * l.quantity, 0));

/** what one order left, after the partner, the payment fee and delivery: actual fee where Razorpay told us, else the rate */
export function marginOf(o: Order, s: Settings, c: Costs, fee?: Fee) {
  if (!isPaid(o)) return null;
  const feeAmt = fee?.fee != null ? Number(fee.fee) : Math.round(o.total * s.feeRate * 100) / 100;
  const ship = o.stage === "cancelled" && !o.partnerId ? 0 : s.shipPerParcel * Math.max(1, Math.ceil(shirts(o) / s.shirtsPerParcel));
  const revenue = o.total - refunded(o);
  const cost = Math.round(partnerCost(o, c) * 100) / 100;
  return { revenue, cost, fee: feeAmt, feeActual: fee?.fee != null, ship, margin: Math.round((revenue - cost - feeAmt - ship) * 100) / 100 };
}

const IST = 5.5 * 3600_000;
/** midnight today and this Monday, in India's time, as epoch ms */
export function periodStarts(now = Date.now()) {
  const d = new Date(now + IST);
  const today = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) - IST;
  const dow = (d.getUTCDay() + 6) % 7;
  return { today, week: today - dow * 86400_000 };
}
export const istDay = (iso: string) => new Date(Date.parse(iso) + IST).toISOString().slice(0, 10);

/** orders: paid and not cancelled; cancelled and refunds are counted apart, and revenue is what's left after refunds */
export type Totals = { orders: number; cancelled: number; refunds: number; refunded: number; shirts: number; revenue: number; cost: number; fees: number; ship: number; margin: number; estimated: boolean };
const zero = (): Totals => ({ orders: 0, cancelled: 0, refunds: 0, refunded: 0, shirts: 0, revenue: 0, cost: 0, fees: 0, ship: 0, margin: 0, estimated: false });

export async function overview() {
  const [orders, s, fees, c] = await Promise.all([allOrders(), getSettings(), knownFees(), costs()]);
  const { today, week } = periodStarts();
  const t = { today: zero(), yesterday: zero(), week: zero(), all: zero() };
  const bySize: Record<string, Record<Size, number>> = {};
  for (const d of Object.keys(DESIGNS)) bySize[d] = Object.fromEntries(SIZE_ORDER.map((z) => [z, 0])) as Record<Size, number>;
  const byDay = new Map<string, { orders: number; revenue: number }>();
  for (const o of orders) {
    const m = marginOf(o, s, c, fees.get(o.id));
    if (!m) continue;
    const at = Date.parse(o.paidAt!);
    for (const [k, from, to] of [["all", 0, Infinity], ["week", week, Infinity], ["today", today, Infinity], ["yesterday", today - 86400_000, today]] as const) {
      if (at < from || at >= to) continue;
      const x = t[k];
      if (o.stage === "cancelled") x.cancelled++;
      else {
        x.orders++;
        x.shirts += shirts(o);
      }
      const back = refunded(o);
      if (back > 0) {
        x.refunds++;
        x.refunded += back;
      }
      x.revenue += m.revenue;
      x.cost += m.cost;
      x.fees += m.fee;
      x.ship += m.ship;
      x.margin += m.margin;
      if (!m.feeActual) x.estimated = true;
    }
    if (o.stage !== "cancelled") for (const l of o.lines) if (bySize[l.design]) bySize[l.design][l.size] += l.quantity;
    const day = istDay(o.paidAt!);
    const b = byDay.get(day) ?? { orders: 0, revenue: 0 };
    if (o.stage !== "cancelled") b.orders++;
    b.revenue += m.revenue;
    byDay.set(day, b);
  }
  for (const x of Object.values(t)) for (const k of ["revenue", "refunded", "cost", "fees", "ship", "margin"] as const) x[k] = Math.round(x[k] * 100) / 100;
  return { orders, totals: t, bySize, byDay, settings: s, needs: needsYou(orders, s) };
}

export type Need = { level: "now" | "soon"; title: string; detail: string; href: string };

/** what needs Onkar, worst first */
export function needsYou(orders: Order[], s: Settings): Need[] {
  const out: Need[] = [];
  const hours = (iso?: string) => (iso ? (Date.now() - Date.parse(iso)) / 3600_000 : 0);
  for (const o of orders) {
    const href = `/admin/orders/${o.id}`;
    if (o.stage === "attention") {
      const wallet = /balance|wallet|insufficient|recharge|fund/i.test(o.problem ?? "");
      out.push({ level: "now", title: wallet ? `#${o.id}: the Qikink wallet looks low` : `#${o.id} is held up`, detail: o.problem ?? "no reason kept", href });
    }
    for (const r of o.refunds ?? []) {
      if (r.status === "failed") out.push({ level: "now", title: `#${o.id}: a refund failed`, detail: `refund ${r.id} for ₹${r.amount}: do it by hand from Razorpay`, href });
      if (r.status === "pending" && hours(r.at) > 24 * 8) out.push({ level: "soon", title: `#${o.id}: a refund is still pending`, detail: `since ${r.at.slice(0, 10)}`, href });
    }
    if (o.stage === "paid" && hours(o.paidAt) > 6) out.push({ level: "now", title: `#${o.id} is paid but not sent to print`, detail: `paid ${Math.round(hours(o.paidAt))} h ago; the sync job may not be running`, href });
    if (o.stage === "printing" && hours(o.events?.find((e) => e.kind === "printing")?.at ?? o.paidAt) > 24 * 7)
      out.push({ level: "soon", title: `#${o.id} has been printing a week`, detail: `last word from Qikink: ${o.partnerRaw ?? "none"}`, href });
    if (o.stage === "shipped" && hours(o.shippedAt) > 24 * 10) out.push({ level: "soon", title: `#${o.id} shipped 10+ days ago`, detail: `${o.tracking?.courier ?? ""} ${o.tracking?.awb ?? ""}`.trim() || "no tracking", href });
  }
  void s;
  return out.sort((a, b) => (a.level === b.level ? 0 : a.level === "now" ? -1 : 1));
}

export type Customer = { email: string; name: string; phone: string; account: Account | null; orders: Order[]; paid: number; spend: number; first: string; last: string };

/** everyone who has ordered or signed up, by email */
export async function customers(): Promise<Customer[]> {
  const [orders, accounts] = await Promise.all([allOrders(), allAccounts()]);
  const m = new Map<string, Customer>();
  const get = (email: string) => {
    let c = m.get(email);
    if (!c) m.set(email, (c = { email, name: "", phone: "", account: null, orders: [], paid: 0, spend: 0, first: "", last: "" }));
    return c;
  };
  for (const a of accounts) {
    const c = get(a.email);
    c.account = a;
    c.name ||= a.name;
    c.phone ||= a.phone;
    c.first = a.createdAt;
  }
  for (const o of orders) {
    const c = get(o.contact.email);
    c.orders.push(o);
    c.name ||= o.contact.name;
    c.phone ||= o.contact.phone;
    if (isPaid(o)) {
      c.paid++;
      c.spend += o.total - refunded(o);
    }
    if (!c.first || o.createdAt < c.first) c.first = o.createdAt;
    if (!c.last || o.createdAt > c.last) c.last = o.createdAt;
  }
  return [...m.values()].sort((a, b) => b.spend - a.spend || (b.last || b.first).localeCompare(a.last || a.first));
}

export const shirtName = (d: Design | string) => {
  const x = DESIGNS[d as Design];
  return x ? `${x.no} ${x.name}${x.city ? ` ${x.city}` : ""}` : String(d);
};
