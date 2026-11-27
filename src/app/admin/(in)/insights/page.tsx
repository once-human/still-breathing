import Link from "next/link";
import { requireAdmin } from "@/lib/admin/auth";
import { allOrders, isPaid, istDay } from "@/lib/admin/data";
import { summary, type Count } from "@/lib/visits/server";
import { span } from "@/lib/visits/shared";
import { DayChart, Funnel } from "../../ui/charts";
import { A, Bars, Card, Group, Page, Row, Section, Table, Tabs, Tile } from "../../ui/ui";
import { pageName, shirtLabel } from "../../ui/visits";
import { PeriodTabs, pickPeriod } from "../period";

export const metadata = { title: "insights" };
export const dynamic = "force-dynamic";

const pct = (n: number, of: number) => (of ? `${Math.round((n / of) * 1000) / 10}%` : "–");
const VIEWS = [["", "summary"], ["shirts", "shirts"], ["pages", "pages"], ["sources", "where from"], ["days", "day by day"], ["programs", "programs"]] as const;
const STEPS = [["saw", "saw it"], ["size", "picked a size"], ["look", "turned it"], ["tryon", "tried it on"], ["bag", "bagged"], ["checkout", "checkout"], ["pay", "payment"], ["paid", "paid"]] as const;

const top = (rows: Count[], label?: (k: string) => string) => rows.map((r) => ({ key: r.key, label: label ? label(r.key) : r.key, n: r.people, sub: `${r.visits} visit${r.visits === 1 ? "" : "s"}` }));

/**
 * insights: what people do on the site over a period, a part at a time: the summary (the way to a sale, each day),
 * each shirt step by step, pages, where people come from, every day as numbers, and the programs that came by.
 * Counted on this site only: no cookies, no outside trackers, no IP addresses. Visits are kept 90 days.
 */
