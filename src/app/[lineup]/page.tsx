import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Label } from "@/components/Label";
import { Now } from "@/components/Now";
import { ShirtCard } from "@/components/ShirtCard";
import { DESIGNS } from "@/content/tee";
import { LINEUPS, lineupOf, fmtDays, shirtHref, shirtLabel, shirtsOf, wornStill, STILL_H, STILL_W } from "@/content/lineups";
import { pageMeta } from "@/lib/site";

type Params = { params: Promise<{ lineup: string }> };

export const dynamicParams = false;
export const generateStaticParams = () => LINEUPS.map((l) => ({ lineup: l.slug }));

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const l = lineupOf((await params).lineup);
  if (!l) return {};
  return pageMeta({ title: `lineup ${l.no} · ${l.title} · ${l.tag}`, description: `${l.lede} Lineup ${l.no} of still breathing, ${l.when}.`, path: `/${l.slug}`, image: l.slug });
}

export default async function LineupPage({ params }: Params) {
  const l = lineupOf((await params).lineup);
  if (!l) notFound();
  const shirts = shirtsOf(l);
  const forCity = (city: string) => shirts.filter((d) => DESIGNS[d].city === null || DESIGNS[d].city === city);

  return (
    <>
      {/* the title, as loud as the page gets */}
      <header className="px-4 pt-6">
        <div className="page-in grid grid-cols-2 gap-4 border-t border-line pt-1.5 text-[13px] md:grid-cols-4">
          <span className="font-semibold">lineup {l.no}</span>
          <span className="text-quiet">{l.tag}</span>
          <span className="hidden text-quiet md:block">{l.when}</span>
          <span className="hidden text-right text-quiet md:block">{shirts.length} shirts</span>
        </div>
        <h1 className="page-in-2 bigword mt-6 text-[19vw] md:text-[15.5vw]">
          <span className="block">fred again..</span>
          <span className="block text-right text-quiet">india</span>
        </h1>
        <p className="page-in-3 mt-10 max-w-[30ch] text-[clamp(22px,2.6vw,36px)] leading-[1.12] font-semibold tracking-[-0.02em] md:ml-[calc((100%-11rem)/12*4+4rem)]">{l.lede}</p>
      </header>

      {/* the five nights */}
      <section className="mt-32 grid grid-cols-1 gap-x-4 px-4 md:grid-cols-12">
        <div className="md:col-span-12 lg:col-span-10 lg:col-start-2">
          <Label note="december, local time">the shows</Label>
          <ul>
            {l.shows.map((x) => (
              <li key={x.city} className="reveal grid grid-cols-[1fr_auto] items-baseline gap-x-6 border-t border-line py-3 md:grid-cols-12 md:gap-x-4">
                <span className="text-[clamp(34px,6vw,84px)] leading-[0.95] font-extrabold tracking-[-0.045em] md:col-span-6">{x.city}</span>
                <span className="text-[clamp(18px,2.2vw,30px)] font-semibold text-quiet tnum md:col-span-2">{fmtDays(x.days)}</span>
                <span className="col-span-2 mt-2 text-[13px] text-quiet md:col-span-4 md:mt-0">
                  {x.ground}
                  <span className="mt-1 block text-ink">
                    {forCity(x.city).map((d, i) => <span key={d}>{i ? ", " : ""}<Link href={shirtHref(d)} className="draw hover:text-blue">{shirtLabel(d)}</Link></span>)}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* the shirts, by where they belong */}
      <section className="mt-32 px-4">
        {l.groups.map((g) => (
          <div key={g.label} className="mt-20 grid grid-cols-1 gap-x-4 first:mt-0 md:grid-cols-12">
            <div className="md:col-span-12 lg:col-span-10 lg:col-start-2">
              <Label note={g.city ? `${g.shirts.length === 1 ? "its map" : "its map and its night"}` : "both cities in each"}>{g.label}</Label>
            </div>
            <ul className="grid grid-cols-2 gap-x-4 gap-y-10 md:col-span-12 md:grid-cols-3 lg:col-span-10 lg:col-start-2 lg:grid-cols-4">
              {g.shirts.map((d, i) => <li key={d} className="reveal"><ShirtCard d={d} big eager={g === l.groups[0] && i < 2} /></li>)}
            </ul>
          </div>
        ))}
      </section>

      {/* the story, beside the crowd worn at the show */}
      <section className="mt-36 grid grid-cols-1 gap-x-4 gap-y-10 px-4 md:grid-cols-12">
        <div className="reveal md:col-span-5 lg:col-span-4 lg:col-start-2">
          <img src={wornStill(l.hero, 180)} alt="the crowd, worn at the show, from behind" width={STILL_W} height={STILL_H} loading="lazy" decoding="async" className="aspect-[880/1120] w-full bg-[#0b0a0a] object-cover" />
        </div>
        <div className="md:col-span-7 lg:col-span-5 lg:col-start-7">
          <Label>the story</Label>
          <div className="space-y-5 text-[clamp(17px,1.5vw,21px)] leading-[1.4] text-ink/85">
            {l.story.map((p) => <p key={p.slice(0, 20)} className="reveal max-w-[44ch]">{p}</p>)}
          </div>
          <Link href="/made" className="draw mt-8 inline-block font-semibold text-blue hover:text-ink">how they&apos;re made →</Link>
        </div>
      </section>

      <div className="mt-32"><Now /></div>
    </>
  );
}
