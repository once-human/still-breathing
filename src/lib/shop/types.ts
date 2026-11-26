import type { Design, Size } from "@/content/tee";

/** What the browser is told about the shop: plain views made on the server, never Shopify's own IDs or keys. */

export type CatalogView =
  | { open: false }
  | {
      open: true;
      /** per shirt: its price (rupees, GST in) and, per size, whether it can be bought now */
      shirts: Partial<Record<Design, { price: number; sizes: Partial<Record<Size, boolean>> }>>;
    };

export type BagLine = {
  /** the line's id in this bag (opaque to the browser; only good for this bag, which only its cookie can reach) */
  id: string;
  design: Design;
  size: Size;
  name: string;
  quantity: number;
  /** what this line costs, from Shopify */
  total: number;
};

export type BagView = {
  open: boolean;
  lines: BagLine[];
  count: number;
  /** what the bag costs before checkout, from Shopify (shipping is free; GST is included) */
  subtotal: number;
};

export const EMPTY_BAG: BagView = { open: false, lines: [], count: 0, subtotal: 0 };
