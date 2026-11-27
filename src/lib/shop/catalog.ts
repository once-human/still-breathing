import { SHOP } from "@/content/shop";
import { DESIGNS, SIZE_ORDER, type Design, type Size } from "@/content/tee";
import { accountsOpen, partnerKeys, razorpayKeys } from "./config";
import { products, type Product } from "./products";
import { shopAccepting } from "./settings";
import type { BagItem, PayView } from "./types";

/**
 * the sizes a shirt can be ordered in: a live shirt's sizes with a partner SKU (in the sandbox, any size of the test
 * blank). Real money only buys what can really go to print: with live payment keys and the partner still on its
 * sandbox, nothing is offered, so no one pays for a shirt that would only wait.
 */
function sizesOf(p: Product): Size[] {
  if (p.status !== "live") return [];
  if (partnerKeys()?.sandbox) return process.env.QIKINK_SANDBOX_SKU && razorpayKeys()?.test ? [...SIZE_ORDER] : [];
  return SIZE_ORDER.filter((s) => p.skus[s]);
}

/** what the pages get: whether payment is on, the sizes each shirt can be paid for in, and every shirt's price now */
export async function payView(): Promise<PayView> {
  const list = await products();
  const prices = Object.fromEntries(list.map((p) => [p.id, p.price])) as PayView["prices"];
  const status = Object.fromEntries(list.map((p) => [p.id, p.status])) as PayView["status"];
  const accounts = accountsOpen();
  if (!(await shopAccepting())) return { pay: false, payable: {}, accounts, prices, status };
  const payable: PayView["payable"] = {};
  for (const p of list) {
    const sizes = sizesOf(p);
    if (sizes.length) payable[p.id] = sizes;
  }
  return { pay: Object.keys(payable).length > 0, payable, accounts, prices, status };
}

/** a bag from the browser, checked line by line against what's actually for sale; merged, bounded, or null */
export async function cleanBag(raw: unknown): Promise<BagItem[] | null> {
  if (!Array.isArray(raw) || raw.length === 0 || raw.length > 30) return null;
  const byId = new Map((await products()).map((p) => [p.id, p]));
  const merged = new Map<string, BagItem>();
  for (const l of raw) {
    const d = (l as BagItem)?.design, s = (l as BagItem)?.size, q = (l as BagItem)?.quantity;
    const p = typeof d === "string" && Object.hasOwn(DESIGNS, d) ? byId.get(d as Design) : undefined;
    if (!p || typeof s !== "string" || !sizesOf(p).includes(s as Size)) return null;
    if (typeof q !== "number" || !Number.isInteger(q) || q < 1 || q > SHOP.maxPerLine) return null;
    const k = `${d}-${s}`, was = merged.get(k)?.quantity ?? 0;
    merged.set(k, { design: d as Design, size: s as Size, quantity: Math.min(SHOP.maxPerLine, was + q) });
  }
  const items = [...merged.values()];
  return items.reduce((t, l) => t + l.quantity, 0) <= SHOP.maxPerBag ? items : null;
}
