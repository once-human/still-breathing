import type { Metadata } from "next";
import Link from "next/link";
import { Label } from "@/components/Label";
import { THE_TEE } from "@/content/tee";
import { CURRENT } from "@/content/lineups";
import { POLICY_LINKS, pageMeta } from "@/lib/site";

export const metadata: Metadata = pageMeta({
  title: "help",
  description: "Help with a sahn order: made to order, sent anywhere in India, sizes and care.",
  path: "/help",
});

type Part = { id: string; title: string; body: React.ReactNode };

const PARTS: Part[] = [
  {
    id: "orders", title: "orders",
    body: <p>every shirt is made to order: nothing sits in a warehouse. yours is made once you&apos;ve paid, in the size you picked, then packed and sent.</p>,
  },
  {
    id: "shipping", title: "shipping",
    body: <p>we send anywhere in india. if you want it for a show, order early: lineup {CURRENT.no}&apos;s nights start on 5 december.</p>,
  },
  {
    id: "sizes", title: "sizes",
    body: <p>one oversized cut, xs to 2xl, every number in cm on the garment: see the <Link href="/size-guide">size guide</Link>, or open fit on any shirt to see it on a body like yours.</p>,
  },
  {
    id: "care", title: "care",
    body: <ul>{THE_TEE.care.map((c) => <li key={c}>{c}</li>)}</ul>,
  },
];

export default function Help() {
  return (
    <div className="pt-6">
      <div className="px-4">
        <h1 className="page-in bigword text-[26vw] md:text-[17vw]">help</h1>
        <nav aria-label="On this page" className="page-in-2 mt-8 flex flex-wrap gap-x-5 gap-y-1 text-[15px]">
          {PARTS.map((p) => <a key={p.id} href={`#${p.id}`} className="draw text-quiet hover:text-ink">{p.title}</a>)}
        </nav>
      </div>
      <div className="page-in-3 mt-20 space-y-16 px-4">
        {PARTS.map((p) => (
          <section key={p.id} className="grid grid-cols-1 gap-x-4 md:grid-cols-12">
            <div className="md:col-span-8 lg:col-span-6 lg:col-start-2">
              <Label id={p.id}>{p.title}</Label>
              <div className="prose-sb text-[15px] leading-relaxed">{p.body}</div>
            </div>
          </section>
        ))}
        {POLICY_LINKS.length ? <section className="grid grid-cols-1 gap-x-4 md:grid-cols-12">
          <div className="md:col-span-8 lg:col-span-6 lg:col-start-2">
            <Label>the small print</Label>
            <ul className="grid grid-cols-2 gap-x-4 gap-y-1 text-[15px]">
              {POLICY_LINKS.map((l) => <li key={l.href}><Link href={l.href} className="draw hover:text-blue">{l.label} →</Link></li>)}
            </ul>
          </div>
        </section> : null}
      </div>
    </div>
  );
}
