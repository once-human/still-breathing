import { notFound } from "next/navigation";
import { requireAdmin } from "@/lib/admin/auth";
import { costs, knownFees, marginOf, shirtName } from "@/lib/admin/data";
import { auditFor } from "@/lib/admin/log";
import { getSettings } from "@/lib/admin/settings";
import { partnerKeys, razorpayKeys } from "@/lib/shop/config";
import { HOLD_MS, MAIL_KINDS, changeable, emailsSent, loadOrder, orderPath, refunded, validId } from "@/lib/shop/orders";
import { products } from "@/lib/shop/products";
import { EVENT_WORD } from "@/lib/shop/words";
import { Act, NoteForm } from "../../../ui/client";
import { A, KV, PageHead, Pill, Section, StageBadge, Table, dt, inr } from "../../../ui/ui";

export const metadata = { title: "order" };

/** Postgres's text time ("2026-11-26 14:00:00.1+00") as ISO */
const pgTime = (t: string) => {
  const d = new Date(t.replace(" ", "T").replace(/([+-]\d\d)$/, "$1:00"));
  return Number.isNaN(d.getTime()) ? new Date(0).toISOString() : d.toISOString();
};

type Row = { at: string; what: string; note?: string; by: "shop" | "admin" | "note" };

export default async function OrderPage({ params }: { params: Promise<{ id: string }> }) {
  await requireAdmin();
  const { id } = await params;
  if (!validId(id)) notFound();
  const o = await loadOrder(id);
  if (!o) notFound();
  const [sent, log, fees, s, c, list] = await Promise.all([emailsSent(id), auditFor(id), knownFees(), getSettings(), costs(), products()]);
  const mails = Object.entries(sent).map(([kind, at]) => ({ kind, at: pgTime(at) })).sort((a, b) => a.at.localeCompare(b.at));
  const skuOf = (d: string, size: string) => (list.find((p) => p.id === d)?.skus as Record<string, string | undefined> | undefined)?.[size];
  const fee = fees.get(id);
  const m = marginOf(o, s, c, fee);
  const dash = razorpayKeys()?.test ? "https://dashboard.razorpay.com/app/test" : "https://dashboard.razorpay.com/app";

  const timeline: Row[] = [
    ...(o.events ?? []).map((e) => ({ at: e.at, what: e.kind === "note" ? "note" : e.kind === "admin" ? "you" : EVENT_WORD[e.kind] ?? e.kind, note: e.note, by: e.kind === "note" ? ("note" as const) : e.kind === "admin" ? ("admin" as const) : ("shop" as const) })),
    // what the order's own events don't hold: tries that failed
    ...log.filter((l) => l.action.endsWith(".failed")).map((l) => ({ at: l.at, what: `${l.action.replace(/^order\./, "").replace(/\.failed$/, "")} failed`, note: String(l.detail?.error ?? ""), by: "admin" as const })),
    ...mails.map((x) => ({ at: x.at, what: `email sent: ${x.kind}`, by: "shop" as const })),
  ].sort((a, b) => a.at.localeCompare(b.at));

  const paid = o.stage !== "paying" && !!o.paidAt;
  const inHour = changeable(o) && o.paidAt && Date.now() - Date.parse(o.paidAt) < HOLD_MS;
  const back = refunded(o), left = o.total - back;
  const refundable = paid && left > 0;
  const shirts = o.lines.reduce((t, l) => t + l.quantity, 0);

  return (
    <>
      <PageHead title={`#${o.id}`} sub={<>placed {dt(o.createdAt)}{o.paidAt ? ` · paid ${dt(o.paidAt)}` : ""} · <StageBadge stage={o.stage} /></>}>
        <a href={orderPath(o.id)} target="_blank" rel="noreferrer" className="inline-flex h-9 items-center px-3 text-[13px] ring-1 ring-line hover:ring-ink">buyer&apos;s page ↗</a>
      </PageHead>

      {o.problem ? <p className="mb-8 border-l-2 border-[#f0a35b] py-1 pl-3 text-[14px]">{o.problem}</p> : null}

      <div className="grid gap-x-12 lg:grid-cols-2">
        <Section title="buyer">
          <KV items={[
            ["name", o.contact.name],
            ["email", <A key="e" href={`/admin/customers/${encodeURIComponent(o.contact.email)}`}>{o.contact.email}</A>],
            ["phone", <a key="p" href={`tel:+91${o.contact.phone}`} className="tnum">+91 {o.contact.phone}</a>],
            ["ship to", <span key="a">{o.ship.name}<br />{o.ship.address1}{o.ship.address2 ? <><br />{o.ship.address2}</> : null}<br />{o.ship.city}, {o.ship.state} {o.ship.pin}<br /><span className="text-quiet">+91 {o.ship.phone}</span></span>],
          ]} />
        </Section>

        <Section title="money" aside={m && !m.feeActual ? "fee estimated until fetched" : undefined}>
          {m ? (
            <KV items={[
              ["paid", inr(o.total)],
              ["refunded", back ? inr(back) : "–"],
              ["qikink cost", inr(m.cost, true)],
              ["razorpay fee", `${inr(m.fee, true)}${m.feeActual ? (fee?.tax != null ? ` (incl. ${inr(Number(fee.tax), true)} gst)` : "") : " est."}`],
              [`post (${Math.max(1, Math.ceil(shirts / s.shirtsPerParcel))} parcel)`, inr(m.ship, true)],
              ["margin", <span key="m" className="font-semibold text-blue">{inr(m.margin, true)}</span>],
            ]} />
          ) : <p className="text-[13px] text-quiet">not paid: {inr(o.total)} was asked.</p>}
        </Section>
      </div>

      <Section title="items">
        <Table head={["shirt", "size", "qty", "price", "qikink cost", "qikink sku"]}>
          {o.lines.map((l, i) => (
            <tr key={i}>
              <td>{shirtName(l.design)}</td>
              <td>{l.size}</td>
              <td className="tnum">{l.quantity}</td>
              <td className="tnum">{inr(l.unitPrice * l.quantity)}</td>
              <td className="tnum">{inr((c[l.design] ?? 0) * l.quantity, true)}</td>
              <td className="font-mono text-[12px] text-quiet">{partnerKeys()?.sandbox ? "sandbox blank" : skuOf(l.design, l.size) ?? "none set"}</td>
            </tr>
          ))}
        </Table>
      </Section>

      <div className="grid gap-x-12 lg:grid-cols-2">
        <Section title="payment · razorpay">
          <KV items={[
            ["razorpay order", <a key="o" className="font-mono text-[12px] underline decoration-line" href={`${dash}/orders/${o.rzpOrderId}`} target="_blank" rel="noreferrer">{o.rzpOrderId}</a>],
            ["payment", o.payment ? <a key="p" className="font-mono text-[12px] underline decoration-line" href={`${dash}/payments/${o.payment.id}`} target="_blank" rel="noreferrer">{o.payment.id}</a> : "–"],
            ["method", fee?.detail ?? o.payment?.label ?? "–"],
            ["fee", fee?.fee != null ? inr(Number(fee.fee), true) : "not fetched"],
            ["settlement", fee?.settlement_id ? `${fee.settlement_id}${fee.settled_at ? ` · ${dt(fee.settled_at)}` : ""}` : fee ? "not settled yet" : "not fetched"],
            ["refunds", o.refunds?.length ? <span key="r" className="grid gap-0.5">{o.refunds.map((r) => (
              <span key={r.id} className="text-[12px]"><span className="tnum">{inr(r.amount)}</span> · <a className="font-mono underline decoration-line" href={`${dash}/refunds/${r.id}`} target="_blank" rel="noreferrer">{r.id}</a> · {r.status}{r.doneAt ? ` ${dt(r.doneAt)}` : ""}{r.reason ? <span className="text-quiet"> · {r.reason}</span> : null}</span>
            ))}</span> : "–"],
          ]} />
          {paid && o.payment ? <div className="mt-3"><Act label="fetch fee and settlement" confirm="ask razorpay for this payment's fee, tax and settlement now." url={`/api/admin/orders/${o.id}`} body={{ action: "fees" }} /></div> : null}
        </Section>

        <Section title="print and post · qikink">
          <KV items={[
            ["qikink order", o.partnerId ? <span key="q" className="font-mono text-[12px]">{o.partnerId}</span> : paid ? (inHour ? "waits for the change-of-mind hour" : "not sent yet") : "–"],
            ["status", o.partnerRaw ?? "–"],
            ["last checked", o.syncedAt ? dt(o.syncedAt) : "–"],
            ["courier", o.tracking?.courier ?? "–"],
            ["awb", o.tracking?.awb ? <span key="a" className="font-mono text-[12px]">{o.tracking.awb}</span> : "–"],
            ["tracking", o.tracking?.url ? <a key="t" className="underline decoration-line" href={o.tracking.url} target="_blank" rel="noreferrer">open ↗</a> : "–"],
            ["shipped", o.shippedAt ? dt(o.shippedAt) : "–"],
            ["delivered", o.deliveredAt ? dt(o.deliveredAt) : "–"],
          ]} />
          {o.partnerId ? <div className="mt-3"><Act label="ask qikink now" confirm="fetch this order's status, courier and tracking from qikink now (the buyer is emailed if it has shipped)." url={`/api/admin/orders/${o.id}`} body={{ action: "sync" }} /></div> : null}
        </Section>
      </div>

      <Section title="actions" aside="each asks first, and every one is in the audit log">
        <div className="flex flex-wrap gap-2">
          {paid && !o.partnerId && o.stage !== "cancelled" ? (
            <Act label="send to qikink now" confirm={inHour ? "the buyer's change-of-mind hour isn't over: sending now ends it. qikink is charged from the wallet." : "hand this order to qikink now. qikink is charged from the wallet."}
              url={`/api/admin/orders/${o.id}`} body={{ action: "retry" }} />
          ) : null}
          {paid && !o.partnerId && o.stage !== "cancelled" ? (
            <Act danger label="cancel" confirm={`cancel #${o.id}: nothing is made and the buyer gets the cancelled email. with a refund, ${inr(left)} goes back through razorpay.`}
              typeToConfirm={o.id} url={`/api/admin/orders/${o.id}`} body={{ action: "cancel" }}
              fields={[{ name: "refund", label: "refund", options: ["full refund", "no refund"], initial: "full refund" }]} />
          ) : null}
          {refundable ? (
            <Act danger label="refund" confirm={`refund through razorpay, back the way it was paid (normal speed: 5–7 working days). the order itself carries on${o.partnerId ? ": it's with qikink already" : ""}. whole rupees, up to ${inr(left)}.`}
              typeToConfirm={o.id} url={`/api/admin/orders/${o.id}`} body={{ action: "refund" }}
              fields={[{ name: "amount", label: "amount in ₹", type: "number", initial: String(left) }, { name: "reason", label: "reason (the buyer sees it)", optional: true, placeholder: "a print fault on the back" }]} />
          ) : null}
          {paid ? (
            <Act label="resend an email" confirm={`send one of the buyer's emails again, as the order is now, to ${o.contact.email}.`}
              url={`/api/admin/orders/${o.id}`} body={{ action: "resend" }}
              fields={[{ name: "kind", label: "email", options: [...MAIL_KINDS], initial: o.stage === "cancelled" ? "cancelled" : o.deliveredAt ? "delivered" : o.shippedAt ? "shipped" : "confirmed" }]} />
          ) : null}
          {changeable(o) ? (
            <Act label="change the address" confirm="where it goes, before it goes to print. the buyer's saved addresses get it too."
              url={`/api/admin/orders/${o.id}`} body={{ action: "address" }}
              fields={[
                { name: "name", label: "name", initial: o.ship.name }, { name: "phone", label: "phone (10 digits)", initial: o.ship.phone },
                { name: "address1", label: "house, street", initial: o.ship.address1 }, { name: "address2", label: "area, landmark", initial: o.ship.address2, optional: true },
                { name: "city", label: "city", initial: o.ship.city }, { name: "state", label: "state", initial: o.ship.state }, { name: "pin", label: "pin", initial: o.ship.pin },
              ]} />
          ) : null}
          {o.stage === "paying" || (o.stage === "cancelled" && !(o.refunds ?? []).some((r) => r.status === "pending")) ? (
            <Act danger label="delete this order" confirm={`wipe #${o.id} from the shop for good: for test orders and checkouts that were never paid. it can't be brought back.`}
              typeToConfirm={o.id} url={`/api/admin/orders/${o.id}`} body={{ action: "delete" }} goTo="/admin/orders" />
          ) : null}
        </div>
        {o.partnerId && o.stage !== "delivered" && o.stage !== "cancelled" ? <p className="mt-4 text-[12px] text-quiet">it&apos;s with qikink: their API has no cancel or address change, so those are by writing to qikink support.</p> : null}
      </Section>

      <div className="grid gap-x-12 lg:grid-cols-[1.4fr_1fr]">
        <Section title="timeline">
          <ol className="grid gap-2 border-l border-line pl-4">
            {timeline.map((t, i) => (
              <li key={i} className="relative text-[13px]">
                <span className={`absolute -left-[21px] top-[6px] h-2 w-2 rounded-full ${t.by === "admin" ? "bg-blue" : t.by === "note" ? "bg-[#f0a35b]" : "bg-ink"}`} />
                <span className="tnum text-quiet">{dt(t.at)}</span> · <span className="font-medium">{t.what}</span>
                {t.by === "admin" ? <> <Pill>you</Pill></> : null}
                {t.note ? <div className="text-quiet">{t.note}</div> : null}
              </li>
            ))}
          </ol>
        </Section>
        <Section title="emails and notes">
          <KV items={[["sent", mails.length ? mails.map((x) => `${x.kind} (${dt(x.at)})`).join(", ") : "none yet"]]} />
          <div className="mt-4"><NoteForm url={`/api/admin/orders/${o.id}`} body={{ action: "note" }} /></div>
        </Section>
      </div>
    </>
  );
}
