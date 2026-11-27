import Link from "next/link";
import { requireAdmin } from "@/lib/admin/auth";
import { allOrders, isPaid, istDay } from "@/lib/admin/data";
import { summary, type Count } from "@/lib/visits/server";
import { span } from "@/lib/visits/shared";
import { PageHead, Section, Stat, Table } from "../../ui/ui";
import { pageName, shirtLabel } from "../../ui/visits";

export const metadata = { title: "activity" };
export const dynamic = "force-dynamic";

const RANGES = [7, 30, 90] as const;
const pct = (n: number, of: number) => (of ? `${Math.round((n / of) * 1000) / 10}%` : "–");

function Bars({ data }: { data: { day: string; people: number; paid: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.people));
  return (
    <div>
      <div className="flex h-40 items-end gap-[2px]" role="img" aria-label="people per day, paid orders marked">
        {data.map((d) => (
          <div key={d.day} className="group relative flex h-full flex-1 flex-col justify-end" title={`${d.day}: ${d.people} people, ${d.paid} paid`}>
            <div className="w-full rounded-t-[2px] bg-ink/25 transition group-hover:bg-ink/60" style={{ height: `${(d.people / max) * 100}%`, minHeight: d.people ? 2 : 0 }} />
            {d.paid ? <div className="absolute inset-x-0 bottom-0 rounded-t-[2px] bg-blue" style={{ height: `${Math.min(100, (d.paid / max) * 100)}%`, minHeight: 3 }} /> : null}
          </div>
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-quiet"><span>{data[0]?.day.slice(5)}</span><span>grey: people · blue: paid orders</span><span>{data[data.length - 1]?.day.slice(5)}</span></div>
    </div>
  );
}

function Top({ title, rows, label, aside }: { title: string; rows: Count[]; label?: (k: string) => React.ReactNode; aside?: string }) {
  const max = Math.max(1, ...rows.map((r) => r.people));
  return (
    <Section title={title} aside={aside}>
      {rows.length ? (
        <ul className="grid gap-1 text-[13px]">
          {rows.map((r) => (
            <li key={r.key} className="relative flex justify-between gap-4 py-1 pl-2">
              <span className="absolute inset-y-0 left-0 rounded-[2px] bg-ink/[0.07]" style={{ width: `${(r.people / max) * 100}%` }} />
              <span className="relative min-w-0 truncate">{label ? label(r.key) : r.key}</span>
              <span className="tnum relative shrink-0 text-quiet">{r.people} <span className="text-[11px]">· {r.visits} visit{r.visits === 1 ? "" : "s"}</span></span>
            </li>
          ))}
        </ul>
      ) : <p className="text-[13px] text-quiet">nothing yet</p>}
    </Section>
  );
}

export default async function Activity({ searchParams }: { searchParams: Promise<{ days?: string }> }) {
  await requireAdmin();
  const want = (await searchParams).days;
  const days = RANGES.find((r) => String(r) === want) ?? 30;
  const [a, orders] = await Promise.all([summary(days), allOrders()]);
  const from = Date.now() - (days - 1) * 86400_000;
  const paidByDay = new Map<string, number>();
  for (const o of orders) if (isPaid(o) && Date.parse(o.paidAt!) >= from - 86400_000) {
    const d = istDay(o.paidAt!);
    paidByDay.set(d, (paidByDay.get(d) ?? 0) + 1);
  }
  const perDay = new Map(a.perDay.map((d) => [d.day, d]));
  const folded = new Map(a.folded.map((d) => [d.day, d.people]));
  let paid = 0;
  const series = Array.from({ length: days }, (_, i) => {
    const day = new Date(from + i * 86400_000 + 5.5 * 3600_000).toISOString().slice(0, 10);
    const r = perDay.get(day);
    const p = paidByDay.get(day) ?? 0;
    paid += p;
    return { day, people: r?.people ?? folded.get(day) ?? 0, visits: r?.visits ?? 0, pages: r?.pages ?? 0, bag: r?.bag ?? 0, checkout: r?.checkout ?? 0, paid: p };
  });
  const t = a.totals;
  const pill = (on: boolean) => `rounded-full px-3 py-1 text-[12px] ring-1 transition ${on ? "bg-ink text-paper ring-ink" : "text-quiet ring-line hover:text-ink hover:ring-ink"}`;
  const STEPS = [["saw", "saw it"], ["size", "picked a size"], ["look", "turned it"], ["tryon", "tried it on"], ["bag", "bagged"], ["checkout", "checkout"], ["pay", "payment"], ["paid", "paid"]] as const;

  return (
    <>
      <PageHead title="activity" sub="counted on this site only: no cookies, no outside trackers, no IP kept. people are counted once each">
        {RANGES.map((r) => <Link key={r} href={`?days=${r}`} className={pill(r === days)}>{r} days</Link>)}
      </PageHead>

      <Section title="the way to a sale" aside={`last ${days} days`}>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-6">
          <Stat label="people" value={t.people} sub={`${t.visits} visits · ${t.returning} came back`} />
          <Stat label="saw a shirt" value={t.shirt} sub={pct(t.shirt, t.people)} />
          <Stat label="put in the bag" value={t.bag} sub={pct(t.bag, t.people)} />
          <Stat label="opened checkout" value={t.checkout} sub={pct(t.checkout, t.people)} />
          <Stat label="opened payment" value={t.pay} sub={pct(t.pay, t.checkout)} />
          <Stat label="paid orders" value={paid} tone="blue" sub={`${pct(t.paid, t.pay)} of payments opened`} />
        </div>
        <p className="mt-3 text-[12px] text-quiet">a visit lasts {span(t.active)} on screen on average, {t.visits ? Math.round((t.pages / t.visits) * 10) / 10 : 0} pages each.</p>
      </Section>

      <Section title="per day"><Bars data={series} /></Section>

      <Section title="each shirt, step by step" aside="people who did each step">
        <Table head={["shirt", ...STEPS.map(([, l]) => l)]} empty="no shirt looked at yet">
          {a.funnel.map((f) => (
            <tr key={f.design}>
              <td className="font-medium">{shirtLabel(f.design)}</td>
              {STEPS.map(([k]) => {
                const n = k === "bag" ? Math.max(f.bag, f.buy) : f[k];
                return <td key={k} className={`tnum ${k === "paid" && n ? "font-semibold text-blue" : n ? "" : "text-quiet"}`}>{n}{k !== "saw" && n ? <span className="ml-1 text-[11px] text-quiet">{pct(n, f.saw)}</span> : null}</td>;
              })}
            </tr>
          ))}
        </Table>
      </Section>

      <Section title="pages" aside="views, people, time on screen and how far down they read">
        <Table head={["page", "views", "people", "time", "read"]} empty="no pages yet">
          {a.pages.map((p) => (
            <tr key={p.key}>
              <td><span className="font-medium">{pageName(p.key)}</span> <span className="text-[11px] text-quiet">{p.key}</span></td>
              <td className="tnum">{p.views}</td>
              <td className="tnum">{p.people}</td>
              <td className="tnum text-quiet">{span(p.ms)}</td>
              <td className="tnum"><span className="inline-block h-1.5 w-16 overflow-hidden rounded-full bg-ink/10 align-middle"><span className="block h-full bg-ink/50" style={{ width: `${Math.min(100, p.scroll)}%` }} /></span> <span className="text-[11px] text-quiet">{p.scroll}%</span></td>
            </tr>
          ))}
        </Table>
      </Section>

      <div className="grid gap-x-12 lg:grid-cols-2">
        <Top title="where they came from" rows={a.referrers} />
        <Top title="where they are" rows={a.places} />
        <Top title="devices" rows={a.devices} />
        <Top title="languages" rows={a.langs} />
        <Top title="screens" rows={a.screens} aside="most common sizes" />
        <Section title="put in the bag" aside="by shirt and size">
          {a.bag.length ? (
            <ul className="grid gap-1 text-[13px]">
              {a.bag.map((b) => <li key={`${b.design}-${b.size}`} className="flex justify-between gap-4 py-1"><span>{shirtLabel(b.design)} <span className="text-quiet">{b.size ?? ""}</span></span><span className="tnum text-quiet">{b.n}×</span></li>)}
            </ul>
          ) : <p className="text-[13px] text-quiet">nothing bagged yet</p>}
        </Section>
      </div>

      <Section title="programs that came by" aside={<Link href="/admin/visitors?tab=bots" className="underline decoration-line underline-offset-4 hover:text-ink">every visit →</Link>}>
        <Table head={["program", "pages", "days", "last"]} empty="no bots or link previews">
          {a.bots.map((b) => <tr key={b.name}><td>{b.name}</td><td className="tnum">{b.pages}</td><td className="tnum">{b.days}</td><td className="text-quiet">{new Date(b.last).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).toLowerCase()}</td></tr>)}
        </Table>
      </Section>

      <Section title="day by day">
        <Table head={["day", "people", "visits", "pages", "bag", "checkout", "paid"]}>
          {[...series].reverse().map((d) => (
            <tr key={d.day}>
              <td className="tnum">{d.day}</td>
              <td className="tnum">{d.people}</td>
              <td className="tnum text-quiet">{d.visits}</td>
              <td className="tnum text-quiet">{d.pages}</td>
              <td className="tnum">{d.bag || ""}</td>
              <td className="tnum">{d.checkout || ""}</td>
              <td className="tnum font-semibold text-blue">{d.paid || ""}</td>
            </tr>
          ))}
        </Table>
      </Section>
    </>
  );
}
