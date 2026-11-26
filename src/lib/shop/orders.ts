import { timingSafeEqual } from "node:crypto";
import { DESIGNS } from "@/content/tee";
import { admin } from "./admin";
import { designOfHandle, sizeOf } from "./catalog";

/**
 * One order, read from Shopify for the order page. An order is shown only to someone holding its key: the secret in
 * Shopify's own order-status link, which every order email carries (the emails link here with it). Without the key,
 * the order number and the email it was placed with get you the key, and nothing else does.
 */
type Raw = {
  name: string;
  createdAt: string;
  email: string | null;
  statusPageUrl: string;
  displayFinancialStatus: string | null;
  displayFulfillmentStatus: string;
  cancelledAt: string | null;
  totalPriceSet: { shopMoney: { amount: string } };
  lineItems: { nodes: { title: string; quantity: number; product: { handle: string } | null; variant: { selectedOptions: { name: string; value: string }[] } | null }[] };
  fulfillments: { displayStatus: string | null; createdAt: string; deliveredAt: string | null; estimatedDeliveryAt: string | null; trackingInfo: { company: string | null; number: string | null; url: string | null }[] }[];
};

const QUERY = `query Order($q: String!) {
  orders(first: 1, query: $q) {
    nodes {
      name createdAt email statusPageUrl displayFinancialStatus displayFulfillmentStatus cancelledAt
      totalPriceSet { shopMoney { amount } }
      lineItems(first: 20) { nodes { title quantity product { handle } variant { selectedOptions { name value } } } }
      fulfillments(first: 5) { displayStatus createdAt deliveredAt estimatedDeliveryAt trackingInfo(first: 3) { company number url } }
    }
  }
}`;

/** an order number as people type it: 1001, #1001 */
export const orderNumber = (v: string) => {
  const m = v.trim().match(/^#?(\d{1,10})$/);
  return m ? m[1] : null;
};

async function find(number: string): Promise<Raw | null> {
  const r = await admin<{ orders: { nodes: Raw[] } }>(QUERY, { q: `name:#${number}` });
  const o = r.orders.nodes[0];
  return o && o.name.replace(/^#/, "") === number ? o : null;
}

/** the secret in Shopify's order-status link (its key=, or the token in its path if a link ever comes without one) */
const keyOf = (statusPageUrl: string) => {
  try {
    const u = new URL(statusPageUrl);
    return u.searchParams.get("key") ?? u.pathname.split("/").filter(Boolean).at(-2) ?? null;
  } catch {
    return null;
  }
};

const same = (a: string, b: string) => {
  const x = Buffer.from(a), y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
};

/** order number + email → the key for its page, or null (the same null for a wrong number and a wrong email) */
export async function keyFor(number: string, email: string) {
  const o = await find(number);
  const k = o && keyOf(o.statusPageUrl);
  return o?.email && k && same(o.email.trim().toLowerCase(), email.trim().toLowerCase()) ? k : null;
}

export type Stage = "paying" | "in" | "making" | "road" | "out" | "delivered" | "trouble" | "cancelled" | "refunded";

export type OrderView = {
  number: string;
  placed: string;
  total: number;
  lines: { name: string; size: string; quantity: number }[];
  stage: Stage;
  tracking: { company: string | null; number: string | null; url: string | null }[];
  shippedAt: string | null;
  deliveredAt: string | null;
  expectedAt: string | null;
};

const ROAD = new Set(["IN_TRANSIT", "PICKED_UP", "CONFIRMED", "FULFILLED", "LABEL_PRINTED", "LABEL_PURCHASED", "MARKED_AS_FULFILLED", "SUBMITTED"]);

function stageOf(o: Raw): Stage {
  const pay = o.displayFinancialStatus ?? "";
  if (o.cancelledAt) return pay === "REFUNDED" || pay === "PARTIALLY_REFUNDED" ? "refunded" : "cancelled";
  if (pay === "PENDING" || pay === "AUTHORIZED" || pay === "EXPIRED") return "paying";
  const f = o.fulfillments.at(-1);
  if (!f) return Date.now() - Date.parse(o.createdAt) < 6 * 3600_000 ? "in" : "making";
  const s = f.displayStatus ?? "";
  if (s === "DELIVERED") return "delivered";
  if (s === "OUT_FOR_DELIVERY") return "out";
  if (s === "ATTEMPTED_DELIVERY" || s === "FAILURE" || s === "NOT_DELIVERED") return "trouble";
  if (ROAD.has(s) || s === "") return "road";
  return "making";
}

/** the order's page, if `key` is its key; null otherwise (never says which part was wrong) */
export async function orderView(number: string, key: string): Promise<OrderView | null> {
  const o = await find(number);
  const k = o && keyOf(o.statusPageUrl);
  if (!o || !k || !same(k, key)) return null;
  const f = o.fulfillments.at(-1);
  return {
    number: o.name.replace(/^#/, ""),
    placed: o.createdAt,
    total: Number(o.totalPriceSet.shopMoney.amount),
    lines: o.lineItems.nodes.map((l) => {
      const d = l.product ? designOfHandle(l.product.handle) : null;
      const size = l.variant ? sizeOf(l.variant.selectedOptions) : null;
      return { name: d ? `${DESIGNS[d].no} ${DESIGNS[d].name}${DESIGNS[d].city ? ` ${DESIGNS[d].city}` : ""}` : l.title.toLowerCase(), size: size ?? "", quantity: l.quantity };
    }),
    stage: stageOf(o),
    tracking: o.fulfillments.flatMap((x) => x.trackingInfo).filter((t) => t.number || t.url).map((t) => ({ ...t, url: t.url && /^https:\/\//.test(t.url) ? t.url : null })),
    shippedAt: f?.createdAt ?? null,
    deliveredAt: f?.deliveredAt ?? null,
    expectedAt: f?.estimatedDeliveryAt ?? null,
  };
}
