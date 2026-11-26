import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { COLOURS, DESIGNS } from "@/content/tee";
import { drafts, livePrices } from "@/lib/live";
import { rupees } from "@/lib/shop/money";
import { LINEUPS, lineupOf, shirtBySlug, shirtsOf, shirtTitle } from "@/content/lineups";
import { pageMeta } from "@/lib/site";

type Params = { params: Promise<{ lineup: string; shirt: string }> };

export const dynamicParams = false;
export const generateStaticParams = () => LINEUPS.flatMap((l) => shirtsOf(l).map((d) => ({ lineup: l.slug, shirt: DESIGNS[d].slug })));

async function find(params: Params["params"]) {
  const p = await params, l = lineupOf(p.lineup), d = l ? shirtBySlug(l, p.shirt) : undefined;
  return l && d ? { l, d } : null;
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const f = await find(params);
  if (!f) return {};
  const { l, d } = f, t = shirtTitle(d), s = DESIGNS[d];
  return pageMeta({
    title: `${t.top} ${t.name}`,
    description: `${t.top}, ${t.name}: a ${COLOURS[s.colour].name} tee, ${l.title} (${l.tag}), ${rupees((await livePrices())[d])}. ${s.about.charAt(0).toUpperCase() + s.about.slice(1)} Heavy 240 gsm cotton, made to order and sent anywhere in India.`,
    path: `/${l.slug}/${s.slug}`,
    image: s.slug,
  });
}

/** The whole shirt page is the stage in the layout above (3D, the picks, the buy button); this only names it. */
export default async function ShirtPage({ params }: Params) {
  const f = await find(params);
  if (!f || (await drafts()).includes(f.d)) notFound();
  return null;
}
