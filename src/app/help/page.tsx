import type { Metadata } from "next";
import Link from "next/link";
import { Label } from "@/components/Label";
import { THE_TEE } from "@/content/tee";
import { CURRENT } from "@/content/lineups";
import { SHOP } from "@/content/shop";
import { box } from "@/content/mail";
import { OPERATOR, POLICIES_READY } from "@/content/policies";
import { priceLine } from "@/lib/live";
import { shopOpen } from "@/lib/shop/config";
import { POLICY_LINKS, pageMeta } from "@/lib/site";

export const metadata: Metadata = pageMeta({
  title: "help",
  description: `Help with a sahn order: made to order, sent anywhere in ${SHOP.shipsTo}, sizes and care.`,
  path: "/help",
});

type Part = { id: string; title: string; body: React.ReactNode };

const parts = (each: string): Part[] => [
  {
    id: "orders", title: "orders",
    body: (
      <>
        <p>every shirt is made to order: nothing sits in a warehouse. each is {each}, all taxes and shipping included. yours is made once you&apos;ve paid, in the size you picked, then packed and sent.</p>
        {shopOpen() ? <p>every order email links to your order&apos;s page, or <Link href="/order">find your order</Link> with its number and your email.</p> : null}
      </>
    ),
  },
  {
    id: "shipping", title: "shipping",
    body: <p>we send anywhere in {SHOP.where}. making takes {SHOP.make[0]} to {SHOP.make[1]} days, then {SHOP.road[0]} to {SHOP.road[1]} days on the road. if you want it for a show, order early: fred again.. india starts on 5 december.</p>,
  },
  {
    id: "sizes", title: "sizes",
    body: <p>one oversized cut, xs to 2xl, every number in cm on the garment: see the <Link href="/size-guide">size guide</Link>, or open fit on any shirt to see it on a body like yours.</p>,
  },
  {
    id: "care", title: "care",
    body: <ul>{THE_TEE.care.map((c) => <li key={c}>{c}</li>)}</ul>,
  },
  ...(POLICIES_READY ? [{
    id: "contact", title: "contact",
    body: (
      <>
        <p>write to <a href={`mailto:${OPERATOR.email}`}>{OPERATOR.email}</a>, or about an order to <a href={`mailto:${box("orders")}`}>{box("orders")}</a>{OPERATOR.phone ? <>, or call {OPERATOR.phone}</> : null}. every address, and a way to write straight to the top when nothing else has worked, on the <Link href="/contact">contact page</Link>.</p>
        <p>returns and refunds: <Link href="/policies/refunds">how they work</Link>.</p>
      </>
    ),
  }] : []),
];

export default async function Help() {
  const p = await priceLine(), PARTS = parts(p.one ? p.from : `${p.from}, depending on the shirt`);
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
