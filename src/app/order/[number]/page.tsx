import type { Metadata } from "next";
import { headers } from "next/headers";
import Link from "next/link";
import { SHOP } from "@/content/shop";
import { OPERATOR, POLICIES_READY } from "@/content/policies";
import { ordersOpen } from "@/lib/shop/config";
import { clientIp, limited } from "@/lib/shop/guard";
import { rupees } from "@/lib/shop/money";
import { orderNumber, orderView, type OrderView, type Stage } from "@/lib/shop/orders";

export const dynamic = "force-dynamic";

/** the page's address carries the order's key: never indexed, never sent on in a Referer */
export const metadata: Metadata = { title: "your order", robots: { index: false, follow: false }, referrer: "no-referrer" };

const STEPS: { stage: Stage[]; label: string }[] = [
  { stage: ["in"], label: "in" },
  { stage: ["making"], label: "being made" },
  { stage: ["road", "out", "trouble"], label: "on its way" },
  { stage: ["delivered"], label: "with you" },
];

const day = (iso: string) => new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).toLowerCase();

function headline(o: OrderView): [string, string] {
  const [m0, m1] = SHOP.make, [r0, r1] = SHOP.road;
  switch (o.stage) {
    case "paying": return ["waiting on the payment.", "your bank hasn't confirmed it yet. if it doesn't go through, nothing is charged and the order lapses on its own."];
    case "in": return ["it's in. thank you.", `your shirt is made for you from here: ${m0}–${m1} days to make, then ${r0}–${r1} on the road. we email you the tracking the moment it leaves.`];
    case "making": return ["being made.", `printed for you, checked and packed: ${m0}–${m1} days from your order. the tracking comes by email when it leaves.`];
    case "road": return ["on its way.", "it's with the courier. follow it with the tracking below."];
    case "out": return ["out for delivery today.", "keep your phone on: the courier calls before coming."];
    case "trouble": return ["the courier couldn't deliver it.", "they'll try again. if they can't reach you, write to us and we'll sort it out."];
    case "delivered": return ["with you.", "film the unboxing if you can: if anything is wrong with it, that's how we put it right. see returns."];
    case "cancelled": return ["cancelled.", "nothing will be made or sent."];
    case "refunded": return ["cancelled and refunded.", "the money goes back the way you paid; banks take 5–7 working days to show it."];
  }
}

export default async function OrderPage({ params, searchParams }: { params: Promise<{ number: string }>; searchParams: Promise<{ k?: string | string[] }> }) {
  const [{ number: raw }, { k }] = await Promise.all([params, searchParams]);
  const number = orderNumber(decodeURIComponent(raw));
  const key = typeof k === "string" && k.length <= 200 ? k : null;

  let o: OrderView | null = null, why = "this link doesn't open an order. find it with its number and your email.";
  if (!ordersOpen()) why = "order pages open with the shop.";
  else if (number && key) {
    const h = await headers();
    const ip = clientIp(h) ?? "?";
    if (limited(`order:${ip}`, 20, 60_000)) why = "too many tries. wait a minute and reload.";
    else {
      try {
        o = await orderView(number, key);
      } catch (e) {
        console.error("order page:", e instanceof Error ? e.message : e);
        why = "couldn't load your order just now. reload in a minute.";
      }
    }
  }

  if (!o) {
    return (
      <div className="px-4 pt-6 pb-24">
        <h1 className="bigword text-[20vw] md:text-[13vw]">your order</h1>
        <p className="mt-6 max-w-[44ch] text-[clamp(18px,1.8vw,24px)] leading-[1.25] text-ink/85">{why}</p>
        {ordersOpen() && <Link href="/order" className="draw mt-8 inline-block">find my order →</Link>}
      </div>
    );
  }

  const [title, sub] = headline(o);
  const at = STEPS.findIndex((s) => s.stage.includes(o.stage));
  return (
    <div className="grid grid-cols-1 gap-x-4 px-4 pt-6 pb-24 md:grid-cols-12">
      <div className="md:col-span-7">
        <p className="page-in border-t border-line pt-1.5 text-[13px] text-quiet tnum">order #{o.number} · placed {day(o.placed)}</p>
        <h1 className="page-in mt-5 text-[46px] leading-[0.9] font-extrabold tracking-[-0.045em] lg:text-[72px]">{title}</h1>
        <p className="page-in-2 mt-5 max-w-[46ch] text-[clamp(17px,1.6vw,22px)] leading-[1.3] text-ink/85">{sub}</p>

        {at >= 0 && (
          <ol className="page-in-2 mt-10 grid grid-cols-4 gap-1.5 text-[13px]" aria-label="Where your order is">
            {STEPS.map((s, i) => (
              <li key={s.label} aria-current={i === at ? "step" : undefined} className={`border-t-2 pt-1.5 ${i <= at ? "border-blue text-ink" : "border-line text-quiet"}`}>{s.label}</li>
            ))}
          </ol>
        )}

        {o.tracking.length > 0 && (
          <div className="page-in-3 mt-10 border-t border-line pt-1.5 text-[14px]">
            <p className="text-quiet">tracking{o.shippedAt ? ` · sent ${day(o.shippedAt)}` : ""}{o.expectedAt && o.stage !== "delivered" ? ` · expected ${day(o.expectedAt)}` : ""}{o.deliveredAt ? ` · delivered ${day(o.deliveredAt)}` : ""}</p>
            {o.tracking.map((t, i) => (
              <p key={i} className="mt-2">
                {t.company ? <span className="text-quiet">{t.company.toLowerCase()} </span> : null}
                {t.url ? <a href={t.url} target="_blank" rel="noreferrer noopener" className="draw tnum">{t.number ?? "track it"} ↗</a> : <span className="tnum">{t.number}</span>}
              </p>
            ))}
          </div>
        )}
      </div>

      <div className="mt-12 md:col-span-4 md:col-start-9 md:mt-0">
        <div className="border-t border-line pt-1.5 text-[14px]">
          <p className="text-quiet">in it</p>
          <ul className="mt-2">
            {o.lines.map((l, i) => (
              <li key={i} className="flex justify-between border-b border-line py-2"><span>{l.name}{l.size ? <span className="text-quiet"> · {l.size}</span> : null}</span><span className="tnum">× {l.quantity}</span></li>
            ))}
          </ul>
          <p className="mt-3 flex justify-between"><span>paid</span><span className="tnum font-semibold">{rupees(o.total)}</span></p>
          <p className="mt-6 text-[13px] text-quiet">
            something not right? <Link href={POLICIES_READY ? "/policies/refunds" : "/help"} className="draw hover:text-ink">returns</Link>{OPERATOR.email ? <> · write to <a href={`mailto:${OPERATOR.email}?subject=${encodeURIComponent(`order #${o.number}`)}`} className="draw hover:text-ink">{OPERATOR.email}</a></> : null} with order #{o.number}.
          </p>
        </div>
      </div>
    </div>
  );
}
