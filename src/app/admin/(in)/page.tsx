import { requireAdmin } from "@/lib/admin/auth";
import { overview, shirtName, type Totals } from "@/lib/admin/data";
import { health, problems } from "@/lib/admin/health";
import { refunded } from "@/lib/shop/orders";
import { dailyPeople, liveCount, liveNow } from "@/lib/visits/server";
import type { IconName } from "../ui/icons";
import { A, Avatar, Card, Group, Page, Row, Section, StageBadge, Tile, ago, inr } from "../ui/ui";
import { pageName, where } from "../ui/visits";

export const metadata = { title: "home" };
export const dynamic = "force-dynamic";

const IST = 5.5 * 3600_000;
const ICON: Record<string, IconName> = { open: "shop", pay: "card", print: "print", sync: "truck", db: "shield", mail: "mail", alerts: "alert", secret: "key", admin: "user" };

function hello() {
  const h = new Date(Date.now() + IST).getUTCHours();
  return h < 5 ? "up late" : h < 12 ? "good morning" : h < 17 ? "good afternoon" : "good evening";
}
const today = () => new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", timeZone: "Asia/Kolkata" }).toLowerCase();

/** the last 30 days: people as grey bars, paid orders in blue on top of them */
function Chart({ days }: { days: { day: string; people: number; orders: number }[] }) {
  const max = Math.max(1, ...days.map((d) => d.people), ...days.map((d) => d.orders));
  return (
    <div>
      <div className="flex h-44 items-end gap-[3px] md:h-56" role="img" aria-label="people and paid orders a day, the last 30 days">
        {days.map((d) => (
          <div key={d.day} className="group relative flex h-full flex-1 flex-col justify-end" title={`${d.day.slice(5)}: ${d.people} people, ${d.orders} orders`}>
            <div className="w-full rounded-[4px] bg-s3 transition-colors group-hover:bg-ink/40" style={{ height: `${(d.people / max) * 100}%`, minHeight: d.people ? 4 : 2 }} />
            {d.orders ? <div className="absolute inset-x-0 bottom-0 rounded-[4px] bg-ink/80" style={{ height: `${(d.orders / max) * 100}%`, minHeight: 6 }} /> : null}
          </div>
        ))}
      </div>
      <div className="mt-3 flex justify-between text-[13px] text-quiet">
        <span>{new Date(`${days[0]?.day}T12:00:00+05:30`).toLocaleDateString("en-IN", { day: "numeric", month: "short" }).toLowerCase()}</span>
        <span className="flex items-center gap-4"><span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-[3px] bg-s3" />people</span><span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-[3px] bg-ink/80" />orders</span></span>
        <span>today</span>
      </div>
    </div>
  );
}

const line = (t: Totals) => `${t.orders} order${t.orders === 1 ? "" : "s"} · margin ${inr(t.margin)}${t.cancelled ? ` · ${t.cancelled} cancelled` : ""}${t.refunds ? ` · ${inr(t.refunded)} refunded` : ""}`;

