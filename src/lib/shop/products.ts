import { PARTNER_SKUS, costOf } from "@/content/shop";
import { DESIGNS, SIZE_ORDER, type Colour, type Design, type Size } from "@/content/tee";
import { kvKeys } from "./config";
import { ShopError } from "./errors";
import { query } from "./kv";
import { getSettings } from "./settings";

/**
 * The shirts as the shop sells them: the code (content/tee.ts, content/shop.ts) is the seed and the fallback, and a
 * row in the products table overrides it field by field. One price rule, here and only here, used by checkout, the
 * catalog the pages read and the admin:
 *   price ?? ceil((cost + (margin ?? settings.margin)) / 10) * 10
 * Server only. 30-second cache per instance; saveProduct clears it here (the admin also revalidates the
 * PRODUCTS_TAG pages). With no database it's exactly the code.
 */
export const PRODUCTS_TAG = "products";

export type ProductStatus = "draft" | "live" | "soldout";
export type Product = {
  id: Design;
  no: string;
  slug: string;
  name: string;
  city: string | null;
  colour: Colour;
  about: string;
  frontText: string;
  backText: string;
  status: ProductStatus;
  /** what the print partner charges for one, GST included */
  cost: number;
  /** null: the shop's margin from settings */
  margin: number | null;
  /** a fixed price, beating the rule */
  fixedPrice: number | null;
  skus: Partial<Record<Size, string>>;
  images: { url: string; alt: string; kind: "front" | "back" | "card" | "worn" }[];
  sort: number;
  updatedAt: string | null;
  /** the price it sells at now */
  price: number;
};

const COLS = "id, lineup, slug, no, name, city, colour, about, front_text, back_text, status, cost::text, margin::text, price::text, skus::text, images::text, sort::text, updated_at::text";
let made: Promise<unknown> | null = null;
const table = () =>
  (made ??= query(
    `CREATE TABLE IF NOT EXISTS products (
       id text PRIMARY KEY, lineup text, slug text UNIQUE, no text, name text, city text, colour text,
       about text, front_text text, back_text text, status text NOT NULL DEFAULT 'live',
       cost numeric, margin int, price int, skus jsonb NOT NULL DEFAULT '{}', sizes text[],
       images jsonb NOT NULL DEFAULT '[]', sort int, updated_at timestamptz NOT NULL DEFAULT now(), updated_by text)`,
  ).catch((e) => {
    made = null;
    throw e;
  }));

export const priceRule = (cost: number, margin: number) => Math.ceil((cost + margin) / 10) * 10;

function seed(d: Design, i: number): Omit<Product, "price"> {
  const x = DESIGNS[d];
  return { id: d, no: x.no, slug: x.slug, name: x.name, city: x.city, colour: x.colour, about: x.about, frontText: x.front, backText: x.back, status: "live", cost: costOf(d), margin: null, fixedPrice: null, skus: PARTNER_SKUS[d], images: [], sort: i, updatedAt: null };
}

const json = <T>(v: string | null, fallback: T): T => {
  try {
    return v ? (JSON.parse(v) as T) : fallback;
  } catch {
    return fallback;
  }
};
const numOr = (v: string | null, fallback: number | null) => (v === null || v === "" || !Number.isFinite(Number(v)) ? fallback : Number(v));

let cache: { list: Product[]; at: number } | null = null;

/** `fresh` reads the database itself, skipping this instance's 30-second cache of products and settings: for pages
 *  regenerated after revalidateTag(PRODUCTS_TAG), which another instance may have triggered */
