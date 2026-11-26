import type { Metadata } from "next";
import { headers } from "next/headers";
import Link from "next/link";
import { notFound } from "next/navigation";
import { OPERATOR, POLICIES_READY } from "@/content/policies";
import { SHOP } from "@/content/shop";
import { shopOpen } from "@/lib/shop/config";
import { clientIp, limited } from "@/lib/shop/guard";
import { rupees } from "@/lib/shop/money";
import { advance, keyMatches, loadOrder, sync, validId, view, type Order, type OrderView, type Stage } from "@/lib/shop/orders";

export const dynamic = "force-dynamic";

/** the address carries the order's key: never indexed, never passed on in a Referer */
export const metadata: Metadata = { title: "your order", robots: { index: false, follow: false }, referrer: "no-referrer" };

const STEPS: { stage: Stage[]; label: string }[] = [
  { stage: ["paid"], label: "in" },
  { stage: ["printing"], label: "being made" },
  { stage: ["shipped", "out"], label: "on its way" },
  { stage: ["delivered"], label: "with you" },
];

const day = (iso: string) => new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).toLowerCase();

function headline(o: OrderView): [string, string] {
  const [m0, m1] = SHOP.make, [r0, r1] = SHOP.road;
  const fresh = Date.now() - Date.parse(o.placed) < 12 * 3600_000;
  switch (o.stage) {
    case "paying": return ["waiting on the payment.", "your bank hasn't confirmed it yet; it usually takes a minute. this page shows it the moment it does. if it doesn't go through, nothing is taken."];
    case "paid":
    case "printing":
      return fresh
        ? ["it's in. thank you.", `your shirt is made for you from here: ${m0}–${m1} days to make, then ${r0}–${r1} on the road to ${o.city.toLowerCase()}. the confirmation is in your email, and the tracking follows the moment it leaves.`]
        : ["being made.", `printed for you, checked and packed: ${m0}–${m1} days from your order. the tracking comes by email when it leaves.`];
    case "shipped": return ["on its way.", "it's with the courier. follow it with the tracking below."];
    case "out": return ["out for delivery.", "keep your phone on: the courier calls before coming."];
    case "delivered": return ["with you.", "if anything is wrong with it, write to us within 7 days with an unboxing video and photos, and we'll put it right."];
    case "attention": return ["we're on it.", "something held your order up on the way. we've been told and will write to you; nothing more is needed from you."];
  }
}

export default async function OrderPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ k?: string | string[] }> }) {
  if (!shopOpen()) notFound();
  const [{ id }, { k }] = await Promise.all([params, searchParams]);
  const key = typeof k === "string" && k.length <= 64 ? k : null;
  if (!validId(id) || !key || !keyMatches(id, key)) notFound();

  let o: Order | null = null, error = false;
  try {
    const ip = clientIp(await headers()) ?? "?";
    o = await loadOrder(id);
    // a look at the page moves the order on too (rate-limited): a payment confirmed late, a parcel that's left
    if (o && !(await limited(`order:${ip}`, 20, 60_000))) {
      if (o.stage === "paying" || (o.stage === "paid" && !o.partnerId)) o = await advance(id);
      else if (o.partnerId && o.stage !== "delivered" && (!o.syncedAt || Date.now() - Date.parse(o.syncedAt) > 15 * 60_000)) o = await sync(id).catch(() => o);
    }
  } catch (e) {
    console.error("order page:", e instanceof Error ? e.message : e);
    error = true;
  }
  if (!o) {
    if (!error) notFound();
    return (
      <div className="px-4 pt-6 pb-24">
        <h1 className="bigword text-[20vw] md:text-[13vw]">your order</h1>
        <p className="mt-6 max-w-[44ch] text-[clamp(18px,1.8vw,24px)] leading-[1.25] text-ink/85">couldn&apos;t load it just now. reload in a minute.</p>
      </div>
    );
  }

  const v = view(o);
  const [title, sub] = headline(v);
  const at = STEPS.findIndex((s) => s.stage.includes(v.stage));
  return (
    <div className="grid grid-cols-1 gap-x-4 px-4 pt-6 pb-24 md:grid-cols-12">
      <div className="md:col-span-7">
        <p className="page-in border-t border-line pt-1.5 text-[13px] text-quiet tnum">order #{v.id} · placed {day(v.placed)}</p>
        <h1 className="page-in mt-5 text-[46px] leading-[0.9] font-extrabold tracking-[-0.045em] lg:text-[72px]">{title}</h1>
        <p className="page-in-2 mt-5 max-w-[46ch] text-[clamp(17px,1.6vw,22px)] leading-[1.3] text-ink/85">{sub}</p>

        {at >= 0 && (
          <ol className="page-in-2 mt-10 grid grid-cols-4 gap-1.5 text-[13px]" aria-label="Where your order is">
            {STEPS.map((s, i) => (
              <li key={s.label} aria-current={i === at ? "step" : undefined} className={`border-t-2 pt-1.5 ${i <= at ? "border-blue text-ink" : "border-line text-quiet"}`}>{s.label}</li>
            ))}
          </ol>
        )}

        {v.tracking && (
          <div className="page-in-3 mt-10 border-t border-line pt-1.5 text-[14px]">
            <p className="text-quiet">tracking{v.shippedAt ? ` · sent ${day(v.shippedAt)}` : ""}{v.deliveredAt ? ` · delivered ${day(v.deliveredAt)}` : ""}</p>
            <p className="mt-2">
              {v.tracking.courier ? <span className="text-quiet">{v.tracking.courier.toLowerCase()} </span> : null}
              {v.tracking.url ? <a href={v.tracking.url} target="_blank" rel="noreferrer noopener" className="draw tnum">{v.tracking.awb ?? "track it"} ↗</a> : <span className="tnum">{v.tracking.awb}</span>}
            </p>
          </div>
        )}
      </div>

      <div className="mt-12 md:col-span-4 md:col-start-9 md:mt-0">
        <div className="border-t border-line pt-1.5 text-[14px]">
          <p className="text-quiet">in it</p>
          <ul className="mt-2">
            {v.lines.map((l, i) => (
              <li key={i} className="flex justify-between border-b border-line py-2"><span>{l.name}<span className="text-quiet"> · {l.size}</span></span><span className="tnum">× {l.quantity}</span></li>
            ))}
          </ul>
          <p className="mt-3 flex justify-between"><span>{v.stage === "paying" ? "to pay" : "paid"}</span><span className="tnum font-semibold">{rupees(v.total)}</span></p>
          <p className="mt-6 text-[13px] text-quiet">
            something not right?{POLICIES_READY ? <> <Link href="/policies/refunds" className="draw hover:text-ink">returns</Link> ·</> : null}
            {OPERATOR.email ? <> write to <a href={`mailto:${OPERATOR.email}?subject=${encodeURIComponent(`order #${v.id}`)}`} className="draw hover:text-ink">{OPERATOR.email}</a></> : " reply to your order email"} with order #{v.id}.
          </p>
        </div>
      </div>
    </div>
  );
}
