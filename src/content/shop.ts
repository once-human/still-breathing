import type { Design } from "@/content/tee";

/**
 * The shop's facts. Shopify holds the price that is charged; this is the price it is set to there, shown while the
 * shop is not open yet. Change both together.
 */
export const SHOP = {
  /** price of one shirt in rupees, GST included, shipping included */
  price: 1499,
  currency: "INR" as const,
  /** the Shopify product handle of each shirt (Shopify → product → URL handle); the site finds shirts by these */
  handles: {
    c: "01-crowd",
    e: "02-i-am-a-party",
    a: "03-map-mumbai",
    d: "04-map-bengaluru",
    f: "05-actual-life",
  } satisfies Record<Design, string>,
  /** most of one shirt in one size per bag, and most shirts in a bag: a bag bigger than this is not one buyer */
  maxPerLine: 5,
  maxPerBag: 10,
  /** made to order: days to print and dispatch, then days on the road, as written on the site */
  make: [2, 5] as [number, number],
  road: [2, 7] as [number, number],
  shipsTo: "India",
};

/** the words on the buy button while there's no shop to buy from */
export const OPENING_SOON = "opening soon";
