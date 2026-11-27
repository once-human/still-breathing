import { requireAdmin } from "@/lib/admin/auth";
import { periodData } from "@/lib/admin/data";
import { health, problems } from "@/lib/admin/health";
import { kv } from "@/lib/shop/kv";
import { funnelBetween, liveCount, peoplePerDay, sinceThen } from "@/lib/visits/server";
import type { IconName } from "../ui/icons";
import { DayChart, Funnel } from "../ui/charts";
import { A, Card, Group, Page, Row, Section, Tile, inr } from "../ui/ui";
import { PeriodTabs, pickPeriod } from "./period";

export const metadata = { title: "overview" };
export const dynamic = "force-dynamic";

const IST = 5.5 * 3600_000;
const ICON: Record<string, IconName> = { open: "shop", pay: "card", print: "print", sync: "truck", db: "shield", mail: "mail", alerts: "alert", secret: "key", admin: "user" };
const day = (ms: number) => new Date(ms + IST).toISOString().slice(0, 10);
const when = (ms: number) => {
  const h = (Date.now() - ms) / 3600_000;
  return h < 20 ? new Date(ms).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" }).toLowerCase()
    : h < 24 * 6 ? new Date(ms).toLocaleDateString("en-IN", { weekday: "long", timeZone: "Asia/Kolkata" }).toLowerCase()
    : new Date(ms).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).toLowerCase();
};

/** "since you last looked": the time this overview was opened before, more than half an hour ago */
async function lastLook() {
  const [last, prev] = await Promise.all([kv<string | null>("GET", "admin:seen:last").catch(() => null), kv<string | null>("GET", "admin:seen:prev").catch(() => null)]);
  const now = Date.now();
  if (!last || now - Number(last) > 30 * 60_000) {
    if (last) await kv("SET", "admin:seen:prev", last).catch(() => {});
    await kv("SET", "admin:seen:last", String(now)).catch(() => {});
    return last ? Number(last) : null;
  }
  return prev ? Number(prev) : null;
}

/** the overview: what needs you, how the period went against the one before, the way to a sale, the days */
export default async function Overview({ searchParams }: { searchParams: Promise<{ p?: string }> }) {
  await requireAdmin();
  const p = await pickPeriod((await searchParams).p);
  const chartFrom = Math.max(p.from, Date.now() - 89 * 86400_000);
  const [d, checks, count, f, fBefore, perDay, seen] = await Promise.all([
    periodData(p), health(false, true), liveCount(), funnelBetween(p.from, p.to),
    p.prev ? funnelBetween(p.prev.from, p.prev.to) : Promise.resolve(null), peoplePerDay(chartFrom, p.to), lastLook(),
  ]);
  const since = seen ? await sinceThen(seen) : null;
  const sinceOrders = seen ? d.orders.filter((o) => o.paidAt && Date.parse(o.paidAt) >= seen && o.stage !== "cancelled").length : 0;
  const issues = problems(checks).filter((c) => c.key !== "open");
  const n = Math.max(1, Math.ceil((p.to - chartFrom) / 86400_000));
  const days = Array.from({ length: n }, (_, i) => {
    const k = day(p.to - 1 - (n - 1 - i) * 86400_000);
    return { day: k, people: perDay.get(k) ?? 0, orders: d.byDay.get(k) ?? 0 };
  });
  const word = p.prev?.word ?? "";
  const rate = f.people ? Math.round((f.paid / f.people) * 1000) / 10 : 0;

  return (
    <>
      <Page title="overview" sub={since
        ? <>since you last looked, {when(seen!)}: <span className="text-ink">{since.people} {since.people === 1 ? "person" : "people"}, {since.bags} put in the bag, {sinceOrders} order{sinceOrders === 1 ? "" : "s"}</span>{count.now ? <>. <span className="text-ink">{count.now} on the site now</span></> : null}</>
        : count.now ? `${count.now} on the site now` : "how the shop is doing"} />

      {issues.length || d.needs.length ? (
        <Section title="needs you">
          <Group>
            {issues.map((c) => <Row key={c.key} icon={ICON[c.key] ?? "alert"} tone={c.tone === "bad" ? "bad" : "warn"} title={`${c.name}: ${c.state}`} sub={c.fix ?? c.detail} href="/admin/status" />)}
            {d.needs.map((x, i) => <Row key={i} icon={x.level === "now" ? "alert" : "clock"} tone={x.level === "now" ? "warn" : "quiet"} title={x.title} sub={x.detail} href={x.href} />)}
          </Group>
        </Section>
      ) : null}

      <PeriodTabs p={p} />


      <div className="mb-10 grid grid-cols-2 gap-3 md:mb-12 lg:grid-cols-4">
        <Tile label="people" icon="visitors" value={f.people} delta={fBefore ? { now: f.people, was: fBefore.people, word } : undefined} sub={`${f.returning} came back`} href="/admin/insights" />
        <Tile label="orders" icon="orders" value={d.now.orders} delta={d.before ? { now: d.now.orders, was: d.before.orders, word } : undefined} sub={`${d.now.shirts} shirt${d.now.shirts === 1 ? "" : "s"}${d.now.cancelled ? `, ${d.now.cancelled} cancelled` : ""}`} href="/admin/orders" />
        <Tile label="sales" icon="money" value={inr(d.now.revenue)} delta={d.before ? { now: d.now.revenue, was: d.before.revenue, word, money: true } : undefined} sub={d.now.refunds ? `${inr(d.now.refunded)} refunded` : undefined} href="/admin/money" />
        <Tile label="you keep" icon="chart" value={inr(d.now.margin)} sub={`after qikink, fees and post${d.now.estimated ? ", fees estimated" : ""}`} href="/admin/money" />
      </div>

      <div className="grid gap-x-6 lg:grid-cols-[1fr_1.25fr]">
        <Section title="the way to a sale" aside={<A href="/admin/insights?v=shirts">each shirt →</A>}>
          <Card>
            <Funnel steps={[["came to the site", f.people], ["looked at a shirt", f.shirt], ["put one in the bag", f.bag], ["opened checkout", f.checkout], ["paid", f.paid]]} />
            <p className="mt-5 border-t border-line/40 pt-4 text-[13px] text-quiet">{f.people ? `${rate}% of the people who came bought.` : "nobody came in this time."} visits are kept 90 days.</p>
          </Card>
        </Section>
        <Section title={p.key === "all" && p.from < chartFrom ? "the last 90 days" : `${p.label}, day by day`} aside={<A href="/admin/visitors">every visit →</A>}>
          <Card><DayChart days={days} /></Card>
        </Section>
      </div>
    </>
  );
}
