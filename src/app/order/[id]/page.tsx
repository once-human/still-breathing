import { box } from "@/content/mail";
import type { Metadata } from "next";
import { headers } from "next/headers";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Reorder } from "@/components/shop/Reorder";
import { POLICIES_READY } from "@/content/policies";
import { SHOP } from "@/content/shop";
import { sessionEmail } from "@/lib/shop/account";
import { accountsOpen, shopOpen } from "@/lib/shop/config";
import { clientIp, limited } from "@/lib/shop/guard";
import { rupees } from "@/lib/shop/money";
import { advance, orderFor, sync, syncRefund, view, type Order, type OrderView, type Stage } from "@/lib/shop/orders";
import { EVENT_WORD, day, time, when } from "@/lib/shop/words";
import { OrderActions } from "./OrderActions";

export const dynamic = "force-dynamic";

/** the address can carry the order's key: never indexed, never passed on in a Referer */
export const metadata: Metadata = { title: "your order", robots: { index: false, follow: false }, referrer: "no-referrer" };

const STEPS: { stage: Stage[]; label: string }[] = [
  { stage: ["paid"], label: "in" },
  { stage: ["printing"], label: "being made" },
  { stage: ["shipped", "out"], label: "on its way" },
  { stage: ["delivered"], label: "with you" },
];

function headline(o: OrderView): [string, string] {
  const [m0, m1] = SHOP.make, [r0, r1] = SHOP.road;
  switch (o.stage) {
    case "paying": return ["waiting on the payment.", "your bank hasn't confirmed it yet; it usually takes a minute. this page shows it the moment it does. if it doesn't go through, nothing is taken."];
    case "paid":
      return ["it's in. thank you.", `it goes to print after ${o.changeUntil ? time(o.changeUntil) : "an hour"}: until then you can still cancel it or fix the address, below. then ${m0}–${m1} days to make and ${r0}–${r1} on the road to ${o.city.toLowerCase()}.`];
    case "printing": return ["being made.", `printed for you, checked and packed: ${m0}–${m1} days from your order. the tracking comes by email the moment it leaves.`];
    case "shipped": return ["on its way.", "it's with the courier. follow it with the tracking below."];
    case "out": return ["out for delivery.", "keep your phone on: the courier calls before coming."];
    case "delivered": return ["with you.", "if anything is wrong with it, write to us within 7 days with an unboxing video and photos, and we'll put it right."];
    case "attention": return ["we're on it.", "something held your order up on the way. we've been told and will write to you; nothing more is needed from you."];
    case "cancelled": {
      const r = o.refunds.filter((x) => x.status !== "failed");
      const failed = o.refunds.some((x) => x.status === "failed") && !r.length;
      return ["cancelled.", failed ? "nothing will be made or sent. the refund needs a hand from us: we've been told and will write to you."
        : !r.length ? "nothing will be made or sent. we'll write to you about your payment."
        : r.every((x) => x.status === "processed") ? `nothing will be made or sent. ${rupees(o.refunded)} has been refunded; banks usually show it within 5–7 working days, often sooner for UPI.`
        : `nothing will be made or sent. your ${rupees(o.refunded)} refund is on its way back; banks usually show it within 5–7 working days.`];
    }
  }
}

