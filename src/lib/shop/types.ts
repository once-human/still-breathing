import type { Design, Size } from "@/content/tee";

/**
 * What the server says about paying: whether the shop can take a payment now, and per shirt the sizes it can be
 * paid for in. With the prices the server charges now.
 */
export type PayView = {
  pay: boolean;
  payable: Partial<Record<Design, Size[]>>;
  accounts?: boolean;
  /** every shirt's price now, from the server's one price rule (the code's priceOf is only the first paint) */
  prices?: Partial<Record<Design, number>>;
  /** draft shirts aren't shown; sold out ones are shown with no buy */
  status?: Partial<Record<Design, "draft" | "live" | "soldout">>;
};

/** a bag line as the browser keeps it: only which shirt, which size, how many (never a price it could change) */
export type BagItem = { design: Design; size: Size; quantity: number };

/** what the checkout page gets back to open Razorpay's payment window */
export type PayStart = { orderId: string; keyId: string; rzpOrderId: string; amount: number; name: string; prefill: { name: string; email: string; contact: string } };
