import type { Design, Size } from "@/content/tee";

/**
 * The shop's facts. Price rule (Onkar, 2026-11-26): what the print partner charges for the shirt (the blank, plus the
 * print for that shirt's own front and back) plus ₹500, rounded up to the next ₹10. For now every shirt sells at a fixed
 * ₹1,170 (FIXED_PRICE), which beats the rule. Shipping (about ₹64), the payment fee and marketing come out of what's
 * above cost; the buyer pays nothing on top.
 *
 * Partner rates, from its 2026 price list (qikink.com/help/payments-pricing/pricing, read 2026-11-26):
 * the UC22 blank ₹260; printing on a coloured garment ₹0.9 per sq in, at least ₹100 a placement; 5% GST on the goods.
 * Off white is costed at the coloured-garment rate too: the list's lower rate is for white garments, and off white
 * isn't white. Every price is worked out here, on the server, from these numbers.
 */
export const RATES = { blank: 260, perSqIn: 0.9, minPerPlacement: 100, gst: 0.05, margin: 500 };

const CM = 1 / 2.54;
/** the print boxes, in inches (fronts from pipeline/fronts.py; every back is 13.5 x 18 in: the partner's
 *  largest print, 14 x 18 in, at the art's 3:4) */
const BACK: [number, number] = [13.5, 18];
const LEFT_CHEST: [number, number] = [10.5 * CM, 10.5 * CM];
const WRISTBAND: [number, number] = [(40 * 288) / 1666 * CM, 40 * CM];

export const PRINTS: Record<Design, { front: [number, number]; back: [number, number] }> = {
  c: { front: LEFT_CHEST, back: BACK },
  e: { front: LEFT_CHEST, back: BACK },
  a: { front: LEFT_CHEST, back: BACK },
  d: { front: LEFT_CHEST, back: BACK },
  f: { front: WRISTBAND, back: BACK },
};

const placement = ([w, h]: [number, number]) => Math.max(RATES.minPerPlacement, Math.round(w * h * RATES.perSqIn * 100) / 100);

/** what the print partner charges for one of this shirt, GST included */
export const costOf = (d: Design) => {
  const p = PRINTS[d];
  return Math.round((RATES.blank + placement(p.front) + placement(p.back)) * (1 + RATES.gst) * 100) / 100;
};

/** the price every shirt sells at, beating the rule (Onkar, 2026-11-26: ₹1,170); null lets the rule set it */
export const FIXED_PRICE: number | null = 1170;

/** one shirt's price in rupees: the fixed price, or else cost + the margin, up to the next ₹10 */
export const priceOf = (d: Design) => FIXED_PRICE ?? Math.ceil((costOf(d) + RATES.margin) / 10) * 10;

/** what each shirt is in the print partner's catalogue, per size: the Store SKU (v-…) of its variant under "My
 *  Products" (read 2026-11-27; its product and design SKUs aren't accepted for orders). A shirt with no SKUs isn't
 *  offered; the admin can set them too, and its values win. */
export const PARTNER_SKUS: Record<Design, Partial<Record<Size, string>>> = {
  // 01 crowd (partner product 65128018)
  c: { XS: "v-9Rul3y-AaVZW1sELNBcgubfVrQLf9Hed", S: "v-9Rul3y-AaVZW1sELNBcgubfVrQLf9Haa", M: "v-9Rul3y-AaVZW1sELNBcgubfVrQLf9Hab", L: "v-9Rul3y-AaVZW1sELNBcgubfVrQLf9HaU", XL: "v-9Rul3y-AaVZW1sELNBcgubfVrQLf9HaV", "2XL": "v-9Rul3y-AaVZW1sELNBcgubfVrQLf9Hec" },
  // 02 i am a party (partner product 65128036)
  e: { XS: "v-9Rul3y-AaVZW1sELNBYhubfVrQLf93uV", S: "v-9Rul3y-AaVZW1sELNBYhubfVrQLf93uY", M: "v-9Rul3y-AaVZW1sELNBYhubfVrQLf93uZ", L: "v-9Rul3y-AaVZW1sELNBYhubfVrQLf93ua", XL: "v-9Rul3y-AaVZW1sELNBYhubfVrQLf93ub", "2XL": "v-9Rul3y-AaVZW1sELNBYhubfVrQLf93uU" },
  // 03 map mumbai (partner product 65128046)
  a: { XS: "v-9Rul3y-AaVZW1sELNBUqubfVrQLf9nub", S: "v-9Rul3y-AaVZW1sELNBUqubfVrQLf9nue", M: "v-9Rul3y-AaVZW1sELNBUqubfVrQLf9nuf", L: "v-9Rul3y-AaVZW1sELNBUqubfVrQLf9nuY", XL: "v-9Rul3y-AaVZW1sELNBUqubfVrQLf9nuZ", "2XL": "v-9Rul3y-AaVZW1sELNBUqubfVrQLf9nua" },
  // 04 map bengaluru (partner product 65128056)
  d: { XS: "v-9Rul3y-AaVZW1sELNBUhubfVrQLf-XSf", S: "v-9Rul3y-AaVZW1sELNBUhubfVrQLf-XeU", M: "v-9Rul3y-AaVZW1sELNBUhubfVrQLf-XeV", L: "v-9Rul3y-AaVZW1sELNBUhubfVrQLf-XSc", XL: "v-9Rul3y-AaVZW1sELNBUhubfVrQLf-XSd", "2XL": "v-9Rul3y-AaVZW1sELNBUhubfVrQLf-XSe" },
  // 05 actual life (partner product 65128072)
  f: { XS: "v-9Rul3y-AaVZW1sELNBQvubfVrQLf-Hua", S: "v-9Rul3y-AaVZW1sELNBQvubfVrQLf-Hud", M: "v-9Rul3y-AaVZW1sELNBQvubfVrQLf-Hue", L: "v-9Rul3y-AaVZW1sELNBQvubfVrQLf-Huf", XL: "v-9Rul3y-AaVZW1sELNBQvubfVrQLf-HuY", "2XL": "v-9Rul3y-AaVZW1sELNBQvubfVrQLf-HuZ" },
};

export const SHOP = {
  /** price of one shirt (all five the same today: ₹1,170, fixed), GST and shipping included */
  price: Math.max(...(["c", "e", "a", "d", "f"] as Design[]).map(priceOf)),
  currency: "INR" as const,
  /** the name on the payment page, the emails and the bank statement */
  merchant: "sahn",
  /** most of one shirt in one size per order, and most shirts in an order */
  maxPerLine: 5,
  maxPerBag: 10,
  /** made to order: days to print and dispatch, then days on the road, as written on the site */
  make: [2, 5] as [number, number],
  road: [2, 7] as [number, number],
  /** where it goes, as the site says it (from SELLS_IN) */
  shipsTo: "India",
  where: "india",
};

/**
 * The states a parcel can go to: all of them (null), Onkar's call (2026-11-26). To narrow it (Maharashtra only, say),
 * list the states here and set shipsTo / where to match: checkout, the address form, the pin check and every line on
 * the site follow.
 */
export const SELLS_IN: readonly string[] | null = null;
