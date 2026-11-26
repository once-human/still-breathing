import { DESIGNS, SIZE_ORDER, type Design } from "@/content/tee";
import { requireAdmin } from "@/lib/admin/auth";
import { overview, shirtName, type Totals } from "@/lib/admin/data";
import { partnerKeys, razorpayKeys, shopOpen } from "@/lib/shop/config";
import { A, Missing, PageHead, Pill, Section, StageBadge, Stat, Table, ago, dt, inr } from "../ui/ui";

export const metadata = { title: "overview" };

function Period({ name, t }: { name: string; t: Totals }) {
  return (
    <div className="grid gap-4">
      <h3 className="text-[15px] font-semibold">{name}</h3>
      <div className="grid grid-cols-2 gap-4">
        <Stat label="orders" value={t.orders} sub={`${t.shirts} shirts`} />
        <Stat label="revenue" value={inr(t.revenue)} sub="after refunds" />
        <Stat label="margin" value={inr(t.margin)} tone="blue" sub={t.estimated ? "fees partly estimated" : "actual fees"} />
        <Stat label="costs" value={inr(t.cost + t.fees + t.ship)} sub={`qikink ${inr(t.cost)} · fees ${inr(t.fees)} · post ${inr(t.ship)}`} />
      </div>
    </div>
  );
}

export default async function Overview() {
  await requireAdmin();
  const { orders, totals, bySize, needs, settings } = await overview();
  const recent = orders.filter((o) => o.stage !== "paying").slice(0, 8);
  const designs = Object.keys(DESIGNS) as Design[];
  const sizeTotal = (s: (typeof SIZE_ORDER)[number]) => designs.reduce((t, d) => t + (bySize[d]?.[s] ?? 0), 0);
  const unpaid = orders.filter((o) => o.stage === "paying" && Date.now() - Date.parse(o.createdAt) < 86400_000).length;

  return (
    <>
      <PageHead title="overview" sub={<>
        shop {shopOpen() ? (settings.open ? <Pill tone="ok">taking orders</Pill> : <Pill tone="warn">closed in settings</Pill>) : <Pill tone="warn">not connected: keys missing</Pill>}
        {" "}{razorpayKeys()?.test ? <Pill tone="warn">razorpay test mode</Pill> : null} {partnerKeys()?.sandbox ? <Pill tone="warn">qikink sandbox</Pill> : null}
      </>} />

      <Section title="needs you" aside={needs.length ? `${needs.length}` : undefined}>
        {needs.length ? (
          <ul className="grid gap-2">
            {needs.map((n, i) => (
              <li key={i} className={`border-l-2 py-1 pl-3 ${n.level === "now" ? "border-[#f0a35b]" : "border-line"}`}>
                <A href={n.href} className="text-[14px] font-medium">{n.title}</A>
                <div className="text-[12px] text-quiet">{n.detail}</div>
              </li>
            ))}
          </ul>
        ) : <p className="text-[13px] text-quiet">nothing. every paid order is moving.</p>}
      </Section>

      <Section title="money" aside={`margin = paid − refunds − qikink cost − razorpay fee − post (${inr(settings.shipPerParcel, true)} a parcel of ${settings.shirtsPerParcel})`}>
        <div className="grid gap-10 md:grid-cols-3">
          <Period name="today" t={totals.today} />
          <Period name="this week" t={totals.week} />
          <Period name="all time" t={totals.all} />
        </div>
      </Section>

      <div className="grid gap-10 lg:grid-cols-[1.3fr_1fr]">
        <Section title="shirts by size" aside="paid, not cancelled">
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
        </Section>

        <Section title="qikink wallet">
          <Missing>
            qikink&apos;s order API has no balance call, so the wallet isn&apos;t shown here.
            a low wallet shows up above the moment a print order is refused for it, and you get the email.
            keep at least {inr(settings.lowWallet)} in it: <a className="underline" href="https://qikink.com" target="_blank" rel="noreferrer">qikink ↗</a>
          </Missing>
          {unpaid ? <p className="mt-3 text-[12px] text-quiet">{unpaid} checkout{unpaid > 1 ? "s" : ""} started in the last day without paying.</p> : null}
        </Section>
      </div>

      <Section title="latest orders" aside={<A href="/admin/orders">all orders</A>}>
        <Table head={["order", "when", "buyer", "shirts", "total", "where"]} empty="no paid orders yet">
          {recent.map((o) => (
            <tr key={o.id}>
              <td><A href={`/admin/orders/${o.id}`} className="font-mono">{o.id}</A></td>
              <td className="whitespace-nowrap text-quiet" title={dt(o.createdAt)}>{ago(o.paidAt ?? o.createdAt)}</td>
              <td>{o.contact.name}<div className="text-[12px] text-quiet">{o.ship.city}</div></td>
              <td>{o.lines.map((l) => `${shirtName(l.design)} ${l.size}${l.quantity > 1 ? ` ×${l.quantity}` : ""}`).join(", ")}</td>
              <td className="tnum">{inr(o.total)}</td>
              <td><StageBadge stage={o.stage} /></td>
            </tr>
          ))}
        </Table>
      </Section>
    </>
  );
}
