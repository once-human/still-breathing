import type { Metadata } from "next";
import Link from "next/link";
import { Label } from "@/components/Label";
import { THE_TEE } from "@/content/tee";
import { CURRENT } from "@/content/lineups";
import { POLICY_LINKS, pageMeta } from "@/lib/site";

export const metadata: Metadata = pageMeta({
  title: "help",
  description: "Help with a still breathing order: made to order, shipping anywhere in India, returns and refunds, sizes, care and how to reach us.",
  path: "/help",
});

type Part = { id: string; title: string; body: React.ReactNode };

const PARTS: Part[] = [
  {
    id: "orders", title: "orders",
    body: (
      <>
        <p>every shirt is made to order: nothing sits in a warehouse. yours is made once you&apos;ve paid, in the size you picked, then packed and sent.</p>
        <p>once it&apos;s on its way you get the tracking with your order.</p>
      </>
    ),
  },
  {
    id: "shipping", title: "shipping",
    body: (
      <>
        <p>we send anywhere in india. how long making and delivery take, and what it costs, is on the <Link href="/policies/shipping">shipping policy</Link>.</p>
        <p>if you want it for a show, order early: lineup {CURRENT.no}&apos;s nights start on 5 december.</p>
      </>
    ),
  },
  {
    id: "returns", title: "returns and refunds",
    body: (
      <>
        <p>because each shirt is made for you, what can be returned or swapped, and how a refund works, is set out in <Link href="/policies/refunds">returns and refunds</Link>.</p>
        <p>if your shirt arrives damaged or misprinted, tell us with a photo and we&apos;ll put it right.</p>
      </>
    ),
  },
  {
    id: "sizes", title: "sizes",
    body: <p>one oversized cut, xs to 2xl, every number in cm on the garment: see the <Link href="/size-guide">size guide</Link>, or open fit on any shirt to see it on a body like yours.</p>,
  },
  {
    id: "care", title: "care",
    body: <ul>{THE_TEE.care.map((c) => <li key={c}>{c}</li>)}</ul>,
  },
  {
    id: "contact", title: "contact",
    body: <p>a question about a shirt or an order: the address to write to goes up here when orders open, and it will be on your order too.</p>,
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
        <section className="grid grid-cols-1 gap-x-4 md:grid-cols-12">
          <div className="md:col-span-8 lg:col-span-6 lg:col-start-2">
            <Label>the small print</Label>
            <ul className="grid grid-cols-2 gap-x-4 gap-y-1 text-[15px]">
              {POLICY_LINKS.map((l) => <li key={l.href}><Link href={l.href} className="draw hover:text-blue">{l.label} →</Link></li>)}
            </ul>
          </div>
        </section>
      </div>
    </div>
  );
}
