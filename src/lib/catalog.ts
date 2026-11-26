import "server-only";
import { unstable_cache } from "next/cache";
import { LINEUPS, type Lineup } from "@/content/lineups";
import { DESIGNS, SIZE_ORDER, type City, type Colour, type Design, type Size } from "@/content/tee";
import { PRODUCTS_TAG, products as shopProducts, type Product as ShopProduct, type ProductStatus } from "@/lib/shop/products";

/**
 * The catalog the public pages render: each shirt as tee.ts has it, with what the admin saved over it (status, price,
 * name, about, pictures) from the shop's products(), which holds the one price rule. Cached across requests on the
 * `products` tag, which an admin save revalidates. With no database it is exactly the code.
 * Server only: client components get the list as props.
 */
export type Product = {
  id: Design;
  /** the collection's slug (/fred-again-india) */
  lineup: string;
  no: string;
  slug: string;
  name: string;
  city: City | null;
  colour: Colour;
  about: string;
  front: string;
  back: string;
  status: ProductStatus;
  /** what it sells at now, from the server's one price rule */
  price: number;
  /** the sizes the shirt is offered in on the page (whether each can be paid for is the shop's /api/shop/catalog) */
  sizes: Size[];
  images: ShopProduct["images"];
  sort: number;
  /** has the 3D viewer's assets (every shirt from the code does) */
  has3d: boolean;
};

const lineupOfId = (d: Design) => LINEUPS.find((l) => l.groups.some((g) => g.shirts.includes(d)))?.slug ?? LINEUPS[0].slug;

function shape(p: ShopProduct): Product {
  const x = DESIGNS[p.id];
  return {
    id: p.id, lineup: lineupOfId(p.id), no: p.no, slug: p.slug, name: p.name, city: (p.city as City | null) ?? null, colour: p.colour,
    about: p.about, front: p.frontText ?? x.front, back: p.backText ?? x.back, status: p.status, price: p.price,
    sizes: [...SIZE_ORDER], images: p.images, sort: p.sort, has3d: Object.hasOwn(DESIGNS, p.id),
  };
}

/** every shirt, drafts included (pages leave drafts out), in the order the admin set */
export const products = unstable_cache(async (): Promise<Product[]> => (await shopProducts({ fresh: true })).map(shape), ["catalog-products"], { tags: [PRODUCTS_TAG], revalidate: 3600 });

export const productBySlug = async (slug: string) => (await products()).find((p) => p.slug === slug) ?? null;

/** the price of one shirt now (the same number checkout charges) */
export const priceFor = async (id: string) => (await products()).find((p) => p.id === id)?.price ?? null;

/**
 * The collections in today's lineups.ts shape: each group keeps its shirts that aren't drafts, in the admin's order;
 * a group left empty is dropped.
 */
export async function lineups(): Promise<Lineup[]> {
  const list = await products();
  const by = new Map(list.map((p) => [p.id, p]));
  return LINEUPS.map((l) => ({
    ...l,
    groups: l.groups
      .map((g) => ({ ...g, shirts: g.shirts.filter((d) => by.get(d) && by.get(d)!.status !== "draft").sort((a, b) => by.get(a)!.sort - by.get(b)!.sort) }))
      .filter((g) => g.shirts.length),
  }));
}
