import type { Design, Size } from "@/content/tee";

/** What the browser is told about the shop: plain facts made on the server. */
export type CatalogView =
  | { open: false }
  | {
      open: true;
      /** per shirt: its price (rupees, GST and shipping in) and the sizes it can be bought in now */
      shirts: Partial<Record<Design, { price: number; sizes: Size[] }>>;
      maxPerLine: number;
      maxPerBag: number;
    };

/** a bag line as the browser keeps it: only which shirt, which size, how many (never a price it could change) */
export type BagItem = { design: Design; size: Size; quantity: number };

/** what the checkout page gets back to open Razorpay's payment window */
export type PayStart = { orderId: string; keyId: string; rzpOrderId: string; amount: number; name: string; prefill: { name: string; email: string; contact: string } };
