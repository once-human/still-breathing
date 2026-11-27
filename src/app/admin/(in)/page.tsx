import { DESIGNS, SIZE_ORDER, type Design } from "@/content/tee";
import { requireAdmin } from "@/lib/admin/auth";
import { overview, shirtName, type Totals } from "@/lib/admin/data";
import { partnerKeys, razorpayKeys, shopOpen } from "@/lib/shop/config";
import { refunded } from "@/lib/shop/orders";
import { products } from "@/lib/shop/products";
import { liveCount, listVisits } from "@/lib/visits/server";
import { Segmented, Toggle } from "../ui/client";
import { A, PageHead, Pill, Section, StageBadge, Stat, Table, ago, dt, inr } from "../ui/ui";
import { VisitTable } from "../ui/visits";
import { LiveStrip } from "./LiveStrip";

export const metadata = { title: "home" };
export const dynamic = "force-dynamic";

const STATUS = [
  { value: "live" as const, label: "on sale", tone: "ok" as const },
  { value: "soldout" as const, label: "sold out", tone: "warn" as const },
  { value: "draft" as const, label: "hidden", tone: "off" as const },
];

function Period({ name, t }: { name: string; t: Totals }) {
  return (
    <div className="grid content-start gap-4">
      <h3 className="text-[15px] font-semibold">{name}</h3>
      <div className="grid grid-cols-2 gap-4">
        <Stat label="orders" value={t.orders} sub={<>{t.shirts} shirts{t.cancelled ? <span className="text-[#f0a35b]"> · {t.cancelled} cancelled</span> : null}</>} />
        <Stat label="revenue" value={inr(t.revenue)} sub={t.refunds ? <span className="text-[#f0a35b]">{t.refunds} refund{t.refunds > 1 ? "s" : ""}, {inr(t.refunded)} back</span> : "after refunds"} />
        <Stat label="margin" value={inr(t.margin)} tone="blue" sub={t.estimated ? "fees partly estimated" : "actual fees"} />
        <Stat label="costs" value={inr(t.cost + t.fees + t.ship)} sub={`qikink ${inr(t.cost)} · fees ${inr(t.fees)} · post ${inr(t.ship)}`} />
      </div>
    </div>
  );
}

/** today against yesterday, one line each */
function Versus({ today, yesterday }: { today: Totals; yesterday: Totals }) {
  const rows: [string, number, number, (n: number) => string][] = [
    ["orders", today.orders, yesterday.orders, String],
    ["shirts", today.shirts, yesterday.shirts, String],
    ["revenue", today.revenue, yesterday.revenue, (n) => inr(n)],
    ["margin", today.margin, yesterday.margin, (n) => inr(n)],
  ];
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {rows.map(([l, a, b, f]) => (
        <Stat key={l} label={l} value={f(a)} sub={<span className={a > b ? "text-[#8fd19e]" : a < b ? "text-[#f0a35b]" : ""}>{a > b ? "▲" : a < b ? "▼" : "="} yesterday {f(b)}</span>} />
      ))}
    </div>
  );
}