/** the one screen to check every day: what needs you, how today went, who's here */
export default async function Home() {
  await requireAdmin();
  const [{ orders, totals: t, byDay, needs, settings }, checks, count, live, people] = await Promise.all([
    overview(), health(false, true), liveCount(), liveNow().catch(() => []), dailyPeople(30),
  ]);
  // the shop's own switch is at the top right already, so it isn't repeated here
  const issues = problems(checks).filter((c) => c.key !== "open");
  const recent = orders.filter((o) => o.stage !== "paying").slice(0, 5);
  const days = Array.from({ length: 30 }, (_, i) => {
    const day = new Date(Date.now() + IST - (29 - i) * 86400_000).toISOString().slice(0, 10);
    return { day, people: people.get(day) ?? 0, orders: byDay.get(day)?.orders ?? 0 };
  });
  const month = days.reduce((a, d) => ({ people: a.people + d.people, orders: a.orders + d.orders }), { people: 0, orders: 0 });

  return (
    <>
      <Page title={hello()} sub={today()} />

      {issues.length || needs.length ? (
        <Section title="needs you" aside={`${issues.length + needs.length}`}>
          <Group>
            {issues.map((c) => <Row key={c.key} icon={ICON[c.key] ?? "alert"} tone={c.tone === "bad" ? "bad" : "warn"} title={`${c.name}: ${c.state}`} sub={c.fix ?? c.detail} href="/admin/status" />)}
            {needs.map((n, i) => <Row key={i} icon={n.level === "now" ? "alert" : "clock"} tone={n.level === "now" ? "warn" : "quiet"} title={n.title} sub={n.detail} href={n.href} />)}
          </Group>
        </Section>
      ) : null}

      <div className="mb-10 grid grid-cols-2 gap-3 md:mb-12 lg:grid-cols-4">
        <Tile label="sales today" icon="money" value={inr(t.today.revenue)} delta={{ now: t.today.revenue, was: t.yesterday.revenue, money: true }} href="/admin/orders" />
        <Tile label="orders today" icon="orders" value={t.today.orders} delta={{ now: t.today.orders, was: t.yesterday.orders }} href="/admin/orders" />
        <Tile label="people today" icon="visitors" value={count.today} delta={{ now: count.today, was: count.yesterday }} sub={count.now ? <span className="text-ok">{count.now} here now</span> : undefined} href="/admin/visitors" />
        <Tile label="margin today" icon="chart" tone="blue" value={inr(t.today.margin)} sub={t.today.estimated ? "fees estimated" : "after every cost"} />
      </div>

      <Section title="the last 30 days" aside={`${month.people} people · ${month.orders} orders`}>
        <Card><Chart days={days} /></Card>
      </Section>

      <div className="grid gap-x-6 lg:grid-cols-2">
        <Section title="latest orders" aside={<A href="/admin/orders">all orders →</A>}>
          {recent.length ? (
            <Group>
              {recent.map((o) => {
                const back = refunded(o);
                return (
                  <Row key={o.id} href={`/admin/orders/${o.id}`} icon={undefined}
                    title={<span className="flex items-center gap-3"><Avatar name={o.contact.name} /><span className="min-w-0"><span className={`block truncate ${o.stage === "cancelled" ? "text-quiet line-through" : ""}`}>{o.contact.name.toLowerCase()}, {o.ship.city.toLowerCase()}</span>
                      <span className="block truncate text-[13px] text-quiet">{o.lines.map((l) => `${shirtName(l.design)} ${l.size}${l.quantity > 1 ? ` ×${l.quantity}` : ""}`).join(", ")} · {ago(o.paidAt ?? o.createdAt)}</span></span></span>}
                    right={<span className="grid justify-items-end gap-1.5"><span className="tnum">{inr(o.total)}</span>{back > 0 ? <span className="text-[12.5px] text-warn">{inr(back)} back</span> : <StageBadge stage={o.stage} />}</span>} />
                );
              })}
            </Group>
          ) : <Card><p className="text-[15px] text-quiet">no orders yet. the first one shows here the moment it's paid.</p></Card>}
        </Section>

        <Section title="on the site now" aside={<A href="/admin/visitors">everyone →</A>}>
          {live.length ? (
            <Group>
              {live.slice(0, 5).map((v) => (
                <Row key={v.id} href={`/admin/visitors/${v.id}`} icon={/phone|iphone|android/i.test(v.device ?? "") ? "phone" : "desktop"} tone="ok"
                  title={<>on {pageName(v.now)}</>} sub={`${where(v)} · ${(v.device ?? "").toLowerCase()} · from ${v.referrer ?? "direct"}`}
                  right={v.bag.length ? <span className="text-[13px] text-ink">{v.bag.reduce((n, b) => n + b.n, 0)} in bag</span> : undefined} />
              ))}
            </Group>
          ) : <Card><p className="text-[15px] text-quiet">nobody right now. {count.hour ? `${count.hour} ${count.hour === 1 ? "person" : "people"} in the last hour.` : "this fills in the moment someone opens a page."}</p></Card>}
        </Section>
      </div>

      <Section title="money">
        <Group>
          <Row icon="money" title="this week" sub={line(t.week)} right={<span className="tnum font-semibold">{inr(t.week.revenue)}</span>} />
          <Row icon="chart" title="all time" sub={line(t.all)} right={<span className="tnum font-semibold">{inr(t.all.revenue)}</span>} />
          <Row icon="card" title="qikink wallet" sub={`their API has no balance, so it isn't shown. keep at least ${inr(settings.lowWallet)} in it; a low wallet shows under needs you.`} href="https://qikink.com" external />
        </Group>
      </Section>
    </>
  );
}
