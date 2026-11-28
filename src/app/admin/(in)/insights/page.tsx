import Link from "next/link";
import { requireAdmin } from "@/lib/admin/auth";
import { allOrders, isPaid, istDay } from "@/lib/admin/data";
import { deeper, summary, type Count } from "@/lib/visits/server";
import { KEEP_DAYS, span } from "@/lib/visits/shared";
import { DayChart, Funnel } from "../../ui/charts";
import { A, Bars, Card, Group, Page, Row, Section, Table, Tabs, Tile } from "../../ui/ui";
import { pageName, shirtLabel } from "../../ui/visits";
import { PeriodTabs, pickPeriod } from "../period";

export const metadata = { title: "insights" };
export const dynamic = "force-dynamic";

const pct = (n: number, of: number) => (of ? `${Math.round((n / of) * 1000) / 10}%` : "–");
const VIEWS = [
  ["", "summary"], ["shirts", "shirts"], ["ads", "ads and links"], ["pages", "pages"], ["taps", "taps and forms"], ["speed", "speed"], ["problems", "problems"],
  ["sources", "where from"], ["days", "day by day"], ["programs", "programs"],
] as const;
const DEEP = new Set(["ads", "taps", "speed", "problems", "sources"]);
const rs = (n: number) => `₹${n.toLocaleString("en-IN")}`;
/** how fast, as people feel it: the 75th slowest of every 100 (Google's own line for good is under each limit) */
const LIMIT: Record<string, number> = { LCP: 2500, INP: 200, CLS: 0.1, FCP: 1800, TTFB: 800 };
const VITAL_WORD: Record<string, string> = { LCP: "main picture shown", INP: "answer to a tap", CLS: "page jumping about", FCP: "first thing shown", TTFB: "server's first byte" };
const speed = (metric: string, v: number | null) => (v == null ? "–" : metric.startsWith("CLS") ? v.toFixed(2) : v >= 1000 ? `${(v / 1000).toFixed(1)} s` : `${Math.round(v)} ms`);
const tone = (metric: string, v: number | null) => (v == null ? "text-quiet" : v <= LIMIT[metric]! ? "" : v <= LIMIT[metric]! * 1.6 ? "text-warn" : "text-bad font-semibold");
const STEPS = [["saw", "saw it"], ["size", "picked a size"], ["look", "turned it"], ["tryon", "tried it on"], ["bag", "bagged"], ["checkout", "checkout"], ["pay", "payment"], ["paid", "paid"]] as const;

const top = (rows: Count[], label?: (k: string) => string) => rows.map((r) => ({ key: r.key, label: label ? label(r.key) : r.key, n: r.people, sub: `${r.visits} visit${r.visits === 1 ? "" : "s"}` }));

/**
 * insights: what people do on the site over a period, a part at a time: the summary (the way to a sale, each day),
 * each shirt step by step, ads and links (what each campaign brought in), pages, taps and forms, speed, what broke,
 * where people come from, every day as numbers, and the programs that came by. Counted on this site only: no cookies,
 * no outside trackers, no IP addresses. Visits are kept KEEP_DAYS days in full.
 */
