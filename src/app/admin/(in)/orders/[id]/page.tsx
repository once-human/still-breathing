import { notFound } from "next/navigation";
import { requireAdmin } from "@/lib/admin/auth";
import { costs, knownFees, marginOf, shirtName } from "@/lib/admin/data";
import { auditFor } from "@/lib/admin/log";
import { getSettings } from "@/lib/admin/settings";
import { partnerKeys, razorpayKeys } from "@/lib/shop/config";
import { HOLD_MS, MAIL_KINDS, changeable, emailsSent, loadOrder, orderPath, refunded, validId, type Order } from "@/lib/shop/orders";
import { products } from "@/lib/shop/products";
import { EVENT_WORD } from "@/lib/shop/words";
import { Act, BTN, NoteForm } from "../../../ui/client";
import { Icon } from "../../../ui/icons";
import { Card, Group, KV, Page, Row, Section, StageBadge, dt, inr } from "../../../ui/ui";

export const metadata = { title: "order" };
export const dynamic = "force-dynamic";

/** Postgres's text time ("2026-11-26 14:00:00.1+00") as ISO */
const pgTime = (t: string) => {
  const d = new Date(t.replace(" ", "T").replace(/([+-]\d\d)$/, "$1:00"));
  return Number.isNaN(d.getTime()) ? new Date(0).toISOString() : d.toISOString();
};

type Line = { at: string; what: string; note?: string; by: "shop" | "admin" | "note" };

