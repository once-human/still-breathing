import { unstable_cache } from "next/cache";
import { PRODUCTS_TAG, products } from "@/lib/shop/products";
import { rupees } from "@/lib/shop/money";
import type { Design } from "@/content/tee";

/**
 * The shop's catalog as the public pages read it: the same prices and statuses checkout uses (lib/shop/products),
 * cached under the products tag so the pages stay static and the admin's revalidateTag refreshes them; an hour
 * at most otherwise.
 */
export const catalog = unstable_cache(products, ["public-catalog"], { tags: [PRODUCTS_TAG], revalidate: 3600 });

/** each shirt's price now */
export const livePrices = async () => Object.fromEntries((await catalog()).map((p) => [p.id, p.price])) as Record<Design, number>;

/** the shirts on sale or sold out: a draft is on no page */
export const shown = async () => new Set((await catalog()).filter((p) => p.status !== "draft").map((p) => p.id));
export const drafts = async () => (await catalog()).filter((p) => p.status === "draft").map((p) => p.id);

/** one line for "what a shirt costs": "₹1,270 each" when they're all one price, "from ₹1,070" when not */
export async function priceLine() {
  const list = (await catalog()).filter((p) => p.status !== "draft").map((p) => p.price);
  if (!list.length) return { each: "", from: "", one: true };
  const lo = Math.min(...list), hi = Math.max(...list);
  return { each: lo === hi ? `${rupees(lo)} each` : `from ${rupees(lo)}`, from: lo === hi ? rupees(lo) : `from ${rupees(lo)}`, one: lo === hi };
}
