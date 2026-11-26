import { PARTNER_SKUS, PRINTS } from "@/content/shop";
import { DESIGNS, type Design, type Size } from "@/content/tee";
import { partnerKeys } from "./config";
import { ShopError } from "./errors";

/**
 * The print partner's custom-store API: a paid order goes in, the partner prints, packs and ships it, paying from
 * the prepaid balance Onkar keeps topped up. Its official reference is offline, so this follows the shape that two
 * independent integrations use (an access token from /api/token, POST /api/order/create with ClientId and
 * Accesstoken headers, values as strings, order numbers of at most 15 letters and digits). Every answer is read
 * defensively and the raw status is kept, so a change on their side shows up as "needs a look", never as a lie.
 */
let token: { value: string; until: number } | null = null;

async function accessToken() {
  const k = partnerKeys();
  if (!k) throw new ShopError("print partner not set up", 503);
  if (token && Date.now() < token.until) return token.value;
  const res = await fetch(`${k.base}/api/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ ClientId: k.id, client_secret: k.secret }),
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  }).catch(() => null);
  if (!res?.ok) throw new ShopError(`partner token ${res?.status ?? "unreachable"}`);
  const j = (await res.json()) as { Accesstoken?: string; expires_in?: number };
  if (!j.Accesstoken) throw new ShopError("partner token missing");
  token = { value: j.Accesstoken, until: Date.now() + Math.max(30, (j.expires_in ?? 3600) - 120) * 1000 };
  return token.value;
}

async function call(path: string, init: { method: "GET" | "POST"; body?: unknown }) {
  const k = partnerKeys();
  if (!k) throw new ShopError("print partner not set up", 503);
  const go = async () =>
    fetch(`${k.base}${path}`, {
      method: init.method,
      headers: { "Content-Type": "application/json", ClientId: k.id, Accesstoken: await accessToken() },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    }).catch(() => null);
  let res = await go();
  if (res?.status === 401) {
    token = null;
    res = await go();
  }
  if (!res) throw new ShopError("partner unreachable");
  const text = await res.text();
  let j: unknown = null;
  try {
    j = JSON.parse(text);
  } catch {
    /* not json */
  }
  if (!res.ok) throw new ShopError(`partner ${res.status}: ${text.slice(0, 300)}`);
  return j as Record<string, unknown> | null;
}

export type ShipTo = { name: string; phone: string; email: string; address1: string; address2: string; city: string; state: string; pin: string };
export type PartnerLine = { design: Design; size: Size; quantity: number; unitPrice: number };

/** the SKU this shirt has in the partner's "My Products" (null: not set up there yet, so not offered) */
export const partnerSku = (d: Design, s: Size) => PARTNER_SKUS[d][s] ?? null;

/** In the sandbox, "My Products" can't be seen, so each line names a plain blank and its print files instead. */
function sandboxLine(l: PartnerLine, site: string) {
  // QIKINK_SANDBOX_SKU is a pattern such as UOsMRnHs-{colour}-{size}: the partner's codes are Bk for black and OFw
  // for off white, and it calls 2XL "XXL"
  const sku = (process.env.QIKINK_SANDBOX_SKU ?? "")
    .replace("{colour}", DESIGNS[l.design].colour === "black" ? "Bk" : "OFw")
    .replace("{size}", l.size === "2XL" ? "XXL" : l.size);
  const p = PRINTS[l.design];
  // the sandbox only needs a reachable picture per placement; the share picture is public already
  const file = () => `${site}/og/home.jpg`;
  return {
    search_from_my_products: 0,
    sku,
    quantity: String(l.quantity),
    price: String(l.unitPrice),
    print_type_id: 1,
    designs: (["front", "back"] as const).map((side) => ({
      design_code: `sahn-${l.design}-${side}`,
      width_inches: String(Math.round(p[side][0] * 10) / 10),
      height_inches: String(Math.round(p[side][1] * 10) / 10),
      placement_sku: side === "front" ? "fr" : "bk",
      design_link: file(),
      mockup_link: file(),
    })),
  };
}

const str = (v: unknown) => (typeof v === "string" || typeof v === "number" ? String(v) : null);
/** the first value found under any of these keys, at any depth */
function dig(o: unknown, keys: string[], depth = 0): string | null {
  if (!o || typeof o !== "object" || depth > 4) return null;
  for (const k of keys) {
    const v = str((o as Record<string, unknown>)[k]);
    if (v) return v;
  }
  for (const v of Object.values(o)) {
    const f = dig(v, keys, depth + 1);
    if (f) return f;
  }
  return null;
}

/** hand a paid order to the partner; returns its id for the order. The order number makes a repeat a duplicate. */
export async function sendToPrint(number: string, lines: PartnerLine[], to: ShipTo, total: number, site: string) {
  const k = partnerKeys();
  if (!k) throw new ShopError("print partner not set up", 503);
  const [first, ...rest] = to.name.trim().split(/\s+/);
  const body = {
    order_number: number,
    qikink_shipping: "1",
    gateway: "Prepaid",
    total_order_value: String(total),
    line_items: lines.map((l) =>
      k.sandbox ? sandboxLine(l, site) : { search_from_my_products: 1, sku: partnerSku(l.design, l.size), quantity: String(l.quantity), price: String(l.unitPrice) },
    ),
    shipping_address: {
      first_name: first ?? to.name,
      last_name: rest.join(" ") || ".",
      address1: to.address1,
      address2: to.address2,
      phone: to.phone,
      email: to.email,
      city: to.city,
      zip: to.pin,
      province: to.state,
      country_code: "IN",
    },
  };
  const j = await call("/api/order/create", { method: "POST", body });
  const id = dig(j, ["order_id", "orderId", "qikink_order_id", "id"]);
  if (!id) throw new ShopError(`partner gave no order id: ${JSON.stringify(j).slice(0, 300)}`);
  return id;
}

export type PartnerStatus = { status: string | null; awb: string | null; courier: string | null; trackingUrl: string | null };

/** where the partner says the order is (status, airway bill, courier, tracking link: whichever it gives) */
export async function partnerStatus(partnerId: string): Promise<PartnerStatus> {
  const j = await call(`/api/order?id=${encodeURIComponent(partnerId)}`, { method: "GET" });
  const url = dig(j, ["tracking_link", "tracking_url", "trackingUrl", "track_url"]);
  return {
    status: dig(j, ["status", "order_status", "shipment_status", "current_status"]),
    awb: dig(j, ["awb", "awb_no", "awb_number", "awbno", "tracking_number"]),
    courier: dig(j, ["courier", "courier_name", "courier_partner", "shipping_partner"]),
    trackingUrl: url && /^https:\/\//.test(url) ? url : null,
  };
}