/** where the order is, as four steps: paid, being made, on its way, delivered */
function Progress({ o }: { o: Order }) {
  if (o.stage === "cancelled" || o.stage === "paying") {
    return (
      <Card className="flex items-center gap-4">
        <span className="grid h-10 w-10 place-items-center rounded-full bg-s3 text-quiet"><Icon name={o.stage === "cancelled" ? "x" : "clock"} /></span>
        <div><div className="text-[17px] font-semibold">{o.stage === "cancelled" ? "cancelled" : "not paid"}</div><div className="text-[13px] text-quiet">{o.stage === "cancelled" ? "nothing was made or sent" : `checkout started ${dt(o.createdAt)}, never paid`}</div></div>
      </Card>
    );
  }
  const made = o.events?.find((e) => e.kind === "printing")?.at ?? (o.partnerId ? o.paidAt : null);
  const steps: [string, string | null | undefined][] = [["paid", o.paidAt], ["being made", made], ["on its way", o.shippedAt], ["delivered", o.deliveredAt]];
  const at = steps.filter(([, t]) => t).length - 1;
  return (
    <Card>
      <ol className="grid grid-cols-4 gap-2">
        {steps.map(([word, t], i) => (
          <li key={word} className="min-w-0">
            <div className={`h-1.5 rounded-full ${i <= at ? (o.stage === "attention" && i === at ? "bg-warn" : i === 3 ? "bg-ok" : "bg-ink/80") : "bg-s3"}`} />
            <div className={`mt-3 text-[14px] ${i <= at ? "font-semibold" : "text-quiet"}`}>{word}</div>
            <div className="tnum text-[12.5px] text-quiet">{t ? dt(t) : "–"}</div>
          </li>
        ))}
      </ol>
    </Card>
  );
}

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

  const timeline: Line[] = [
    ...(o.events ?? []).map((e) => ({ at: e.at, what: e.kind === "note" ? "note" : e.kind === "admin" ? "you" : EVENT_WORD[e.kind] ?? e.kind, note: e.note, by: e.kind === "note" ? ("note" as const) : e.kind === "admin" ? ("admin" as const) : ("shop" as const) })),
    ...log.filter((l) => l.action.endsWith(".failed")).map((l) => ({ at: l.at, what: `${l.action.replace(/^order\./, "").replace(/\.failed$/, "")} failed`, note: String(l.detail?.error ?? ""), by: "admin" as const })),
    ...mails.map((x) => ({ at: x.at, what: `email: ${x.kind}`, by: "shop" as const })),
  ].sort((a, b) => b.at.localeCompare(a.at));

  const paid = o.stage !== "paying" && !!o.paidAt;
  const inHour = changeable(o) && o.paidAt && Date.now() - Date.parse(o.paidAt) < HOLD_MS;
  const back = refunded(o), left = o.total - back;
  const shirts = o.lines.reduce((t, l) => t + l.quantity, 0);
  const url = `/api/admin/orders/${o.id}`;
  const canPrint = paid && !o.partnerId && o.stage !== "cancelled";
  const canDelete = o.stage === "paying" || (o.stage === "cancelled" && !(o.refunds ?? []).some((r) => r.status === "pending"));

  return (
    <>
      <Page title={o.contact.name.toLowerCase()} back={["/admin/orders", "orders"]}
        sub={<span className="inline-flex flex-wrap items-center gap-x-3 gap-y-2"><span className="font-mono">#{o.id}</span><StageBadge stage={o.stage} /><span>{inr(o.total)} · {shirts} shirt{shirts > 1 ? "s" : ""}</span></span>}
        actions={<a href={orderPath(o.id)} target="_blank" rel="noreferrer" className={BTN.plain}>buyer&apos;s page<Icon name="out" className="h-4 w-4" /></a>} />

      {o.problem ? (
        <div className="a-pop mb-8 flex items-start gap-4 rounded-[22px] bg-warn/10 p-5">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-warn/15 text-warn"><Icon name="alert" /></span>
          <div><div className="text-[15px] font-semibold text-warn">needs you</div><p className="mt-0.5 text-[14px] text-ink/85">{o.problem}</p></div>
        </div>
      ) : null}

      <div className="mb-10"><Progress o={o} /></div>

      <div className="grid gap-x-6 lg:grid-cols-[1.35fr_1fr]">
        <div>
          <Section title="shirts">
            <Group>
              {o.lines.map((l, i) => (
                <Row key={i} icon="shirt" title={shirtName(l.design)} sub={`size ${l.size} · ${l.quantity} × ${inr(l.unitPrice)} · ${partnerKeys()?.sandbox ? "sandbox blank" : skuOf(l.design, l.size) ?? "no qikink sku"}`} right={<span className="tnum">{inr(l.unitPrice * l.quantity)}</span>} />
              ))}
            </Group>
          </Section>

          <Section title="money" aside={m && !m.feeActual ? "fee estimated until fetched" : undefined}>
            {m ? (
              <KV items={[
                ["paid", <span key="p" className="tnum">{inr(o.total)}{o.payment ? <span className="text-quiet"> · {o.payment.label}</span> : null}</span>],
                ...(back ? [["refunded", <span key="r" className="tnum text-warn">−{inr(back)}</span>] as [string, React.ReactNode]] : []),
                ["qikink", <span key="q" className="tnum text-quiet">−{inr(m.cost, true)}</span>],
                ["razorpay fee", <span key="f" className="tnum text-quiet">−{inr(m.fee, true)}{m.feeActual ? "" : " est."}</span>],
                [`post, ${Math.max(1, Math.ceil(shirts / s.shirtsPerParcel))} parcel`, <span key="s" className="tnum text-quiet">−{inr(m.ship, true)}</span>],
                ["you keep", <span key="m" className="tnum text-[17px] font-bold text-ink">{inr(m.margin, true)}</span>],
              ]} />
            ) : <Card><p className="text-[15px] text-quiet">not paid: {inr(o.total)} was asked.</p></Card>}
          </Section>

          <Section title="everything that happened">
            <Card>
              <ol className="relative grid gap-5 before:absolute before:bottom-2 before:left-[5px] before:top-2 before:w-px before:bg-line">
                {timeline.map((t, i) => (
                  <li key={i} className="relative pl-7">
                    <span className={`absolute left-0 top-[5px] h-[11px] w-[11px] rounded-full ring-4 ring-s1 ${t.by === "admin" ? "bg-ink/80" : t.by === "note" ? "bg-warn" : i === 0 ? "bg-ink" : "bg-quiet"}`} />
                    <div className="text-[15px]">{t.what}{t.by === "admin" ? <span className="ml-2 text-[13px] text-quiet">by you</span> : null}</div>
                    {t.note ? <div className="mt-0.5 text-[14px] text-quiet">{t.note}</div> : null}
                    <div className="tnum mt-0.5 text-[13px] text-quiet">{dt(t.at)}</div>
                  </li>
                ))}
              </ol>
            </Card>
          </Section>
        </div>

        <div>
          <Section title="buyer">
            <Group>
              <Row icon="user" title={o.contact.name} sub="all their orders and their account" href={`/admin/people/${encodeURIComponent(o.contact.email)}`} />
              <Row icon="mail" title={o.contact.email} href={`mailto:${o.contact.email}`} external />
              <Row icon="phone" title={<span className="tnum">+91 {o.contact.phone}</span>} href={`tel:+91${o.contact.phone}`} external />
              <Row icon="pin" title={o.ship.name} sub={<>{o.ship.address1}{o.ship.address2 ? `, ${o.ship.address2}` : ""}<br />{o.ship.city}, {o.ship.state} {o.ship.pin} · +91 {o.ship.phone}</>} />
            </Group>
          </Section>

          {paid || canDelete ? (
            <Section title="manage" aside="each asks first">
              <Group>
                {canPrint ? (
                  <Act row={{ icon: "print", sub: inHour ? "skips the rest of the change-of-mind hour" : "hand it to qikink now" }} label="send to print now" url={url} body={{ action: "retry" }}
                    confirm={inHour ? "the buyer's change-of-mind hour isn't over: sending now ends it. qikink is charged from the wallet." : "hand this order to qikink now. qikink is charged from the wallet."} />
                ) : null}
                {changeable(o) ? (
                  <Act row={{ icon: "pin", sub: "before it goes to print; the buyer is emailed" }} label="change the address" url={url} body={{ action: "address" }}
                    confirm="where it goes, before it goes to print. the buyer gets an email with the new address."
                    fields={[
                      { name: "name", label: "name", initial: o.ship.name }, { name: "phone", label: "phone (10 digits)", initial: o.ship.phone },
                      { name: "address1", label: "house, street", initial: o.ship.address1 }, { name: "address2", label: "area, landmark", initial: o.ship.address2, optional: true },
                      { name: "city", label: "city", initial: o.ship.city }, { name: "state", label: "state", initial: o.ship.state }, { name: "pin", label: "pin", initial: o.ship.pin },
                    ]} />
                ) : null}
                {paid ? (
                  <Act row={{ icon: "mail", sub: `to ${o.contact.email}` }} label="send an email again" url={url} body={{ action: "resend" }}
                    confirm={`send one of the buyer's emails again, as the order is now, to ${o.contact.email}.`}
                    fields={[{ name: "kind", label: "which email", options: [...MAIL_KINDS], initial: o.stage === "cancelled" ? "cancelled" : o.deliveredAt ? "delivered" : o.shippedAt ? "shipped" : "confirmed" }]} />
                ) : null}
                {paid && left > 0 ? (
                  <Act row={{ icon: "return", sub: `any part, up to ${inr(left)}; the order carries on` }} danger label="refund" url={url} body={{ action: "refund" }} typeToConfirm={o.id}
                    confirm={`refund through razorpay, back the way it was paid (5–7 working days). the order itself carries on${o.partnerId ? ": it's with qikink already" : ""}. whole rupees, up to ${inr(left)}.`}
                    fields={[{ name: "amount", label: "amount in ₹", type: "number", initial: String(left) }, { name: "reason", label: "reason (the buyer sees it)", optional: true, placeholder: "a print fault on the back" }]} />
                ) : null}
                {canPrint ? (
                  <Act row={{ icon: "x", sub: "nothing is made; refund it in full or not" }} danger label="cancel the order" url={url} body={{ action: "cancel" }} typeToConfirm={o.id}
                    confirm={`cancel #${o.id}: nothing is made and the buyer gets the cancelled email. with a refund, ${inr(left)} goes back through razorpay.`}
                    fields={[{ name: "refund", label: "refund", options: ["full refund", "no refund"], initial: "full refund" }]} />
                ) : null}
                {canDelete ? (
                  <Act row={{ icon: "trash", sub: "for test orders and checkouts never paid" }} danger label="delete this order" url={url} body={{ action: "delete" }} typeToConfirm={o.id} goTo="/admin/orders"
                    confirm={`wipe #${o.id} from the shop for good. it can't be brought back.`} />
                ) : null}
              </Group>
              {o.partnerId && o.stage !== "delivered" && o.stage !== "cancelled" ? <p className="mt-3 px-1 text-[13px] text-quiet">it&apos;s with qikink, whose API has no cancel or address change: write to qikink support for those.</p> : null}
            </Section>
          ) : null}

          <Section title="payment">
            <Group>
              <Row icon="card" title={fee?.detail ?? o.payment?.label ?? "not paid"} sub={fee?.fee != null ? `fee ${inr(Number(fee.fee), true)}${fee.tax != null ? `, ${inr(Number(fee.tax), true)} of it gst` : ""} · ${fee.settlement_id ? `settled ${fee.settled_at ? dt(fee.settled_at) : ""}` : "not settled yet"}` : "fee not fetched yet"}
                href={o.payment ? `${dash}/payments/${o.payment.id}` : `${dash}/orders/${o.rzpOrderId}`} external />
              {(o.refunds ?? []).map((r) => (
                <Row key={r.id} icon="return" tone={r.status === "failed" ? "bad" : "quiet"} title={`${inr(r.amount)} refund, ${r.status}`} sub={`${r.reason ? `${r.reason} · ` : ""}${r.doneAt ? dt(r.doneAt) : dt(r.at)}`} href={`${dash}/refunds/${r.id}`} external />
              ))}
              {paid && o.payment ? <Act row={{ icon: "refresh", sub: "the fee, its gst and the settlement, from razorpay" }} label="fetch from razorpay" url={url} body={{ action: "fees" }} confirm="ask razorpay for this payment's fee, tax and settlement now." /> : null}
            </Group>
          </Section>

          <Section title="print and post">
            <Group>
              <Row icon="print" title={o.partnerId ? `qikink order ${o.partnerId}` : paid ? (inHour ? "waits for the change-of-mind hour" : "not with qikink yet") : "–"} sub={o.partnerRaw ? `qikink says: ${o.partnerRaw}${o.syncedAt ? ` · asked ${dt(o.syncedAt)}` : ""}` : undefined} />
              {o.tracking ? <Row icon="truck" title={o.tracking.courier?.toLowerCase() ?? "courier"} sub={o.tracking.awb ? `tracking ${o.tracking.awb}` : undefined} href={o.tracking.url ?? undefined} external={!!o.tracking.url} /> : null}
              {o.partnerId ? <Act row={{ icon: "refresh", sub: "status, courier and tracking; the buyer is emailed if it has left" }} label="ask qikink now" url={url} body={{ action: "sync" }} confirm="fetch this order's status, courier and tracking from qikink now (the buyer is emailed if it has shipped)." /> : null}
            </Group>
          </Section>

          <Section title="notes"><Card><NoteForm url={url} body={{ action: "note" }} /></Card></Section>
        </div>
      </div>
    </>
  );
}