export default async function Home() {
  await requireAdmin();
  const [{ orders, totals, bySize, needs, settings }, shirts, count, visits] = await Promise.all([
    overview(),
    products().catch(() => []),
    liveCount(),
    listVisits(24, { kind: "person" }, 8).catch(() => []),
  ]);
  const recent = orders.filter((o) => o.stage !== "paying").slice(0, 8);
  const designs = Object.keys(DESIGNS) as Design[];
  const sizeTotal = (s: (typeof SIZE_ORDER)[number]) => designs.reduce((t, d) => t + (bySize[d]?.[s] ?? 0), 0);
  const unpaid = orders.filter((o) => o.stage === "paying" && Date.now() - Date.parse(o.createdAt) < 86400_000).length;
  const connected = shopOpen();

  return (
    <>
      <PageHead title="home" sub={<>
        {connected ? (settings.open ? <Pill tone="ok">taking orders</Pill> : <Pill tone="warn">orders switched off</Pill>) : <Pill tone="warn">not connected: keys missing</Pill>}
        {" "}{razorpayKeys()?.test ? <Pill tone="warn">razorpay test mode</Pill> : null} {partnerKeys()?.sandbox ? <Pill tone="warn">qikink sandbox</Pill> : null}
        {settings.notice ? <span className="ml-1">· top line: “{settings.notice}”</span> : null}
      </>}>
        <A href="/admin/status" className="text-[13px]">what&apos;s live →</A>
      </PageHead>

      <LiveStrip initial={count} />

      <Section title="needs you" aside={needs.length ? `${needs.length}` : undefined}>
        {needs.length ? (
          <ul className="grid gap-2">
            {needs.map((n, i) => (
              <li key={i} className={`rounded-r-lg border-l-2 py-2 pl-3 ${n.level === "now" ? "border-[#f0a35b] bg-[#f0a35b]/[0.06]" : "border-line"}`}>
                <A href={n.href} className="text-[14px] font-medium">{n.title}</A>
                <div className="text-[12px] text-quiet">{n.detail}</div>
              </li>
            ))}
          </ul>
        ) : <p className="text-[13px] text-quiet">nothing. every paid order is moving.{unpaid ? ` ${unpaid} checkout${unpaid > 1 ? "s" : ""} in the last day stopped before paying.` : ""}</p>}
      </Section>

      <Section title="quick switches" aside="saved the moment you flip them">
        <div className="grid gap-x-12 rounded-xl border border-line px-4 py-1 lg:grid-cols-2">
          <div className="divide-y divide-line/60">
            <Toggle label="taking orders" field="open" url="/api/admin/settings" value={settings.open}
              hint={connected ? (settings.open ? "the bag and checkout work on every page" : "people can look, but checkout is closed") : "payments aren't connected, so it stays closed either way"}
              confirmOff="checkout closes on the whole site at once. people can still look and fill their bag; anyone mid-payment can finish."
              confirmOn="checkout opens again for everyone, at the prices shown now." />
          </div>
          <div className="divide-y divide-line/60">
            {shirts.map((p) => (
              <div key={p.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <A href={`/admin/products/${p.id}`} className="min-w-0 text-[14px] font-medium">{shirtName(p.id)} <span className="tnum text-[12px] font-normal text-quiet">{inr(p.price)}</span></A>
                <Segmented compact label={shirtName(p.id)} value={p.status} options={STATUS} url={`/api/admin/products/${p.id}`} field="status" />
              </div>
            ))}
          </div>
        </div>
      </Section>

      <Section title="today against yesterday"><Versus today={totals.today} yesterday={totals.yesterday} /></Section>

      <Section title="money" aside={`margin = paid − refunds − qikink cost − razorpay fee − post (${inr(settings.shipPerParcel, true)} a parcel of ${settings.shirtsPerParcel}). cancelled orders aren't counted as orders`}>
        <div className="grid gap-10 md:grid-cols-3">
          <Period name="today" t={totals.today} />
          <Period name="this week" t={totals.week} />
          <Period name="all time" t={totals.all} />
        </div>
      </Section>

      <Section title="latest orders" aside={<A href="/admin/orders">all orders</A>}>
        <Table head={["order", "when", "buyer", "shirts", "total", "where"]} empty="no paid orders yet">
          {recent.map((o) => {
            const back = refunded(o);
            const off = o.stage === "cancelled";
            return (
              <tr key={o.id} className={off ? "opacity-60" : ""}>
                <td><A href={`/admin/orders/${o.id}`} className={`font-mono ${off ? "line-through" : ""}`}>{o.id}</A></td>
                <td className="whitespace-nowrap text-quiet" title={dt(o.createdAt)}>{ago(o.paidAt ?? o.createdAt)}</td>
                <td>{o.contact.name}<div className="text-[12px] text-quiet">{o.ship.city}</div></td>
                <td>{o.lines.map((l) => `${shirtName(l.design)} ${l.size}${l.quantity > 1 ? ` ×${l.quantity}` : ""}`).join(", ")}</td>
                <td className="tnum">{inr(o.total)}{back > 0 ? <div className="text-[11px] text-[#f0a35b]">{inr(back)} refunded</div> : null}</td>
                <td><StageBadge stage={o.stage} /></td>
              </tr>
            );
          })}
        </Table>
      </Section>

      <Section title="latest visitors" aside={<A href="/admin/visitors">every visit</A>}>
        <VisitTable visits={visits} empty="nobody in the last day" />
      </Section>

      <Section title="shirts sold by size" aside="paid, not cancelled">
        <Table head={["shirt", ...SIZE_ORDER, "all"]}>
          {designs.map((d) => (
            <tr key={d}>
              <td className="whitespace-nowrap">{shirtName(d)}</td>
              {SIZE_ORDER.map((s) => <td key={s} className="tnum">{bySize[d]?.[s] || <span className="text-line">0</span>}</td>)}
              <td className="tnum font-semibold">{SIZE_ORDER.reduce((t, s) => t + (bySize[d]?.[s] ?? 0), 0)}</td>
            </tr>
          ))}
          <tr className="font-semibold">
            <td>all</td>
            {SIZE_ORDER.map((s) => <td key={s} className="tnum">{sizeTotal(s)}</td>)}
            <td className="tnum">{SIZE_ORDER.reduce((t, s) => t + sizeTotal(s), 0)}</td>
          </tr>
        </Table>
        <p className="mt-3 text-[12px] text-quiet">
          qikink&apos;s API has no wallet balance, so it isn&apos;t shown. a low wallet shows up in “needs you” the moment a print order is refused for it, and you get an email.
          keep at least {inr(settings.lowWallet)} in it: <a className="underline" href="https://qikink.com" target="_blank" rel="noreferrer">qikink ↗</a>
        </p>
      </Section>
    </>
  );
}
