import sizes from "../../public/tee/fred/sizes.json";

/** Lineup 01: again.., the shirts for the December shows. Everything the page says about them lives here. */

export type Colour = "black" | "cream";
export type Design = "c" | "a" | "d" | "e";
export type City = "mumbai" | "bengaluru";

/**
 * Four shirts. Same blank, same front (again.. in four scripts); the back is what changes.
 * The tour has two (the crowd, both cities in one drawing, and breath); each city has its map.
 * Each shirt comes in one colour only: a night shirt in black, a day shirt in off white.
 */
export const DESIGNS: Record<Design, { no: string; name: string; city: City | null; colour: Colour; back: string }> = {
  c: { no: "01", name: "crowd", city: null, colour: "black", back: "both nights in one drawing: the crowd from behind, the green line stopping at Madavara on one side, the Mumbai skyline behind the race course on the other, people from both cities in front" },
  e: { no: "02", name: "breath", city: null, colour: "black", back: "both nights through a heat camera: the crowd from the stage, hands up, every breath rising into the December air, 16° in Bengaluru, 20° in Mumbai" },
  a: { no: "03", name: "map", city: "mumbai", colour: "cream", back: "the race course from above, the sea beside it, the sound rolling out from the stage" },
  d: { no: "04", name: "map", city: "bengaluru", colour: "cream", back: "the NICE grounds from above, every person in the crowd drawn, friends holding hands; the last train in at Madavara, Tumakuru Road jammed, the sound rolling out over the village to the lake" },
};
export const CITIES: City[] = ["mumbai", "bengaluru"];

export const COLOURS: Record<Colour, { name: string; hex: string; ink: string }> = {
  black: { name: "black", hex: "#151515", ink: "#4C66F5" },
  cream: { name: "off white", hex: "#FFFAE7", ink: "#2C46BE" },
};

export const SIZE_ORDER = ["XS", "S", "M", "L", "XL", "2XL"] as const;
export type Size = (typeof SIZE_ORDER)[number];

type SizeRow = { chest_round: number; chest_flat: number; length: number; shoulder: number };
export const SIZES = Object.fromEntries(
  SIZE_ORDER.map((s) => [s, (sizes.sizes as Record<string, { cm: SizeRow }>)[s].cm]),
) as Record<Size, SizeRow>;

/** The shows this tee is for. Dates are local (IST). */
export const SHOWS = [
  { city: "delhi ncr", days: ["2026-12-05"] },
  { city: "mumbai", days: ["2026-12-08", "2026-12-09"] },
  { city: "bengaluru", days: ["2026-12-12", "2026-12-13"] },
];

export const THE_TEE = {
  lineup: "lineup 01",
  lede: "again.. in four scripts across the chest, the night drawn across the whole back. Heavy cotton, cut loose, made for a long night on your feet.",
  cloth: [
    ["cotton", "100% combed cotton, single jersey"],
    ["weight", "240 g/m², heavy and dense, not see-through"],
    ["fit", "oversized, dropped shoulder, boxy body"],
    ["collar", "ribbed, keeps its shape"],
    ["hems", "double stitched"],
    ["finish", "pre-shrunk and bio-washed, soft from the first wear"],
  ] as [string, string][],
  care: [
    "wash cold, inside out",
    "no bleach",
    "dry in the shade, the sun fades black",
    "iron inside out, never on the print",
  ],
};