export default async function OrderPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ k?: string | string[] }> }) {
  if (!shopOpen()) notFound();
  const [{ id }, { k }] = await Promise.all([params, searchParams]);
  const key = typeof k === "string" ? k : null;

  let found: { o: Order; full: boolean } | null = null, error = false;
  try {
    found = await orderFor(id, key, await sessionEmail().catch(() => null));
    // a look at the page moves the order on too (rate-limited): a payment confirmed late, the hour over, a parcel that's left
    const ip = clientIp(await headers()) ?? "?";
    if (found && !(await limited(`order:${ip}`, 20, 60_000))) {
      const o = found.o;
      let n: Order | null = o;
      if (o.stage === "paying" || (o.stage === "paid" && !o.partnerId)) n = await advance(id);
      else if (o.refunds?.some((r) => r.status === "pending")) n = await syncRefund(id).catch(() => o);
      else if (o.partnerId && o.stage !== "delivered" && (!o.syncedAt || Date.now() - Date.parse(o.syncedAt) > 15 * 60_000)) n = await sync(id).catch(() => o);
      if (n) found = { ...found, o: n };
    }
  } catch (e) {
    console.error("order page:", e instanceof Error ? e.message : e);
    error = true;
  }
  if (!found) {
    if (!error) notFound();
    return (
      <div className="px-4 pt-6 pb-24">
        <h1 className="bigword text-[20vw] md:text-[13vw]">your order</h1>
        <p className="mt-6 max-w-[44ch] text-[clamp(18px,1.8vw,24px)] leading-[1.25] text-ink/85">couldn&apos;t load it just now. reload in a minute.</p>
      </div>
    );
  }

  const v = view(found.o, found.full);
  const [title, sub] = headline(v);
  const at = STEPS.findIndex((s) => s.stage.includes(v.stage));
  const q = key ? `?k=${encodeURIComponent(key)}` : "";
  const events = [...v.events].reverse();

  return (
    <div className="grid grid-cols-1 gap-x-4 px-4 pt-6 pb-24 md:grid-cols-12">
      <div className="md:col-span-7">
        <p className="page-in flex justify-between border-t border-line pt-1.5 text-[13px] text-quiet tnum">
          <span>order #{v.id} · placed {day(v.placed)}</span>
          {found.full ? <Link href="/profile" className="draw hover:text-ink">all your orders</Link> : accountsOpen() ? <Link href="/profile" className="draw hover:text-ink">sign in</Link> : null}
        </p>
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

        {v.changeUntil && v.ship && <div className="page-in-3 mt-10"><OrderActions id={v.id} k={key} until={v.changeUntil} total={v.total} ship={v.ship} /></div>}

        <section className="page-in-3 mt-10 border-t border-line pt-1.5 text-[14px]" aria-labelledby="what-happened">
          <h2 id="what-happened" className="text-quiet">everything so far</h2>
          <ol className="mt-2">
            {events.map((e, i) => (
              <li key={i} className="grid grid-cols-[7.5rem_1fr] gap-3 border-b border-line py-2">
                <time dateTime={e.at} className="text-quiet tnum">{when(e.at)}</time>
                <span>{EVENT_WORD[e.kind]}{e.note ? <span className="text-quiet"> · {e.kind === "partner" ? e.note.toLowerCase() : e.note}</span> : null}</span>
              </li>
            ))}
          </ol>
          {v.stage !== "paying" && v.stage !== "cancelled" && v.stage !== "delivered" && <p className="mt-2 text-[12px] text-quiet">checked with the workshop and courier every few hours, and whenever this page is opened.</p>}
        </section>
      </div>

      <div className="mt-12 md:col-span-4 md:col-start-9 md:mt-0">
        <div className="border-t border-line pt-1.5 text-[14px]">
          <p className="text-quiet">in it</p>
          <ul className="mt-2">
            {v.lines.map((l, i) => (
              <li key={i} className="flex justify-between gap-3 border-b border-line py-2"><span>{l.name}<span className="text-quiet"> · {l.size} × {l.quantity}</span></span><span className="tnum">{rupees(l.unitPrice * l.quantity)}</span></li>
            ))}
          </ul>
          <p className="mt-3 flex justify-between"><span>{v.stage === "paying" ? "to pay" : "paid"}</span><span className="tnum font-semibold">{rupees(v.total)}</span></p>
          {v.payment?.at && <p className="mt-1 text-[13px] text-quiet">{v.payment.label ? `by ${v.payment.label}, ` : ""}{when(v.payment.at)}{v.payment.id ? <> · <span className="tnum">{v.payment.id}</span></> : null}</p>}
          {v.refunds.map((r) => <p key={r.id} className="mt-1 text-[13px] text-quiet">refund {rupees(r.amount)}{r.reason && r.reason !== "cancelled" ? ` (${r.reason})` : ""}: {r.status === "processed" ? `sent ${when(r.doneAt ?? r.at)}` : r.status === "failed" ? "needs a hand from us" : "on its way"} · <span className="tnum">{r.id}</span></p>)}
          <p className="mt-1 text-[12px] text-quiet">all taxes and shipping included.</p>

          {v.ship && !v.changeUntil && (
            <div className="mt-6">
              <p className="text-quiet">going to</p>
              <p className="mt-1">{v.ship.name}<br />{[v.ship.address1, v.ship.address2].filter(Boolean).join(", ")}<br />{v.ship.city}, {v.ship.state} {v.ship.pin}</p>
            </div>
          )}
          {!v.ship && <p className="mt-6 text-[13px] text-quiet">going to {v.city.toLowerCase()}.</p>}

          <div className="mt-6 flex flex-wrap gap-x-4 text-[13px] text-quiet">
            {v.stage !== "paying" && <Link href={`/order/${v.id}/receipt${q}`} className="hit hover:text-ink">receipt</Link>}
            <Reorder lines={v.lines} />
          </div>
          <p className="mt-6 text-[13px] text-quiet">
            something not right?{POLICIES_READY ? <> <Link href="/policies/refunds" className="draw hover:text-ink">returns</Link> ·</> : null}
            <> write to <a href={`mailto:${box("orders")}?subject=${encodeURIComponent(`order #${v.id}`)}`} className="draw hover:text-ink">{box("orders")}</a></> with order #{v.id}.
          </p>
        </div>
      </div>
    </div>
  );
}
