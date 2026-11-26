import type { Design, Size } from "@/content/tee";

/**
 * The shop's facts. Price rule (Onkar, 2026-11-26): what the print partner charges for the shirt (the blank, plus the
 * print for that shirt's own front and back) plus ₹400, rounded up to the next ₹10. Shipping (about ₹64), the
 * payment fee and marketing come out of the ₹400; the buyer pays nothing on top.
 *
 * Partner rates, from its 2026 price list (qikink.com/help/payments-pricing/pricing, read 2026-11-26):
 * the UC22 blank ₹260; printing on a coloured garment ₹0.9 per sq in, at least ₹100 a placement; 5% GST on the goods.
 * Off white is costed at the coloured-garment rate too: the list's lower rate is for white garments, and off white
 * isn't white. Every price is worked out here, on the server, from these numbers.
 */
export const RATES = { blank: 260, perSqIn: 0.9, minPerPlacement: 100, gst: 0.05, margin: 400 };

const CM = 1 / 2.54;
/** the print boxes, in inches (fronts from pipeline/fronts.py; every back is 15 x 20 in) */
const BACK: [number, number] = [15, 20];
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

/** one shirt's price in rupees: cost + ₹400, up to the next ₹10 */
export const priceOf = (d: Design) => Math.ceil((costOf(d) + RATES.margin) / 10) * 10;

/** what each shirt is in the print partner's catalogue, per size: its SKU under "My Products" once the shirt is made
 *  there with its print files. A shirt with no SKUs isn't offered (fill these in from the partner's dashboard). */
export const PARTNER_SKUS: Record<Design, Partial<Record<Size, string>>> = {
  c: {},
  e: {},
  a: {},
  d: {},
  f: {},
};

export const SHOP = {
  /** price of one shirt (all five cost the same today: ₹1,070), GST and shipping included */
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
  shipsTo: "India",
};
