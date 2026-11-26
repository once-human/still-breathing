import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { OPERATOR } from "@/content/policies";
import { SHOP } from "@/content/shop";
import { sessionEmail } from "@/lib/shop/account";
import { shopOpen } from "@/lib/shop/config";
import { rupees } from "@/lib/shop/money";
import { orderFor, view } from "@/lib/shop/orders";
import { dayYear, when } from "@/lib/shop/words";
import { Print } from "./Print";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "receipt", robots: { index: false, follow: false }, referrer: "no-referrer" };

/**
 * A receipt for the payment, to print or save as PDF. Not a GST tax invoice: sahn is run by a person who isn't
 * GST-registered, so it says so rather than look like one. It speaks as the brand: no person's name or city (Onkar).
 */
export default async function Receipt({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ k?: string | string[] }> }) {
  if (!shopOpen()) notFound();
  const [{ id }, { k }] = await Promise.all([params, searchParams]);
  const found = await orderFor(id, typeof k === "string" ? k : null, await sessionEmail().catch(() => null)).catch(() => null);
  if (!found || found.o.stage === "paying") notFound();
  const o = found.o, v = view(o, true);
  return (
    <div className="mx-auto max-w-[720px] px-4 pt-6 pb-24 text-[14px] print:p-0">
      <div className="flex items-baseline justify-between border-t border-line pt-1.5 text-[13px] text-quiet"><span>receipt</span><Print /></div>
      <h1 className="mt-5 text-[40px] leading-none font-extrabold tracking-[-0.04em]">{SHOP.merchant}</h1>
      <p className="mt-2 text-quiet">{["an independent label from india", OPERATOR.email].filter(Boolean).join(" · ")}</p>

      <div className="mt-8 grid grid-cols-2 gap-4">
        <div>
          <p className="text-quiet">order</p>
          <p className="tnum font-semibold">#{v.id}</p>
          <p className="mt-2 text-quiet">placed</p>
          <p>{dayYear(v.placed)}</p>
        </div>
        <div>
          <p className="text-quiet">to</p>
          <p>{o.ship.name}<br />{found.full ? <>{[o.ship.address1, o.ship.address2].filter(Boolean).join(", ")}<br /></> : null}{o.ship.city}, {o.ship.state} {o.ship.pin}</p>
        </div>
      </div>

      <table className="mt-8 w-full border-collapse">
        <thead><tr className="border-b border-line text-left text-quiet"><th className="py-2 font-normal">shirt</th><th className="py-2 font-normal">size</th><th className="py-2 text-right font-normal">qty</th><th className="py-2 text-right font-normal">each</th><th className="py-2 text-right font-normal">amount</th></tr></thead>
        <tbody>
          {v.lines.map((l, i) => (
            <tr key={i} className="border-b border-line"><td className="py-2">{l.name}</td><td>{l.size}</td><td className="text-right tnum">{l.quantity}</td><td className="text-right tnum">{rupees(l.unitPrice)}</td><td className="text-right tnum">{rupees(l.unitPrice * l.quantity)}</td></tr>
          ))}
          <tr className="border-b border-line"><td className="py-2" colSpan={4}>shipping</td><td className="text-right tnum">{rupees(0)}</td></tr>
        </tbody>
        <tfoot><tr><td className="py-3 font-semibold" colSpan={4}>total paid</td><td className="text-right font-semibold tnum">{rupees(v.total)}</td></tr></tfoot>
      </table>

      <p className="mt-2 text-quiet">{v.payment?.at ? `paid ${when(v.payment.at)}${v.payment.label ? ` by ${v.payment.label}` : ""}${v.payment.id ? `, payment ${v.payment.id}` : ""}, through Razorpay.` : ""}</p>
      {v.refund && <p className="mt-1 text-quiet">refunded {rupees(v.refund.amount)}{v.refund.status === "processed" ? ` on ${dayYear(v.refund.doneAt ?? v.refund.at)}` : " (on its way)"}, refund {v.refund.id}. order cancelled.</p>}
      <p className="mt-8 text-[12px] text-quiet">all taxes and shipping included. this is a receipt for your payment, not a GST tax invoice.</p>
    </div>
  );
}
