import { asset } from "@/lib/asset";
import { DESIGNS, SHOWS, type City, type Design } from "@/content/tee";

/**
 * The collections, newest first, each named for what it is (fred again.. india): its shows, its story and its shirts.
 * A new one drops in by adding an entry here (its shirts in tee.ts); every page, the header, the footer and the
 * sitemap read from this list. Its slug is its address: /fred-again-india, /fred-again-india/<shirt>.
 */
export type Lineup = {
  slug: string;
  no: string;
  title: string;
  tag: string;
  when: string;
  shows: { city: string; days: string[]; ground: string }[];
  lede: string;
  story: string[];
  groups: { label: string; city: City | null; shirts: Design[] }[];
  /** the shirt whose back artwork stands for the collection on the home page */
  hero: Design;
};

const GROUND: Record<string, string> = { "delhi ncr": "gurugram", mumbai: "the race course, mahalaxmi", bengaluru: "the nice grounds, madavara" };

export const LINEUPS: Lineup[] = [
  {
    slug: "fred-again-india",
    no: "01",
    title: "fred again.. india",
    tag: "fan made",
    when: "december 2026",
    shows: SHOWS.map((s) => ({ ...s, ground: GROUND[s.city] ?? s.city })),
    lede: "five shirts for the december shows in india. two for the whole tour, and the ground itself for each city, drawn by hand from where it really is.",
    story: [
      "five shirts for five nights in december: delhi on the 5th, mumbai on the 8th and 9th, bengaluru on the 12th and 13th. not a tour shirt with a list of dates on the back, but the nights themselves.",
      "the crowd and i am a party belong to the whole tour: both cities in one drawing, the crowd from behind and the crowd from the stage. the maps are the grounds seen from above, the race course by the sea and the nice grounds at the end of the green line, every road and rail line where it really is. actual life is the walk home after, in bengaluru's rain.",
      "each one is made to order, one at a time, and sent anywhere in maharashtra. it's a fan's shirt: drawn for the shows, not by them.",
    ],
    groups: [
      { label: "the tour", city: null, shirts: ["c", "e"] },
      { label: "mumbai", city: "mumbai", shirts: ["a"] },
      { label: "bengaluru", city: "bengaluru", shirts: ["d", "f"] },
    ],
    hero: "c",
  },
];

export const CURRENT = LINEUPS[0];

export const lineupOf = (slug: string) => LINEUPS.find((l) => l.slug === slug);
export const shirtsOf = (l: Lineup) => l.groups.flatMap((g) => g.shirts);
export const lineupOfShirt = (d: Design) => LINEUPS.find((l) => shirtsOf(l).includes(d))!;
export const shirtBySlug = (l: Lineup, slug: string) => shirtsOf(l).find((d) => DESIGNS[d].slug === slug);
export const shirtHref = (d: Design) => `/${lineupOfShirt(d).slug}/${DESIGNS[d].slug}`;

/** "again.. mumbai" over "map": the shirt's two-line name, as printed on the page */
export const shirtTitle = (d: Design) => ({ top: `again.. ${DESIGNS[d].city ?? "india"}`, name: DESIGNS[d].name });
export const shirtLabel = (d: Design) => `${DESIGNS[d].name}${DESIGNS[d].city ? `, ${DESIGNS[d].city}` : ""}`;

/** The studio renders. Paper: the tee alone on the studio paper. Worn: at the show, him by default, or her. */
export type StillView = "front" | "q" | "back";
export const paperStill = (d: Design, v: StillView) => asset(`/tee/still/${d}/tee/${v}.webp`);

export const STILL_W = 880, STILL_H = 1120;
/** each side's whole print area, uncropped and at one scale (scripts/art.mjs), shown on the shirt's own colour */
export const printArt = (d: Design, side: "front" | "back") => asset(`/tee/art/${d}-${side}.webp`);

/** "08 + 09.12" */
export const fmtDays = (days: string[]) => days.map((d) => d.slice(8, 10)).join(" + ") + "." + days[0].slice(5, 7);
