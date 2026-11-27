import { DESIGNS, SIZE_ORDER, type Design } from "@/content/tee";
import { requireAdmin } from "@/lib/admin/auth";
import { allOrders, costs, isPaid, knownFees, shirtName, totalsBetween } from "@/lib/admin/data";
import { getSettings } from "@/lib/admin/settings";
import { refunded } from "@/lib/shop/orders";
import { BTN } from "../../ui/client";
import { Icon } from "../../ui/icons";
import { Empty, Group, Page, Row, Section, Tile, inr } from "../../ui/ui";
import { PeriodTabs, pickPeriod } from "../period";

export const metadata = { title: "money" };
export const dynamic = "force-dynamic";

const IST = 5.5 * 3600_000;
const minus = (n: number) => (n ? `− ${inr(n)}` : inr(0));

/** money: what came in over a period, where it went, what you keep; then month by month, the shirts, and Razorpay's payouts */
export default async function Money({ searchParams }: { searchParams: Promise<{ p?: string }> }) {
  await requireAdmin();
  const p = await pickPeriod((await searchParams).p);
  const [orders, s, fees, c] = await Promise.all([allOrders(), getSettings(), knownFees(), costs()]);
  const t = totalsBetween(orders, s, c, fees, p.from, p.to);
  const before = p.prev ? totalsBetween(orders, s, c, fees, p.prev.from, p.prev.to) : null;
  const word = p.prev?.word;
  const paid = orders.filter(isPaid);

  // month by month, from the first paid order to this one
  const months: { key: string; label: string; t: ReturnType<typeof totalsBetween> }[] = [];
  const first = paid.length ? Math.min(...paid.map((o) => Date.parse(o.paidAt!))) : null;
  if (first) {
    const now = new Date(Date.now() + IST);
    const f = new Date(first + IST);
    for (let y = now.getUTCFullYear(), m = now.getUTCMonth(); y > f.getUTCFullYear() || (y === f.getUTCFullYear() && m >= f.getUTCMonth()); m--) {
      if (m < 0) { m = 11; y--; }
      const from = Date.UTC(y, m, 1) - IST, to = Date.UTC(y, m + 1, 1) - IST;
      const label = new Date(from + IST).toLocaleDateString("en-IN", { month: "long", year: "numeric", timeZone: "UTC" }).toLowerCase();
      months.push({ key: `${y}-${m}`, label, t: totalsBetween(orders, s, c, fees, from, to) });
      if (months.length > 36) break;
    }
  }

  // each shirt in the period: how many, by size
  const sold = new Map<string, { n: number; sizes: Record<string, number> }>();
  for (const o of paid) {
    const at = Date.parse(o.paidAt!);
    if (at < p.from || at >= p.to || o.stage === "cancelled") continue;
    for (const l of o.lines) {
      const x = sold.get(l.design) ?? { n: 0, sizes: {} };
      x.n += l.quantity;
      x.sizes[l.size] = (x.sizes[l.size] ?? 0) + l.quantity;
      sold.set(l.design, x);
    }
  }
  const shirts = (Object.keys(DESIGNS) as Design[]).map((d) => ({ d, ...(sold.get(d) ?? { n: 0, sizes: {} }) })).sort((a, b) => b.n - a.n);

  // Razorpay's payouts: what it has told us it settled, and what it still holds
  let held = 0, heldN = 0, lastPayout: string | null = null;
  for (const o of paid) {
    if (o.stage === "cancelled" && refunded(o) >= o.total) continue;
    const f = fees.get(o.id);
    if (f?.settled_at) { if (!lastPayout || f.settled_at > lastPayout) lastPayout = f.settled_at; continue; }
    held += o.total - refunded(o) - (f?.fee != null ? Number(f.fee) : o.total * s.feeRate);
    heldN++;
  }

  const avg = t.orders ? t.revenue / t.orders : 0;
  const gross = t.revenue + t.refunded;

  return (
    <>
      <Page title="money" sub={`${p.label}: what came in, where it went, and what you keep`}
        actions={<a href="/api/admin/orders/export" className={BTN.plain}><Icon name="download" className="h-[18px] w-[18px]" />every order as csv</a>} />
      <PeriodTabs p={p} />

      <div className="mb-10 grid grid-cols-2 gap-3 md:mb-12 lg:grid-cols-4">
        <Tile label="you keep" icon="chart" value={inr(t.margin)} delta={before ? { now: t.margin, was: before.margin, word, money: true } : undefined} sub={t.estimated ? "some fees estimated" : undefined} />
        <Tile label="sales" icon="money" value={inr(t.revenue)} delta={before ? { now: t.revenue, was: before.revenue, word, money: true } : undefined} />
        <Tile label="shirts sold" icon="shirt" value={t.shirts} delta={before ? { now: t.shirts, was: before.shirts, word } : undefined} sub={`in ${t.orders} order${t.orders === 1 ? "" : "s"}`} />
        <Tile label="an order" icon="bag" value={inr(Math.round(avg))} sub={t.orders ? "on average" : "no orders yet"} />
      </div>

      <div className="grid gap-x-6 lg:grid-cols-2">
        <Section title="where it went">
          <Group>
            <Row title="buyers paid" sub={`${t.orders + t.cancelled} order${t.orders + t.cancelled === 1 ? "" : "s"}`} right={<span className="tnum">{inr(gross)}</span>} />
            <Row title="refunded" sub={t.refunds ? `${t.refunds} refund${t.refunds === 1 ? "" : "s"}${t.cancelled ? `, ${t.cancelled} cancelled` : ""}` : "none"} right={<span className="tnum text-quiet">{minus(t.refunded)}</span>} />
            <Row title="qikink" sub="making and printing each shirt" right={<span className="tnum text-quiet">{minus(t.cost)}</span>} />
            <Row title="payment fees" sub={t.estimated ? `razorpay's, at ${(s.feeRate * 100).toFixed(1)}% where it hasn't said yet` : "razorpay's, as it charged them"} right={<span className="tnum text-quiet">{minus(t.fees)}</span>} />
            <Row title="post" sub={`${inr(s.shipPerParcel)} a parcel, ${s.shirtsPerParcel} shirt${s.shirtsPerParcel === 1 ? "" : "s"} to one`} right={<span className="tnum text-quiet">{minus(t.ship)}</span>} />
            <Row title={<span className="font-semibold">you keep</span>} sub={gross ? `${Math.round((t.margin / Math.max(1, t.revenue)) * 100)}% of sales` : undefined} right={<span className="tnum font-semibold">{inr(t.margin)}</span>} />
          </Group>
        </Section>

        <Section title="razorpay payouts">
          <Group>
            <Row icon="clock" title="still with razorpay" sub={heldN ? `${heldN} payment${heldN === 1 ? "" : "s"} not paid out to you yet, after fees` : "everything has been paid out"} right={<span className="tnum">{inr(Math.round(held))}</span>} />
            <Row icon="check" title="last payout" sub="the newest settlement razorpay told us about" right={<span className="text-quiet">{lastPayout ? new Date(lastPayout).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).toLowerCase() : "none yet"}</span>} />
            <Row icon="out" external href="https://dashboard.razorpay.com/app/settlements" title="settlements in razorpay" sub="each payout and the bank reference" />
          </Group>
        </Section>
      </div>

      <Section title="shirts sold" aside={p.label}>
        <Group>
          {shirts.map((x) => (
            <Row key={x.d} icon="shirt" muted={!x.n} title={shirtName(x.d)}
              sub={x.n ? SIZE_ORDER.filter((z) => x.sizes[z]).map((z) => `${z} ${x.sizes[z]}`).join(" · ") : "none sold"}
              right={<span className="tnum">{x.n}</span>} />
          ))}
        </Group>
      </Section>

      <Section title="month by month">
        {months.length ? (
          <Group>
            {months.map((m) => (
              <Row key={m.key} muted={!m.t.orders} title={m.label}
                sub={m.t.orders ? `${m.t.orders} order${m.t.orders === 1 ? "" : "s"} · ${m.t.shirts} shirt${m.t.shirts === 1 ? "" : "s"}${m.t.refunded ? ` · ${inr(m.t.refunded)} refunded` : ""}` : "no orders"}
                right={<span className="grid justify-items-end gap-0.5"><span className="tnum">{inr(m.t.revenue)}</span><span className="tnum text-[13px] text-quiet">keep {inr(m.t.margin)}</span></span>} />
            ))}
          </Group>
        ) : <Empty icon="money" title="no money yet" sub="the first paid order shows here, with its month" />}
      </Section>
    </>
  );
}
