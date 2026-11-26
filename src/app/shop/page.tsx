import type { Metadata } from "next";
import Link from "next/link";
import { Label } from "@/components/Label";
import { ShirtCard } from "@/components/ShirtCard";
import { Facts } from "@/components/Facts";
import { LINEUPS, fmtDays } from "@/content/lineups";
import { SHOP } from "@/content/shop";
import { rupees } from "@/lib/shop/money";
import { pageMeta } from "@/lib/site";

export const metadata: Metadata = pageMeta({
  title: "shop",
  description: `Every sahn shirt: fred again.. india, five fan-made shirts for the December shows, ${rupees(SHOP.price)} each with all taxes and shipping included, made to order and sent anywhere in India.`,
  path: "/shop",
  image: LINEUPS[0].slug,
});

/** Every shirt there is, by collection and then by city; each card goes to its shirt. */
export default function Shop() {
  return (
    <div className="px-4 pt-6">
      <div className="page-in grid grid-cols-2 gap-4 border-t border-line pt-1.5 text-[13px] md:grid-cols-4">
        <span className="font-semibold">shop</span>
        <span className="text-right text-quiet md:text-left">{rupees(SHOP.price)} each, all taxes and shipping included</span>
        <span className="hidden text-quiet md:block">made to order</span>
        <span className="hidden text-right text-quiet md:block">sent anywhere in {SHOP.where}</span>
      </div>
      <h1 className="page-in-2 bigword mt-6 text-[30vw] md:text-[22vw]">shop</h1>

      {LINEUPS.map((l) => (
        <section key={l.slug} className="page-in-3 mt-16">
          <div className="flex flex-wrap items-end justify-between gap-4 border-t border-ink pt-2">
            <h2 className="text-[clamp(30px,4.4vw,64px)] leading-[0.95] font-extrabold tracking-[-0.045em]">{l.title}<span className="ml-3 text-[0.45em] font-semibold tracking-normal text-quiet">{l.tag}</span></h2>
            <Link href={`/${l.slug}`} className="draw pb-1 text-[14px] font-semibold text-blue hover:text-ink">the shows and the story →</Link>
          </div>
          <p className="mt-2 text-[13px] text-quiet tnum">{l.shows.map((s) => `${s.city} ${fmtDays(s.days)}`).join(" · ")}</p>
          {l.groups.map((g) => (
            <div key={g.label} className="mt-12">
              <Label note={g.city ? g.city : "both cities"}>{g.label}</Label>
              <ul className="grid grid-cols-2 gap-x-4 gap-y-10 md:grid-cols-3 lg:grid-cols-4">
                {g.shirts.map((d, i) => <li key={d} className="reveal"><ShirtCard d={d} big eager={g === l.groups[0] && i < 2} /></li>)}
              </ul>
            </div>
          ))}
        </section>
      ))}

      <Facts className="mt-28" />
    </div>
  );
}