export async function products(opts: { fresh?: boolean } = {}): Promise<Product[]> {
  if (!opts.fresh && cache && Date.now() - cache.at < 30_000) return cache.list;
  const { margin } = await getSettings(opts);
  const base = (Object.keys(DESIGNS) as Design[]).map(seed);
  let rows: (string | null)[][] = [];
  if (kvKeys()) {
    try {
      await table();
      rows = await query(`SELECT ${COLS} FROM products`);
    } catch (e) {
      console.error("products:", e instanceof Error ? e.message : e);
      // a fresh read must not hand a stale list to a page cached for an hour: outside the build, let the regeneration
      // fail (Next keeps serving the page it had and tries again); a build goes on with the code's values
      if (opts.fresh && process.env.NEXT_PHASE !== "phase-production-build") throw e;
      if (cache) return cache.list;
    }
  }
  const byId = new Map(rows.map((r) => [r[0], r]));
  const list = base.map((p) => {
    const r = byId.get(p.id);
    const m: Omit<Product, "price"> = r
      ? {
          ...p,
          slug: r[2] ?? p.slug, no: r[3] ?? p.no, name: r[4] ?? p.name, city: r[5] ?? p.city,
          colour: r[6] === "black" || r[6] === "cream" ? r[6] : p.colour,
          about: r[7] ?? p.about, frontText: r[8] ?? p.frontText, backText: r[9] ?? p.backText,
          status: r[10] === "draft" || r[10] === "soldout" || r[10] === "live" ? r[10] : p.status,
          cost: numOr(r[11], p.cost)!, margin: numOr(r[12], null), fixedPrice: numOr(r[13], null),
          skus: { ...p.skus, ...json<Partial<Record<Size, string>>>(r[14], {}) },
          images: json(r[15], p.images), sort: numOr(r[16], p.sort)!, updatedAt: r[17],
        }
      : p;
    return { ...m, price: m.fixedPrice ?? priceRule(m.cost, m.margin ?? margin) };
  });
  list.sort((a, b) => a.sort - b.sort);
  cache = { list, at: Date.now() };
  return list;
}

export const productById = async (id: string) => (await products()).find((p) => p.id === id) ?? null;

/** every shirt's price now, by design */
export const prices = async () => Object.fromEntries((await products()).map((p) => [p.id, p.price])) as Record<Design, number>;

/** the one true price of one shirt, on the server */
export async function priceFor(d: Design) {
  const p = await productById(d);
  if (!p) throw new ShopError("no such shirt", 400);
  return p.price;
}

/** the admin's save: only the fields given change; `by` is kept on the row */
export async function saveProduct(id: Design, patch: Partial<Pick<Product, "status" | "cost" | "margin" | "fixedPrice" | "skus" | "images" | "sort" | "name" | "about" | "frontText" | "backText">>, by: string) {
  if (!Object.hasOwn(DESIGNS, id)) throw new ShopError("no such shirt", 400);
  if (patch.status && !["draft", "live", "soldout"].includes(patch.status)) throw new ShopError("status is draft, live or soldout", 400);
  for (const k of ["cost", "margin", "fixedPrice"] as const) {
    const v = patch[k];
    if (v !== undefined && v !== null && !(Number.isFinite(v) && v >= 0 && v <= 100_000)) throw new ShopError(`${k} must be rupees`, 400);
  }
  if (patch.fixedPrice != null && !Number.isInteger(patch.fixedPrice)) throw new ShopError("a fixed price is whole rupees", 400);
  if (patch.skus && !Object.entries(patch.skus).every(([s, v]) => (SIZE_ORDER as readonly string[]).includes(s) && typeof v === "string" && v.length <= 80)) throw new ShopError("skus: a size → sku text", 400);
  await table();
  const col: Record<string, string> = { status: "status", cost: "cost", margin: "margin", fixedPrice: "price", skus: "skus", images: "images", sort: "sort", name: "name", about: "about", frontText: "front_text", backText: "back_text" };
  const cast: Record<string, string> = { cost: "::numeric", margin: "::int", price: "::int", skus: "::jsonb", images: "::jsonb", sort: "::int" };
  const sets: string[] = [], params: (string | number | null)[] = [id, by.slice(0, 120)];
  for (const [k, v] of Object.entries(patch)) {
    if (v === undefined || !col[k]) continue;
    params.push(v === null ? null : typeof v === "object" ? JSON.stringify(v) : (v as string | number));
    sets.push(`${col[k]} = $${params.length}${cast[col[k]] ?? ""}`);
  }
  await query("INSERT INTO products (id, updated_by) VALUES ($1, $2) ON CONFLICT (id) DO NOTHING", [id, by.slice(0, 120)]);
  if (sets.length) await query(`UPDATE products SET ${sets.join(", ")}, updated_at = now(), updated_by = $2 WHERE id = $1`, params);
  cache = null;
  return productById(id);
}