export default async function Insights({ searchParams }: { searchParams: Promise<{ p?: string; v?: string }> }) {
  await requireAdmin();
  const sp = await searchParams;
  const p = await pickPeriod(sp.p);
  const view = VIEWS.find(([k]) => k === sp.v)?.[0] ?? "";
  // the log keeps KEEP_DAYS in full, so all time reads from there
  const from = Math.max(p.from, Date.now() - (KEEP_DAYS - 1) * 86400_000);
  const days = Math.max(1, Math.ceil((p.to - from) / 86400_000));
  const [a, orders, d] = await Promise.all([summary({ from, to: p.to }), allOrders(), DEEP.has(view) ? deeper({ from, to: p.to }).catch((e) => (console.error("insights", e), null)) : null]);
  const paidByDay = new Map<string, number>();
  for (const o of orders) {
    const at = isPaid(o) && o.stage !== "cancelled" ? Date.parse(o.paidAt!) : NaN;
    if (at >= from && at < p.to) paidByDay.set(istDay(o.paidAt!), (paidByDay.get(istDay(o.paidAt!)) ?? 0) + 1);
  }
  const perDay = new Map(a.perDay.map((d) => [d.day, d]));
  const folded = new Map(a.folded.map((d) => [d.day, d.people]));
  const series = Array.from({ length: days }, (_, i) => {
    const day = new Date(from + i * 86400_000 + 5.5 * 3600_000).toISOString().slice(0, 10); // from is midnight, or the oldest kept day
    const r = perDay.get(day);
    return { day, people: r?.people ?? folded.get(day) ?? 0, visits: r?.visits ?? 0, pages: r?.pages ?? 0, bag: r?.bag ?? 0, checkout: r?.checkout ?? 0, orders: paidByDay.get(day) ?? 0 };
  });
  const t = a.totals;
  const orderCount = series.reduce((n, d) => n + d.orders, 0);
  const href = (v: string) => "?" + new URLSearchParams(Object.entries({ p: sp.p, v }).filter(([, x]) => x) as [string, string][]).toString();

  return (
    <>
      <Page title="insights" sub={`${from > p.from ? `the kept ${KEEP_DAYS} days` : p.label}: counted on this site only, no cookies, no outside trackers, each person once`} />
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
          <Section title="day by day" aside={<A href={href("days")}>as numbers →</A>}>
            <Card><DayChart days={series} /></Card>
          </Section>
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
          <Section title="the way to a sale" aside="everyone, then each shirt below">
            <Card>
              <Funnel steps={[["came to the site", t.people], ["looked at a shirt", t.shirt], ["put one in the bag", t.bag], ["opened checkout", t.checkout], ["opened payment", t.pay], ["paid", t.paid]]} />
              <p className="mt-5 border-t border-line/40 pt-4 text-[13px] text-quiet">{orderCount} paid order{orderCount === 1 ? "" : "s"} in this time; a person who paid in two visits counts once.</p>
            </Card>
          </Section>
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

      {DEEP.has(view) && !d ? <p className="mb-6 rounded-[14px] bg-s1 px-5 py-4 text-[14px] text-quiet">these numbers couldn&apos;t be read just now; try again in a minute.</p> : null}

      {view === "ads" && d ? (
        <>
          <Section title="every link and campaign" aside="tag ad links ?utm_source=…&utm_campaign=…; each person counted once">
            <Table head={["from", "campaign", "people", "saw a shirt", "bagged", "checkout", "paid", "brought in"]} empty="no visits yet">
              {d.campaigns.map((c) => (
                <tr key={`${c.source}|${c.campaign}|${c.content}|${c.via}`}>
                  <td><span className="font-medium">{c.source}</span>{c.via ? <span className="ml-1.5 text-[12px] text-quiet">via {c.via}</span> : null}</td>
                  <td className="text-[13px]">{c.campaign || <span className="text-quiet">–</span>}{c.content ? <span className="ml-1.5 text-[12px] text-quiet">{c.content}</span> : null}</td>
                  <td className="tnum">{c.people}<span className="ml-1 text-[12px] text-quiet">{c.visits} visit{c.visits === 1 ? "" : "s"}</span></td>
                  <td className="tnum">{c.shirt || ""}{c.shirt ? <span className="ml-1 text-[12px] text-quiet">{pct(c.shirt, c.people)}</span> : null}</td>
                  <td className="tnum">{c.bag || ""}{c.bag ? <span className="ml-1 text-[12px] text-quiet">{pct(c.bag, c.people)}</span> : null}</td>
                  <td className="tnum">{c.checkout || ""}</td>
                  <td className="tnum font-semibold">{c.paid || ""}{c.paid ? <span className="ml-1 text-[12px] font-normal text-quiet">{pct(c.paid, c.people)}</span> : null}</td>
                  <td className="tnum">{c.rupees ? rs(c.rupees) : ""}</td>
                </tr>
              ))}
            </Table>
          </Section>
          <Section title="where buyers first came from" aside="their first visit in the log, even if they paid on a later one">
            <Table head={["first from", "campaign", "orders", "brought in", "first visit to paying"]} empty="no orders in this time">
              {d.firstTouch.map((f) => (
                <tr key={`${f.source}|${f.campaign}`}>
                  <td className="font-medium">{f.source}</td>
                  <td className="text-[13px]">{f.campaign || <span className="text-quiet">–</span>}</td>
                  <td className="tnum">{f.orders}</td>
                  <td className="tnum font-semibold">{rs(f.rupees)}</td>
                  <td className="tnum text-quiet">{f.days < 1 / 24 ? "same visit" : f.days < 1 ? `${Math.round(f.days * 24)} h` : `${Math.round(f.days * 10) / 10} days`}</td>
                </tr>
              ))}
            </Table>
          </Section>
          <Section title="where they land" aside="the first page of a visit; left = one page, under 15 s">
            <Table head={["first page", "visits", "people", "left", "bagged", "paid"]} empty="no visits yet">
              {d.landing.map((l) => (
                <tr key={l.key}>
                  <td><span className="font-medium">{pageName(l.key)}</span> <span className="text-[12px] text-quiet">{l.key}</span></td>
                  <td className="tnum">{l.visits}</td>
                  <td className="tnum text-quiet">{l.people}</td>
                  <td className={`tnum ${l.left / Math.max(1, l.visits) > 0.6 ? "text-warn" : ""}`}>{pct(l.left, l.visits)}</td>
                  <td className="tnum">{l.bag || ""}</td>
                  <td className="tnum font-semibold">{l.paid || ""}</td>
                </tr>
              ))}
            </Table>
          </Section>
          <Section title="the hours they come" aside="india's time, when a visit starts">
            <Table head={["hour", "people", "bagged", "paid"]} empty="no visits yet">
              {d.hours.map((h) => {
                const max = Math.max(1, ...d.hours.map((x) => x.people));
                return (
                  <tr key={h.hour}>
                    <td className="tnum whitespace-nowrap">{`${h.hour % 12 || 12} ${h.hour < 12 ? "am" : "pm"}`}</td>
                    <td className="tnum"><span className="inline-block h-1.5 w-24 overflow-hidden rounded-full bg-s3 align-middle"><span className="block h-full bg-ink/60" style={{ width: `${(h.people / max) * 100}%` }} /></span> <span className="text-[12px]">{h.people}</span></td>
                    <td className="tnum">{h.bag || ""}</td>
                    <td className="tnum font-semibold">{h.paid || ""}</td>
                  </tr>
                );
              })}
            </Table>
          </Section>
        </>
      ) : null}

      {view === "taps" && d ? (
        <>
          <Section title="shirt cards: seen, then tapped" aside="a card counts as seen when half of it was on screen for a second">
            <Table head={["shirt", "saw the card", "tapped it", "of those who saw it"]} empty="no cards seen yet">
              {d.cards.map((c) => (
                <tr key={c.design}>
                  <td className="font-medium">{shirtLabel(c.design)}</td>
                  <td className="tnum">{c.seen}</td>
                  <td className="tnum">{c.tapped}</td>
                  <td className="tnum font-semibold">{pct(c.tapped, c.seen)}</td>
                </tr>
              ))}
            </Table>
          </Section>
          <div className="grid gap-x-6 lg:grid-cols-2">
            <Section title="what people tap" aside="buttons and links inside the site">
              <Bars rows={d.taps.map((t) => ({ key: `${t.path}|${t.key}`, label: <>{t.key} <span className="text-[12px] text-quiet">on {pageName(t.path)}</span></>, n: t.people, sub: `${t.n} tap${t.n === 1 ? "" : "s"}` }))} empty="no taps yet" />
            </Section>
            <Section title="what people really saw" aside="people who got to it, of those on the page">
              <Bars rows={d.seen.map((x) => ({ key: `${x.path}|${x.key}`, label: <>{x.key} <span className="text-[12px] text-quiet">on {pageName(x.path)}</span></>, n: x.people, sub: pct(x.people, x.of) }))} empty="nothing yet" />
            </Section>
          </div>
          <Section title="the form boxes" aside="people in each box, the time in it, and how often it was left empty; never what was typed">
            <Table head={["page", "box", "people", "time in it", "left empty"]} empty="no forms used yet">
              {d.fields.map((f) => (
                <tr key={`${f.path}|${f.key}`}>
                  <td className="text-[13px] text-quiet">{pageName(f.path)}</td>
                  <td className="font-medium">{f.key}</td>
                  <td className="tnum">{f.people}</td>
                  <td className="tnum text-quiet">{span(f.ms)}</td>
                  <td className={`tnum ${f.empty / Math.max(1, f.n) > 0.3 ? "text-warn" : ""}`}>{pct(f.empty, f.n)}</td>
                </tr>
              ))}
            </Table>
          </Section>
          <Section title="checkout: where they stopped" aside="the last box of each checkout that never reached payment">
            <Bars rows={d.stopped.map((x) => ({ key: x.key, label: x.key, n: x.n, sub: "checkouts" }))} empty="no checkout left early" />
          </Section>
        </>
      ) : null}

      {view === "speed" && d ? (
        <>
          <Section title="how fast it is for people" aside="the 75th slowest of every 100 visits; green under google's line for good">
            <Table head={["", "phone", "tablet", "desktop", "good"]} empty="no speeds yet: they come in as people visit">
              {["LCP", "INP", "CLS", "FCP", "TTFB"].map((m) => {
                const at = (sc: string) => d.vitals.find((v) => v.metric === m && v.screen === sc) ?? null;
                const all = d.vitals.filter((v) => v.metric === m);
                const n = all.reduce((x, v) => x + v.n, 0);
                if (!n) return null;
                return (
                  <tr key={m}>
                    <td><span className="font-medium">{VITAL_WORD[m]}</span> <span className="text-[12px] text-quiet">{m}</span></td>
                    {["phone", "tablet", "desktop"].map((sc) => {
                      const v = at(sc);
                      return <td key={sc} className={`tnum ${tone(m, v?.p75 ?? null)}`}>{speed(m, v?.p75 ?? null)}{v ? <span className="ml-1 text-[12px] font-normal text-quiet">{v.n}</span> : null}</td>;
                    })}
                    <td className="tnum">{pct(all.reduce((x, v) => x + v.good, 0), n)}</td>
                  </tr>
                );
              })}
            </Table>
          </Section>
          <Section title="each page" aside="the same line, page by page">
            <Table head={["page", "visits", "main picture", "tap answer", "jumping", "server"]} empty="no speeds yet">
              {d.vitalPages.map((v) => (
                <tr key={v.key}>
                  <td><span className="font-medium">{pageName(v.key)}</span> <span className="text-[12px] text-quiet">{v.key}</span></td>
                  <td className="tnum text-quiet">{v.visits}</td>
                  <td className={`tnum ${tone("LCP", v.lcp)}`}>{speed("LCP", v.lcp)}</td>
                  <td className={`tnum ${tone("INP", v.inp)}`}>{speed("INP", v.inp)}</td>
                  <td className={`tnum ${tone("CLS", v.cls)}`}>{speed("CLS", v.cls)}</td>
                  <td className={`tnum ${tone("TTFB", v.ttfb)}`}>{speed("TTFB", v.ttfb)}</td>
                </tr>
              ))}
            </Table>
          </Section>
        </>
      ) : null}

      {view === "problems" && d ? (
        <>
          <Section title="what broke for people" aside="errors on their screen and files that didn't load; the message only">
            <Table head={["what", "people", "times", "where", "last"]} empty="nothing broke">
              {d.errors.map((e) => (
                <tr key={e.key}>
                  <td className="max-w-[420px] break-words font-mono text-[12px]">{e.key}</td>
                  <td className="tnum font-semibold">{e.people}</td>
                  <td className="tnum text-quiet">{e.n}</td>
                  <td className="text-[12px] text-quiet">{(e.paths ?? []).map(pageName).join(", ")}</td>
                  <td className="tnum whitespace-nowrap text-[12px] text-quiet">{new Date(e.last).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" }).toLowerCase()}</td>
                </tr>
              ))}
            </Table>
          </Section>
          <Section title="tapped again and again" aside="three taps in a second on the same thing: it looked tappable, or didn't answer fast enough">
            <Bars rows={d.rage.map((r) => ({ key: `${r.path}|${r.key}`, label: <>{r.key} <span className="text-[12px] text-quiet">on {pageName(r.path)}</span></>, n: r.people, sub: `${r.n} time${r.n === 1 ? "" : "s"}` }))} empty="no one got stuck" />
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
          {d ? <Section title="window sizes" aside="width x height"><Bars rows={top(d.views)} /></Section> : null}
          {d ? <Section title="connections" aside="as the browser reports it; save = data saver on"><Bars rows={top(d.nets)} /></Section> : null}
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
          ) : <p className="rounded-[14px] bg-s1 px-5 py-10 text-center text-[15px] text-quiet">no programs or link previews</p>}
        </Section>
      ) : null}
    </>
  );
}
