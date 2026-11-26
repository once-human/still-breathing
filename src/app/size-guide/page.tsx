import type { Metadata } from "next";
import Link from "next/link";
import { Label } from "@/components/Label";
import { SIZES, SIZE_ORDER, THE_TEE } from "@/content/tee";
import { CURRENT, shirtHref } from "@/content/lineups";
import { pageMeta } from "@/lib/site";

export const metadata: Metadata = pageMeta({
  title: "size guide",
  description: "still breathing sizes XS to 2XL, measured on the garment in cm: chest, length and shoulder, how to measure a tee you own, and how the oversized cut fits.",
  path: "/size-guide",
});

const ROWS: [string, string, "chest_round" | "chest_flat" | "length" | "shoulder"][] = [
  ["chest, all round", "the full way round, just under the arms", "chest_round"],
  ["chest, flat", "armpit to armpit, laid flat", "chest_flat"],
  ["length", "from the top of the shoulder by the collar down to the hem", "length"],
  ["shoulder", "seam to seam across the back", "shoulder"],
];

/** One cut, six sizes, every number in cm on the garment itself. */
export default function SizeGuide() {
  return (
    <div className="pt-6">
      <div className="px-4">
        <h1 className="page-in bigword text-[20vw] md:text-[13vw]">size guide</h1>
        <p className="page-in-2 mt-6 max-w-[48ch] text-[clamp(18px,1.8vw,24px)] leading-[1.25] text-ink/85">
          one cut for every shirt: oversized, with a dropped shoulder and a straight, boxy body. it&apos;s cut big, so most people take their usual size; go one down for a closer fit.
        </p>
      </div>

      <section className="page-in-3 mt-20 grid grid-cols-1 gap-x-4 px-4 md:grid-cols-12">
        <div className="md:col-span-12 lg:col-span-10 lg:col-start-2">
          <Label note="cm, measured on the garment">the sizes</Label>
          <div className="-mx-4 overflow-x-auto px-4">
            <table className="w-full min-w-[560px] text-[15px] tnum">
              <thead>
                <tr className="text-quiet"><th className="py-2 text-left font-normal" />{SIZE_ORDER.map((s) => <th key={s} className="py-2 text-right text-[clamp(18px,2vw,28px)] font-extrabold tracking-[-0.03em] text-ink">{s}</th>)}</tr>
              </thead>
              <tbody>
                {ROWS.map(([label, how, k]) => (
                  <tr key={k} className="border-t border-line align-baseline">
                    <td className="py-3 pr-4"><span className="block">{label}</span><span className="block text-[13px] text-quiet">{how}</span></td>
                    {SIZE_ORDER.map((s) => <td key={s} className="py-3 text-right text-[clamp(16px,1.6vw,22px)] font-semibold">{SIZES[s][k]}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <div className="mt-24 grid grid-cols-1 gap-x-4 gap-y-16 px-4 md:grid-cols-12">
        <section className="reveal md:col-span-6 lg:col-span-4 lg:col-start-2">
          <Label>to check yours</Label>
          <div className="prose-sb text-[15px]">
            <p>lay a tee you love flat, smooth it out, and measure it the same way: armpit to armpit across the front (double it for all round), and from the top of the shoulder by the collar straight down to the hem.</p>
            <p>pick the size whose numbers are closest. if you&apos;re between two, the bigger one gives the loose, straight fall it&apos;s cut for.</p>
          </div>
        </section>
        <section className="reveal md:col-span-6 lg:col-span-4 lg:col-start-7">
          <Label>how it wears</Label>
          <div className="prose-sb text-[15px]">
            <p>in the studio renders and the 3d, he is 175 cm and wears an M; she is 163 cm and wears an S.</p>
            <p>on any shirt page, open fit and give your height and weight: the tee is shown sewn onto the nearest of five simulated indian bodies in your size, standing, with hands up at the show and sitting, with where the hem and sleeves land.</p>
            <p><Link href={shirtHref(CURRENT.hero)}>try it on a shirt →</Link></p>
          </div>
        </section>
      </div>

      <section className="reveal mt-24 grid grid-cols-1 gap-x-4 px-4 md:grid-cols-12">
        <div className="md:col-span-6 lg:col-span-4 lg:col-start-2">
          <Label>the cloth</Label>
          <dl className="space-y-2 text-[14px]">
            {THE_TEE.cloth.map(([k, v]) => <div key={k} className="grid grid-cols-[6rem_1fr] gap-3"><dt className="text-quiet">{k}</dt><dd>{v}</dd></div>)}
          </dl>
        </div>
      </section>
    </div>
  );
}