export default async function Insights({ searchParams }: { searchParams: Promise<{ p?: string; v?: string }> }) {
  await requireAdmin();
  const sp = await searchParams;
  const p = await pickPeriod(sp.p);
  const view = VIEWS.find(([k]) => k === sp.v)?.[0] ?? "";
  const days = Math.max(1, Math.min(90, Math.ceil((p.to - p.from) / 86400_000)));
  const [a, orders] = await Promise.all([summary(days), allOrders()]);
  const from = Date.now() - (days - 1) * 86400_000;
  const paidByDay = new Map<string, number>();
  for (const o of orders) if (isPaid(o) && o.stage !== "cancelled" && Date.parse(o.paidAt!) >= from - 86400_000) paidByDay.set(istDay(o.paidAt!), (paidByDay.get(istDay(o.paidAt!)) ?? 0) + 1);
  const perDay = new Map(a.perDay.map((d) => [d.day, d]));
  const folded = new Map(a.folded.map((d) => [d.day, d.people]));
  const series = Array.from({ length: days }, (_, i) => {
    const day = new Date(from + i * 86400_000 + 5.5 * 3600_000).toISOString().slice(0, 10);
    const r = perDay.get(day);
    return { day, people: r?.people ?? folded.get(day) ?? 0, visits: r?.visits ?? 0, pages: r?.pages ?? 0, bag: r?.bag ?? 0, checkout: r?.checkout ?? 0, orders: paidByDay.get(day) ?? 0 };
  });
  const t = a.totals;
  const orderCount = series.reduce((n, d) => n + d.orders, 0);
  const href = (v: string) => "?" + new URLSearchParams(Object.entries({ p: sp.p, v }).filter(([, x]) => x) as [string, string][]).toString();

  return (
    <>
      <Page title="insights" sub={`${days === 90 && p.key === "all" ? "the kept 90 days" : p.label}: counted on this site only, no cookies, no outside trackers, each person once`} />
      <div className="mb-5 flex flex-wrap gap-x-3 [&>nav]:mb-3">
        <Tabs active={view} items={VIEWS.map(([k, l]) => ({ key: k, label: l, href: href(k) }))} />
        <PeriodTabs p={p} keep={{ v: view || undefined }} />
      </div>

      {view === "" ? (
        <>
          <div className="mb-10 grid grid-cols-2 gap-3 md:mb-12 lg:grid-cols-4">
            <Tile label="people" icon="visitors" value={t.people} sub={`${t.visits} visit${t.visits === 1 ? "" : "s"}`} />
            <Tile label="came back" icon="return" value={t.returning} sub={pct(t.returning, t.people) + " of people"} />
            <Tile label="on screen" icon="clock" value={span(t.active)} sub="a visit, on average" />
            <Tile label="pages" icon="list" value={t.visits ? Math.round((t.pages / t.visits) * 10) / 10 : 0} sub="a visit, on average" />
          </div>
          <div className="grid gap-x-6 lg:grid-cols-[1fr_1.25fr]">
            <Section title="the way to a sale" aside={<A href={href("shirts")}>each shirt →</A>}>
              <Card>
                <Funnel steps={[["came to the site", t.people], ["looked at a shirt", t.shirt], ["put one in the bag", t.bag], ["opened checkout", t.checkout], ["opened payment", t.pay], ["paid", t.paid]]} />
                <p className="mt-5 border-t border-line/40 pt-4 text-[13px] text-quiet">{orderCount} paid order{orderCount === 1 ? "" : "s"} in this time; a person who paid in two visits counts once.</p>
              </Card>
            </Section>
            <Section title="day by day" aside={<A href={href("days")}>as numbers →</A>}>
              <Card><DayChart days={series} /></Card>
            </Section>
          </div>
          <div className="grid gap-x-6 lg:grid-cols-2">
            <Section title="where they came from" aside={<A href={href("sources")}>all →</A>}><Bars rows={top(a.referrers.slice(0, 6))} /></Section>
            <Section title="most read pages" aside={<A href={href("pages")}>all →</A>}>
              <Bars rows={a.pages.slice(0, 6).map((x) => ({ key: x.key, label: pageName(x.key), n: x.views, sub: "views" }))} />
            </Section>
          </div>
        </>
      ) : null}

      {view === "shirts" ? (
        <>
          <Section title="each shirt, step by step" aside="people who did each step, and the share of those who saw it">
            <Table head={["shirt", ...STEPS.map(([, l]) => l)]} empty="no shirt looked at yet">
              {a.funnel.map((f) => (
                <tr key={f.design}>
                  <td className="font-medium">{shirtLabel(f.design)}</td>
                  {STEPS.map(([k]) => {
                    const n = k === "bag" ? Math.max(f.bag, f.buy) : f[k];
                    return <td key={k} className={`tnum ${k === "paid" && n ? "font-semibold" : n ? "" : "text-quiet"}`}>{n}{k !== "saw" && n ? <span className="ml-1 text-[12px] text-quiet">{pct(n, f.saw)}</span> : null}</td>;
                  })}
                </tr>
              ))}
            </Table>
          </Section>
          <Section title="put in the bag" aside="by shirt and size">
            <Bars rows={a.bag.map((b) => ({ key: `${b.design}-${b.size}`, label: `${shirtLabel(b.design)} ${b.size ?? ""}`, n: b.n, sub: "times" }))} empty="nothing bagged yet" />
          </Section>
        </>
      ) : null}

      {view === "pages" ? (
        <Section title="pages" aside="views, people, time on screen and how far down they read">
          <Table head={["page", "views", "people", "on screen", "read"]} empty="no pages yet">
            {a.pages.map((x) => (
              <tr key={x.key}>
                <td><span className="font-medium">{pageName(x.key)}</span> <span className="text-[12px] text-quiet">{x.key}</span></td>
                <td className="tnum">{x.views}</td>
                <td className="tnum">{x.people}</td>
                <td className="tnum text-quiet">{span(x.ms)}</td>
                <td className="tnum"><span className="inline-block h-1.5 w-16 overflow-hidden rounded-full bg-s3 align-middle"><span className="block h-full bg-ink/60" style={{ width: `${Math.min(100, x.scroll)}%` }} /></span> <span className="text-[12px] text-quiet">{x.scroll}%</span></td>
              </tr>
            ))}
          </Table>
        </Section>
      ) : null}

      {view === "sources" ? (
        <div className="grid gap-x-6 lg:grid-cols-2">
          <Section title="where they came from"><Bars rows={top(a.referrers)} /></Section>
          <Section title="where they are"><Bars rows={top(a.places)} /></Section>
          <Section title="devices"><Bars rows={top(a.devices)} /></Section>
          <Section title="languages"><Bars rows={top(a.langs)} /></Section>
          <Section title="screens" aside="the most common sizes"><Bars rows={top(a.screens)} /></Section>
        </div>
      ) : null}

      {view === "days" ? (
        <Section title="every day" aside="people, then how many of them got to each step">
          <Table head={["day", "people", "visits", "pages", "bag", "checkout", "orders"]}>
            {[...series].reverse().map((d) => (
              <tr key={d.day}>
                <td className="tnum whitespace-nowrap">{new Date(`${d.day}T12:00:00+05:30`).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" }).toLowerCase()}</td>
                <td className="tnum">{d.people}</td>
                <td className="tnum text-quiet">{d.visits}</td>
                <td className="tnum text-quiet">{d.pages}</td>
                <td className="tnum">{d.bag || ""}</td>
                <td className="tnum">{d.checkout || ""}</td>
                <td className="tnum font-semibold">{d.orders || ""}</td>
              </tr>
            ))}
          </Table>
        </Section>
      ) : null}

      {view === "programs" ? (
        <Section title="programs that came by" aside={<Link href="/admin/visitors?tab=bots" className="underline decoration-ink/25 underline-offset-4 hover:text-ink">every visit →</Link>}>
          {a.bots.length ? (
            <Group>
              {a.bots.map((b) => <Row key={b.name} icon="bot" title={b.name} sub={`${b.pages} page${b.pages === 1 ? "" : "s"} over ${b.days} day${b.days === 1 ? "" : "s"}`}
                right={<span className="text-[13px] text-quiet">{new Date(b.last).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).toLowerCase()}</span>} />)}
            </Group>
          ) : <p className="rounded-[22px] bg-s1 px-5 py-10 text-center text-[15px] text-quiet">no programs or link previews</p>}
        </Section>
      ) : null}
    </>
  );
}
