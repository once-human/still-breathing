import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Label } from "@/components/Label";
import { ShirtCard } from "@/components/ShirtCard";
import { COLOURS, DESIGNS, SIZES, SIZE_ORDER, THE_TEE } from "@/content/tee";
import { LINEUPS, lineupOf, paperStill, shirtBySlug, shirtsOf, shirtTitle, wornStill, STILL_H, STILL_W } from "@/content/lineups";
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
    description: `${t.top}, ${t.name}: a ${COLOURS[s.colour].name} tee from lineup ${l.no}, ${l.title} (${l.tag}). On the back, ${s.back}. Heavy 240 gsm cotton, cut loose, made to order and sent anywhere in India.`,
    path: `/${l.slug}/${s.slug}`,
    image: s.slug,
  });
}

const ROWS: [string, "chest_round" | "length" | "shoulder"][] = [["chest, all round", "chest_round"], ["length", "length"], ["shoulder", "shoulder"]];

export default async function ShirtPage({ params }: Params) {
  const f = await find(params);
  if (!f) notFound();
  const { l, d } = f, s = DESIGNS[d], t = shirtTitle(d);
  const worn = [
    { src: wornStill(d, 0), alt: `${t.top} ${t.name}, worn at the show, from the front` },
    { src: wornStill(d, 180), alt: `${t.top} ${t.name}, worn at the show, from behind` },
    { src: wornStill(d, 0, "her"), alt: `${t.top} ${t.name}, worn by her at the show, from the front` },
    { src: wornStill(d, 180, "her"), alt: `${t.top} ${t.name}, worn by her at the show, from behind` },
  ];

  return (
    <div className="page-in-3">
      {/* both sides of the shirt, each with what's on it */}
      <div className="mt-32 grid grid-cols-1 gap-x-4 gap-y-20 px-4 md:grid-cols-12">
        {([["the front", "front", s.front], ["the back", "back", s.back]] as const).map(([label, v, words], i) => (
          <section key={v} className={`reveal md:col-span-6 ${i ? "lg:col-span-5 lg:col-start-8" : "lg:col-span-5 lg:col-start-2"}`}>
            <Label note={v === "front" ? "left chest" : "across the back"}>{label}</Label>
            <img src={paperStill(d, v)} alt={`${t.top} ${t.name}, ${label}, on the studio paper`} width={STILL_W} height={STILL_H} loading="lazy" decoding="async" className="aspect-[880/1120] w-full bg-studio object-cover" />
            <p className="mt-4 max-w-[46ch] text-[15px] text-ink/85">{words}.</p>
          </section>
        ))}
      </div>

      {/* worn at the show, him and her */}
      <section className="mt-32 px-4">
        <div className="grid grid-cols-1 md:grid-cols-12"><div className="md:col-span-12 lg:col-span-10 lg:col-start-2"><Label note="studio renders, the same tee as the 3D">at the show</Label></div></div>
        <ul className="-mx-4 flex snap-x snap-mandatory gap-2 overflow-x-auto px-4 pb-2 [scrollbar-width:none] md:mx-0 md:grid md:grid-cols-4 md:gap-4 md:overflow-visible md:px-0 lg:mx-[calc((100%-11rem)/12+1rem)]">
          {worn.map((w) => (
            <li key={w.src} className="reveal w-[72vw] shrink-0 snap-start md:w-auto">
              <img src={w.src} alt={w.alt} width={STILL_W} height={STILL_H} loading="lazy" decoding="async" className="aspect-[880/1120] w-full bg-[#0b0a0a] object-cover" />
            </li>
          ))}
        </ul>
      </section>

      {/* the cloth, the care and the sizes */}
      <div className="mt-32 grid grid-cols-1 gap-x-4 gap-y-16 px-4 md:grid-cols-12">
        <section className="reveal md:col-span-6 lg:col-span-4 lg:col-start-2">
          <Label>cloth</Label>
          <dl className="space-y-2 text-[14px]">
            {THE_TEE.cloth.map(([k, v]) => <div key={k} className="grid grid-cols-[6rem_1fr] gap-3"><dt className="text-quiet">{k}</dt><dd>{v}</dd></div>)}
          </dl>
        </section>
        <section className="reveal md:col-span-6 lg:col-span-3">
          <Label>care</Label>
          <ul className="space-y-1 text-[14px]">{THE_TEE.care.map((c) => <li key={c}>{c}</li>)}</ul>
        </section>
        <section className="reveal md:col-span-12 lg:col-span-3">
          <Label note={<Link href="/size-guide" className="draw hover:text-ink">size guide</Link>}>sizes</Label>
          <table className="w-full text-[13px] tnum">
            <thead><tr className="text-quiet"><th className="py-1 text-left font-normal">cm</th>{SIZE_ORDER.map((x) => <th key={x} className="py-1 text-right font-normal">{x}</th>)}</tr></thead>
            <tbody>
              {ROWS.map(([label, k]) => (
                <tr key={k} className="border-t border-line"><td className="py-1.5 text-quiet">{label}</td>{SIZE_ORDER.map((x) => <td key={x} className="py-1.5 text-right">{SIZES[x][k]}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      {/* the rest of the lineup */}
      <section className="mt-36 px-4">
        <div className="grid grid-cols-1 md:grid-cols-12"><div className="md:col-span-12 lg:col-span-10 lg:col-start-2">
          <Label note={<Link href={`/${l.slug}`} className="draw hover:text-ink">the whole lineup</Link>}>more from lineup {l.no}</Label>
        </div></div>
        <ul className="grid grid-cols-2 gap-x-4 gap-y-10 md:grid-cols-4 lg:mx-[calc((100%-11rem)/12+1rem)]">
          {shirtsOf(l).filter((x) => x !== d).map((x) => <li key={x} className="reveal"><ShirtCard d={x} /></li>)}
        </ul>
      </section>
    </div>
  );
}
