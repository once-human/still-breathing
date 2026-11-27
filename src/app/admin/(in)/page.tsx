import { requireAdmin } from "@/lib/admin/auth";
import { periodData } from "@/lib/admin/data";
import { health, problems } from "@/lib/admin/health";
import { kv } from "@/lib/shop/kv";
import { funnelBetween, liveCount, peoplePerDay, sinceThen } from "@/lib/visits/server";
import type { IconName } from "../ui/icons";
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

/** people a day as grey bars; a day an order came is drawn in cream with a dot over it */
function Chart({ days }: { days: { day: string; people: number; orders: number }[] }) {
  const max = Math.max(1, ...days.map((d) => d.people));
  const fmt = (d: string) => new Date(`${d}T12:00:00+05:30`).toLocaleDateString("en-IN", { day: "numeric", month: "short" }).toLowerCase();
  return (
    <div>
      <div className="flex h-44 items-end gap-[3px] md:h-52" role="img" aria-label="people a day, with the days an order came">
        {days.map((d) => (
          <div key={d.day} className="group relative flex h-full flex-1 flex-col justify-end" title={`${fmt(d.day)}: ${d.people} people${d.orders ? `, ${d.orders} order${d.orders > 1 ? "s" : ""}` : ""}`}>
            {d.orders ? <span className="absolute inset-x-0 top-0 mx-auto h-1.5 w-1.5 rounded-full bg-ink" /> : null}
            <div className={`w-full rounded-[4px] transition-colors ${d.orders ? "bg-ink/70" : "bg-s3 group-hover:bg-ink/35"}`} style={{ height: `${(d.people / max) * 88}%`, minHeight: 3 }} />
          </div>
        ))}
      </div>
      <div className="mt-3 flex justify-between text-[13px] text-quiet">
        <span>{fmt(days[0].day)}</span>
        <span className="hidden items-center gap-1.5 sm:flex"><span className="h-1.5 w-1.5 rounded-full bg-ink" />a day an order came</span>
        <span>today</span>
      </div>
    </div>
  );
}

/** the way to a sale: each step as a bar against everyone who came, and how many went no further */
function Way({ f }: { f: Awaited<ReturnType<typeof funnelBetween>> }) {
  const steps: [string, number][] = [["came to the site", f.people], ["looked at a shirt", f.shirt], ["put one in the bag", f.bag], ["opened checkout", f.checkout], ["paid", f.paid]];
  const top = Math.max(1, f.people);
  return (
    <div className="grid gap-4">
      {steps.map(([label, n], i) => {
        const lost = i ? steps[i - 1][1] - n : 0;
        return (
          <div key={label}>
            <div className="flex items-baseline justify-between gap-4 text-[15px]">
              <span>{label}</span>
              <span className="tnum"><span className="font-semibold">{n}</span>{i && f.people ? <span className="ml-2 text-[13px] text-quiet">{Math.round((n / top) * 100)}%</span> : null}</span>
            </div>
            <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-s3"><div className="h-full rounded-full bg-ink/75" style={{ width: `${Math.max(n ? 2 : 0, (n / top) * 100)}%` }} /></div>
            {lost > 0 ? <div className="mt-1 text-[13px] text-quiet">{lost} stopped here</div> : null}
          </div>
        );
      })}
    </div>
  );
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
    const k = day(p.to - (n - 1 - i) * 86400_000);
    return { day: k, people: perDay.get(k) ?? 0, orders: d.byDay.get(k) ?? 0 };
  });
  const word = p.prev?.word ?? "";
  const rate = f.people ? Math.round((f.paid / f.people) * 1000) / 10 : 0;

  return (
    <>
      <Page title="overview" sub={since
        ? <>since you last looked, {when(seen!)}: <span className="text-ink">{since.people} {since.people === 1 ? "person" : "people"}, {since.bags} put in the bag, {sinceOrders} order{sinceOrders === 1 ? "" : "s"}</span>{count.now ? <>. <span className="text-ink">{count.now} on the site now</span></> : null}</>
        : count.now ? `${count.now} on the site now` : "how the shop is doing"} />

      <PeriodTabs p={p} />

      {issues.length || d.needs.length ? (
        <Section title="needs you">
          <Group>
            {issues.map((c) => <Row key={c.key} icon={ICON[c.key] ?? "alert"} tone={c.tone === "bad" ? "bad" : "warn"} title={`${c.name}: ${c.state}`} sub={c.fix ?? c.detail} href="/admin/status" />)}
            {d.needs.map((x, i) => <Row key={i} icon={x.level === "now" ? "alert" : "clock"} tone={x.level === "now" ? "warn" : "quiet"} title={x.title} sub={x.detail} href={x.href} />)}
          </Group>
        </Section>
      ) : null}

      <div className="mb-10 grid grid-cols-2 gap-3 md:mb-12 lg:grid-cols-4">
        <Tile label="people" icon="visitors" value={f.people} delta={fBefore ? { now: f.people, was: fBefore.people, word } : undefined} sub={`${f.returning} came back`} href="/admin/insights" />
        <Tile label="orders" icon="orders" value={d.now.orders} delta={d.before ? { now: d.now.orders, was: d.before.orders, word } : undefined} sub={`${d.now.shirts} shirt${d.now.shirts === 1 ? "" : "s"}${d.now.cancelled ? `, ${d.now.cancelled} cancelled` : ""}`} href="/admin/orders" />
        <Tile label="sales" icon="money" value={inr(d.now.revenue)} delta={d.before ? { now: d.now.revenue, was: d.before.revenue, word, money: true } : undefined} sub={d.now.refunds ? `${inr(d.now.refunded)} refunded` : undefined} href="/admin/money" />
        <Tile label="you keep" icon="chart" value={inr(d.now.margin)} sub={`after qikink, fees and post${d.now.estimated ? ", fees estimated" : ""}`} href="/admin/money" />
      </div>

      <div className="grid gap-x-6 lg:grid-cols-[1fr_1.25fr]">
        <Section title="the way to a sale" aside={<A href="/admin/insights">each shirt →</A>}>
          <Card>
            <Way f={f} />
            <p className="mt-5 border-t border-line/40 pt-4 text-[13px] text-quiet">{f.people ? `${rate}% of the people who came bought.` : "nobody came in this time."} visits are kept 90 days.</p>
          </Card>
        </Section>
        <Section title={p.key === "all" && p.from < chartFrom ? "the last 90 days" : `${p.label}, day by day`} aside={<A href="/admin/visitors">every visit →</A>}>
          <Card><Chart days={days} /></Card>
        </Section>
      </div>
    </>
  );
}
