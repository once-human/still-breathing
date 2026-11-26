import { SHOP } from "@/content/shop";
import { DESIGNS, SIZE_ORDER, type Design, type Size } from "@/content/tee";
import { partnerKeys, shopOpen } from "./config";
import { partnerSku } from "./partner";
import type { BagItem, PayView } from "./types";

/** the sizes a shirt can be ordered in: those with a partner SKU (in the sandbox, any size of the test blank) */
export function sizesOf(d: Design): Size[] {
  if (partnerKeys()?.sandbox) return process.env.QIKINK_SANDBOX_SKU ? [...SIZE_ORDER] : [];
  return SIZE_ORDER.filter((s) => partnerSku(d, s));
}

export function payView(): PayView {
  if (!shopOpen()) return { pay: false, payable: {} };
  const payable: PayView["payable"] = {};
  for (const d of Object.keys(DESIGNS) as Design[]) {
    const sizes = sizesOf(d);
    if (sizes.length) payable[d] = sizes;
  }
  return { pay: Object.keys(payable).length > 0, payable };
}

/** a bag from the browser, checked line by line against what's actually for sale; merged, bounded, or null */
export function cleanBag(raw: unknown): BagItem[] | null {
  if (!Array.isArray(raw) || raw.length === 0 || raw.length > 30) return null;
  const merged = new Map<string, BagItem>();
  for (const l of raw) {
    const d = (l as BagItem)?.design, s = (l as BagItem)?.size, q = (l as BagItem)?.quantity;
    if (typeof d !== "string" || !Object.hasOwn(DESIGNS, d) || typeof s !== "string" || !sizesOf(d as Design).includes(s as Size)) return null;
    if (typeof q !== "number" || !Number.isInteger(q) || q < 1 || q > SHOP.maxPerLine) return null;
    const k = `${d}-${s}`, was = merged.get(k)?.quantity ?? 0;
    merged.set(k, { design: d as Design, size: s as Size, quantity: Math.min(SHOP.maxPerLine, was + q) });
  }
  const items = [...merged.values()];
  return items.reduce((t, l) => t + l.quantity, 0) <= SHOP.maxPerBag ? items : null;
}
