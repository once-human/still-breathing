import { SHOP } from "@/content/shop";
import { SIZE_ORDER, type Design, type Size } from "@/content/tee";
import { shopOpen } from "./config";
import { storefront } from "./storefront";
import type { CatalogView } from "./types";

/** the cache tag the webhook refreshes when a product, price or stock level changes in Shopify */
export const CATALOG_TAG = "shop:catalog";

type Variant = { id: string; availableForSale: boolean; price: { amount: string; currencyCode: string }; selectedOptions: { name: string; value: string }[] };
type Product = { handle: string; availableForSale: boolean; variants: { nodes: Variant[] } } | null;

const DESIGNS = Object.keys(SHOP.handles) as Design[];

/** XXL and 2XL are the same size; Shopify's option values are whatever Qikink pushed */
export const toSize = (v: string): Size | null => {
  const s = v.trim().toUpperCase().replace(/^XXL$/, "2XL");
  return (SIZE_ORDER as readonly string[]).includes(s) ? (s as Size) : null;
};

export const sizeOf = (opts: { name: string; value: string }[]) => {
  const o = opts.find((x) => /size/i.test(x.name)) ?? (opts.length === 1 ? opts[0] : undefined);
  return o ? toSize(o.value) : null;
};

export const designOfHandle = (handle: string): Design | null =>
  DESIGNS.find((d) => SHOP.handles[d] === handle) ?? null;

const QUERY = `query Catalog {
${DESIGNS.map((d) => `  ${d}: product(handle: ${JSON.stringify(SHOP.handles[d])}) { ...P }`).join("\n")}
}
fragment P on Product {
  handle
  availableForSale
  variants(first: 30) { nodes { id availableForSale price { amount currencyCode } selectedOptions { name value } } }
}`;

export type Catalog = Partial<Record<Design, { price: number; sizes: Partial<Record<Size, { id: string; available: boolean }>> }>>;

/** The five shirts as Shopify has them right now (cached five minutes, refreshed at once by the product webhook). */
export async function getCatalog(): Promise<Catalog> {
  if (!shopOpen()) return {};
  const data = await storefront<Record<Design, Product>>(QUERY, {}, { cache: { revalidate: 300, tags: [CATALOG_TAG] } });
  const out: Catalog = {};
  for (const d of DESIGNS) {
    const p = data[d];
    if (!p) continue;
    const sizes: Partial<Record<Size, { id: string; available: boolean }>> = {};
    let price = Infinity;
    for (const v of p.variants.nodes) {
      const size = sizeOf(v.selectedOptions);
      if (!size || v.price.currencyCode !== SHOP.currency) continue;
      sizes[size] = { id: v.id, available: v.availableForSale };
      price = Math.min(price, Number(v.price.amount));
    }
    if (Number.isFinite(price) && Object.keys(sizes).length) out[d] = { price, sizes };
  }
  return out;
}

/** the catalog without Shopify's IDs, for the browser */
export async function catalogView(): Promise<CatalogView> {
  if (!shopOpen()) return { open: false };
  const cat = await getCatalog();
  const shirts: Extract<CatalogView, { open: true }>["shirts"] = {};
  for (const d of Object.keys(cat) as Design[]) {
    const c = cat[d]!;
    shirts[d] = { price: c.price, sizes: Object.fromEntries(Object.entries(c.sizes).map(([s, v]) => [s, v!.available])) };
  }
  // keys are set but no shirt is found (handles not set yet, or not on the Headless channel): still not open
  return Object.keys(shirts).length ? { open: true, shirts } : { open: false };
}
