import type { Metadata } from "next";
import Link from "next/link";
import { LINEUPS, paperStill, shirtsOf, STILL_H, STILL_W } from "@/content/lineups";
import { pageMeta } from "@/lib/site";

export const metadata: Metadata = pageMeta({
  title: "lineups",
  description: "Every still breathing lineup: one moment each, its shows and its shirts. Lineup 01 is Fred again.. India, December 2026, fan made.",
  path: "/lineups",
  image: LINEUPS[0].slug,
});

/** The index of lineups, newest first: one row each, its shirts in a strip. */
export default function Lineups() {
  return (
    <div className="px-4 pt-6">
      <div className="page-in grid grid-cols-2 gap-4 border-t border-line pt-1.5 text-[13px] md:grid-cols-4">
        <span className="font-semibold">lineups</span>
        <span className="text-right text-quiet md:text-left">{LINEUPS.length} so far</span>
      </div>
      <h1 className="page-in-2 bigword mt-6 text-[22vw] md:text-[17vw]">lineups</h1>
      <p className="page-in-3 mt-8 max-w-[44ch] text-[clamp(18px,1.8vw,24px)] leading-[1.25] text-ink/85">
        a lineup is one moment: a run of nights, its places, and the shirts drawn for them. each stays up for as long as it&apos;s made.
      </p>

      <ol className="mt-24">
        {LINEUPS.map((l) => (
          <li key={l.slug} className="reveal border-t border-ink">
            <Link href={`/${l.slug}`} className="group grid grid-cols-1 gap-x-4 gap-y-6 pt-3 pb-10 md:grid-cols-12">
              <span className="text-[clamp(64px,10vw,160px)] leading-[0.8] font-extrabold tracking-[-0.05em] tnum transition-colors group-hover:text-blue md:col-span-2">{l.no}</span>
              <span className="md:col-span-4">
                <span className="block text-[clamp(28px,3.4vw,52px)] leading-[0.95] font-extrabold tracking-[-0.045em]">{l.title}</span>
                <span className="mt-2 block text-[14px] text-quiet">{l.tag} · {l.when} · {shirtsOf(l).length} shirts</span>
                <span className="mt-1 block text-[14px] text-quiet">{l.shows.map((s) => s.city).join(", ")}</span>
                <span className="draw mt-6 inline-block text-[15px] font-semibold text-blue">see the lineup →</span>
              </span>
              <span className="grid grid-cols-5 gap-2 md:col-span-6">
                {shirtsOf(l).map((d, i) => (
                  <img key={d} src={paperStill(d, "back")} alt="" width={STILL_W} height={STILL_H} loading={i < 3 ? "eager" : "lazy"}
                    className="aspect-[880/1120] w-full bg-studio object-cover transition-transform duration-700 ease-[cubic-bezier(.2,.7,.2,1)] group-hover:-translate-y-1"
                    style={{ transitionDelay: `${i * 40}ms` }} />
                ))}
              </span>
            </Link>
          </li>
        ))}
        <li className="border-t border-line pt-3 text-[14px] text-quiet">the next one comes when the next moment does.</li>
      </ol>
    </div>
  );
}
