import { products as catalogProducts, lineups as catalogLineups, type Product } from "@/lib/catalog";
import { rupees } from "@/lib/shop/money";
import { DESIGNS, type Design } from "@/content/tee";
import type { ShirtTexts } from "@/components/ShirtText";

/**
 * What the public pages read from the admin's catalog (lib/catalog: the shop's prices and statuses, with the admin's
 * names, words and order over the code). It's cached on the products tag, so the pages stay static and an admin save
 * refreshes them.
 */
export const catalog = catalogProducts;
export const lineups = catalogLineups;

/** each shirt's price now */
export const livePrices = async () => Object.fromEntries((await catalog()).map((p) => [p.id, p.price])) as Record<Design, number>;

/** the shirts on sale or sold out, in the admin's order: a draft is on no page */
export const shownList = async () => (await catalog()).filter((p) => p.status !== "draft").map((p) => p.id);
export const shown = async () => new Set(await shownList());
export const drafts = async () => (await catalog()).filter((p) => p.status === "draft").map((p) => p.id);

/** one line for "what a shirt costs": "₹1,170 each" when they're all one price, "from ₹1,070" when not */
export async function priceLine() {
  const list = (await catalog()).filter((p) => p.status !== "draft").map((p) => p.price);
  if (!list.length) return { each: "", from: "", one: true };
  const lo = Math.min(...list), hi = Math.max(...list);
  return { each: lo === hi ? `${rupees(lo)} each` : `from ${rupees(lo)}`, from: lo === hi ? rupees(lo) : `from ${rupees(lo)}`, one: lo === hi };
}

/** the words each shirt goes by, for the client parts of the page (ShirtText) */
export async function shirtTexts(): Promise<ShirtTexts> {
  const list = await catalog();
  return {
    order: list.filter((p) => p.status !== "draft").map((p) => p.id),
    text: Object.fromEntries(list.map((p) => [p.id, { name: p.name, about: p.about }])) as ShirtTexts["text"],
  };
}

/** a shirt's title and label as the catalog names it, on the server (the same shapes as lineups.ts) */
export async function named(d: Design) {
  const p: Product | undefined = (await catalog()).find((x) => x.id === d);
  const name = p?.name ?? DESIGNS[d].name, about = p?.about ?? DESIGNS[d].about, city = DESIGNS[d].city;
  return { top: `again.. ${city ?? "india"}`, name, about, label: `${name}${city ? `, ${city}` : ""}` };
}
