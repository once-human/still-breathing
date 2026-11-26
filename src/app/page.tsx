import type { Metadata } from "next";
import Link from "next/link";
import { Label } from "@/components/Label";
import { Now } from "@/components/Now";
import { Countdown } from "@/components/Countdown";
import { ShirtCard } from "@/components/ShirtCard";
import { Facts } from "@/components/Facts";
import { CURRENT, fmtDays, paperStill, shirtHref, shirtsOf, STILL_H, STILL_W } from "@/content/lineups";
import { pageMeta } from "@/lib/site";
import { SHOP } from "@/content/shop";
import { shown } from "@/lib/live";

export const metadata: Metadata = pageMeta({
  description: "sahn makes one shirt per moment. fred again.. india: five fan-made shirts for Fred again..'s December shows in India, drawn by hand from the crowd and the grounds, made to order and sent anywhere in India.",
  path: "/",
});

/** The front door: the name, the collection that's on now, its shirts, and what the label is. Stills only, no 3D. */
export default async function Home() {
  const on = await shown(), l = CURRENT, shirts = shirtsOf(l).filter((d) => on.has(d));
  return (
    <>
      <section className="px-4 pt-6">
        <div className="page-in grid grid-cols-2 gap-4 border-t border-line pt-1.5 text-[13px] md:grid-cols-4">
          <Link href={`/${l.slug}`} className="font-semibold hover:text-blue">{l.title}</Link>
          <span className="text-right text-quiet md:text-left">{l.tag}</span>
          <span className="hidden text-quiet md:block">made to order, sent anywhere in {SHOP.where}</span>
          <span className="hidden text-right tnum md:block"><Countdown short /></span>
        </div>
        <div className="mt-4 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <h1 className="page-in-2 bigword text-[46vw] md:text-[30vw]">sahn</h1>
          <p className="page-in-3 max-w-[18ch] pb-[1.2vw] text-[clamp(22px,2.4vw,36px)] leading-[1.02] font-extrabold tracking-[-0.04em] md:text-right">one shirt per moment.<span className="block text-quiet">fred again.. india is on now.</span></p>
        </div>
      </section>

      {/* the collection, up front */}
      <section className="mt-14 grid grid-cols-1 gap-x-4 gap-y-10 px-4 md:grid-cols-12">
        <Link href={shirtHref(l.hero)} className="page-in-3 group relative block overflow-hidden bg-studio md:col-span-7">
          <img src={paperStill(l.hero, "back")} alt="crowd, the back, on the studio paper" width={STILL_W} height={STILL_H} fetchPriority="high" className="aspect-[880/1120] w-full object-cover transition-transform duration-[1.6s] ease-[cubic-bezier(.2,.7,.2,1)] group-hover:scale-[1.02]" />
          <span className="absolute bottom-3 left-3 text-[13px] text-black/60">crowd, the back</span>
        </Link>
        <div className="flex flex-col md:col-span-5 lg:col-span-4 lg:col-start-9">
          <Label note={l.when}>{l.tag}</Label>
          <p className="text-[clamp(30px,3.6vw,54px)] leading-[0.95] font-extrabold tracking-[-0.045em]">{l.title}<span className="block text-quiet">five shirts</span></p>
          <p className="mt-6 max-w-[38ch] text-[16px] text-ink/85">{l.lede}</p>
          <ul className="mt-6 space-y-0.5 text-[14px] tnum">
            {l.shows.map((x) => <li key={x.city} className="flex justify-between border-t border-line py-1"><span>{x.city}</span><span className="text-quiet">{fmtDays(x.days)}</span></li>)}
          </ul>
          <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-[15px] font-semibold">
            <Link href={`/${l.slug}`} className="draw text-blue hover:text-ink">see all five →</Link>
            <a href="#shirts" className="draw hover:text-blue">the five shirts ↓</a>
          </div>
          <div className="mt-auto hidden grid-cols-2 gap-4 pt-12 md:grid">
            <Link href={shirtHref("a")} className="group block bg-studio"><img src={paperStill("a", "q")} alt="map, mumbai, on the studio paper" width={STILL_W} height={STILL_H} loading="lazy" className="aspect-[880/1120] w-full object-cover transition-opacity group-hover:opacity-85" /></Link>
            <Link href={shirtHref("e")} className="group block bg-studio"><img src={paperStill("e", "front")} alt="i am a party, the front, on the studio paper" width={STILL_W} height={STILL_H} loading="lazy" className="aspect-[880/1120] w-full object-cover transition-opacity group-hover:opacity-85" /></Link>
          </div>
        </div>
      </section>

      <section className="mt-20 px-4"><Facts /></section>

      {/* the shirts */}
      <section id="shirts" className="mt-36 scroll-mt-20 px-4">
        <Label note={<Link href={`/${l.slug}`} className="draw hover:text-ink">by city, with the shows</Link>}>{l.title} · the shirts</Label>
        <ul className="grid grid-cols-2 gap-x-4 gap-y-10 md:grid-cols-3 lg:grid-cols-5">
          {shirts.map((d) => <li key={d} className="reveal"><ShirtCard d={d} /></li>)}
        </ul>
      </section>

      {/* what this is */}
      <section className="mt-40 grid grid-cols-1 gap-x-4 px-4 md:grid-cols-12">
        <div className="md:col-span-12 lg:col-span-10 lg:col-start-2">
          <Label>sahn</Label>
          <p className="reveal max-w-[22ch] text-[clamp(32px,5.2vw,80px)] leading-[0.98] font-extrabold tracking-[-0.045em]">
            a night you were there, <span className="text-quiet">drawn by hand and worn after.</span>
          </p>
        </div>
        <div className="mt-12 grid grid-cols-1 gap-x-4 gap-y-6 text-[15px] text-ink/85 md:col-span-12 md:grid-cols-12 lg:col-span-10 lg:col-start-2 lg:grid-cols-10">
          <p className="reveal max-w-[40ch] md:col-span-6 lg:col-span-4">
            every back is a real place on a real night: the ground from above, the crowd from behind, the walk home after. drawn by hand from maps and the horizon you&apos;d actually see from the field, in a few inks and a little blue.
          </p>
          <p className="reveal max-w-[40ch] md:col-span-6 lg:col-span-4 lg:col-start-6">
            heavy 240 gsm cotton, cut loose for a long night on your feet, fitted on indian bodies, made one at a time when you order it. the 3d you can turn on each shirt is the same tee, cut from the same size chart.
          </p>
          <div className="flex gap-6 font-semibold md:col-span-12 lg:col-span-10">
            <Link href="/made" className="draw text-blue hover:text-ink">how it&apos;s made →</Link>
            <Link href="/shop" className="draw hover:text-blue">shop →</Link>
          </div>
        </div>
      </section>

      <div className="mt-36"><Now /></div>
    </>
  );
}
