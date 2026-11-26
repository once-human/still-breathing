import type { Design, Size } from "@/content/tee";

/**
 * What the server says about paying: whether the shop can take a payment now, and per shirt the sizes it can be
 * paid for in. Prices aren't here: they come from content/shop.ts, the same numbers the server charges.
 */
export type PayView = { pay: boolean; payable: Partial<Record<Design, Size[]>>; accounts?: boolean };

/** a bag line as the browser keeps it: only which shirt, which size, how many (never a price it could change) */
export type BagItem = { design: Design; size: Size; quantity: number };

/** what the checkout page gets back to open Razorpay's payment window */
export type PayStart = { orderId: string; keyId: string; rzpOrderId: string; amount: number; name: string; prefill: { name: string; email: string; contact: string } };
