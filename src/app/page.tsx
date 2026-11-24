import { Nav } from "@/components/Nav";
import { Product } from "@/components/Product";
import { BigWord } from "@/components/BigWord";
import { Label } from "@/components/Label";
import { Now } from "@/components/Now";
import { SIZES, SIZE_ORDER, SHOWS, THE_TEE } from "@/content/tee";
import pkg from "../../package.json";

const ROWS: [string, "chest_round" | "length" | "shoulder"][] = [["chest, all round", "chest_round"], ["length, shoulder to hem", "length"], ["shoulder, seam to seam", "shoulder"]];

export default function Home() {
  return (
    <>
      <Nav />
      <main id="top" className="pt-20">
        <Product />

        <div className="mt-24"><Now /></div>

        <BigWord word="still breathing" marquee className="mt-28 text-[22vw] md:text-[16vw]" />

        <div className="mt-20 grid grid-cols-1 gap-x-4 px-4 md:grid-cols-12">
          <section className="md:col-span-7 lg:col-span-6 lg:col-start-2">
            <Label id="sizes" note="cm, on the garment">sizes</Label>
            <table className="w-full text-[14px] tnum">
              <thead>
                <tr className="text-quiet"><th className="py-1 text-left font-normal" />{SIZE_ORDER.map((s) => <th key={s} className="py-1 text-right font-normal">{s}</th>)}</tr>
              </thead>
              <tbody>
                {ROWS.map(([label, k]) => (
                  <tr key={k} className="border-t border-line">
                    <td className="py-2 text-quiet">{label}</td>
                    {SIZE_ORDER.map((s) => <td key={s} className="py-2 text-right">{SIZES[s][k]}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-4 max-w-[52ch] text-[13px] text-quiet">
              to check, lay a tee you love flat and measure it the same way: armpit to armpit (double it for all round), and from the top of the shoulder by the collar down to the hem.
            </p>
          </section>

          <section className="mt-20 md:col-span-5 md:mt-0 lg:col-span-4 lg:col-start-9">
            <Label id="cloth">cloth</Label>
            <dl className="space-y-2 text-[14px]">
              {THE_TEE.cloth.map(([k, v]) => (
                <div key={k} className="grid grid-cols-[6.5rem_1fr] gap-3"><dt className="text-quiet">{k}</dt><dd>{v}</dd></div>
              ))}
            </dl>
            <Label id="care" className="mt-16">care</Label>
            <ul className="space-y-1 text-[14px]">{THE_TEE.care.map((c) => <li key={c}>{c}</li>)}</ul>
          </section>
        </div>

        <div className="mt-24 grid grid-cols-1 gap-x-4 px-4 md:grid-cols-12">
          <section className="md:col-span-7 lg:col-span-6 lg:col-start-2">
            <Label id="shows" note="lineup 01">the india shows</Label>
            <ul className="text-[clamp(28px,5vw,64px)] leading-[1] font-extrabold tracking-[-0.04em]">
              {SHOWS.map((s) => (
                <li key={s.city} className="flex items-baseline justify-between border-t border-line py-2">
                  <span>{s.city}</span>
                  <span className="text-[0.45em] font-normal tracking-normal text-quiet tnum">{s.days.map((d) => d.slice(8, 10)).join(" + ")}.12</span>
                </li>
              ))}
            </ul>
          </section>
          <section className="mt-16 md:col-span-5 md:mt-0 lg:col-span-4 lg:col-start-9">
            <Label>about this tee</Label>
            <p className="max-w-[40ch] text-[14px] text-ink/85">
              still breathing makes one shirt per moment. lineup 01 is for the december shows in india: two shirts, the crowd in black and the map in off white, each made to order and sent anywhere in india.
            </p>
          </section>
        </div>
      </main>

      <footer className="mt-32 grid grid-cols-2 gap-3 px-4 pb-4 text-[13px] md:grid-cols-4">
        <span className="border-t border-line pt-1.5">still breathing, lineup 01</span>
        <span className="border-t border-line pt-1.5 text-quiet">made to order</span>
        <span className="hidden border-t border-line pt-1.5 text-quiet md:block">made in india</span>
        <span className="hidden border-t border-line pt-1.5 text-right text-quiet md:block">v{pkg.version}</span>
      </footer>
    </>
  );
}
