import { requireAdmin } from "@/lib/admin/auth";
import { activity, type Count } from "@/lib/admin/activity";
import { allOrders, isPaid, istDay, shirtName } from "@/lib/admin/data";
import { A, PageHead, Section, Stat, Table } from "../../ui/ui";

export const metadata = { title: "activity" };

const RANGES = [7, 30, 90] as const;

function Bars({ data }: { data: { day: string; visitors: number; paid: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.visitors));
  return (
    <div>
      <div className="flex h-36 items-end gap-[2px]" role="img" aria-label="visitors per day, paid orders marked">
        {data.map((d) => (
          <div key={d.day} className="group relative flex h-full flex-1 flex-col justify-end" title={`${d.day}: ${d.visitors} visitors, ${d.paid} paid`}>
            <div className="w-full bg-ink/25 transition group-hover:bg-ink/60" style={{ height: `${(d.visitors / max) * 100}%`, minHeight: d.visitors ? 2 : 0 }} />
            {d.paid ? <div className="absolute inset-x-0 bottom-0 bg-blue" style={{ height: `${Math.min(100, (d.paid / max) * 100)}%`, minHeight: 3 }} /> : null}
          </div>
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-quiet"><span>{data[0]?.day.slice(5)}</span><span>grey: visitors · blue: paid orders</span><span>{data[data.length - 1]?.day.slice(5)}</span></div>
    </div>
  );
}

function Top({ title, rows, label }: { title: string; rows: Count[]; label?: (k: string | null) => React.ReactNode }) {
  const max = Math.max(1, ...rows.map((r) => r.visitors));
  return (
    <Section title={title}>
      {rows.length ? (
        <ul className="grid gap-1 text-[13px]">
          {rows.map((r) => (
            <li key={r.key ?? "?"} className="relative flex justify-between gap-4 py-1 pl-2">
              <span className="absolute inset-y-0 left-0 bg-ink/[0.07]" style={{ width: `${(r.visitors / max) * 100}%` }} />
              <span className="relative min-w-0 truncate">{label ? label(r.key) : r.key}</span>
              <span className="tnum relative shrink-0 text-quiet">{r.visitors} <span className="text-[11px]">· {r.views} views</span></span>
            </li>
          ))}
        </ul>
      ) : <p className="text-[13px] text-quiet">nothing counted yet</p>}
    </Section>
  );
}

export default async function Activity({ searchParams }: { searchParams: Promise<{ days?: string }> }) {
  await requireAdmin();
  const want = (await searchParams).days;
  const days = RANGES.find((r) => String(r) === want) ?? 30;
  const [a, orders] = await Promise.all([activity(days), allOrders()]);
  const from = Date.now() - (days - 1) * 86400_000;
  const paidByDay = new Map<string, number>();
  let paid = 0;
  for (const o of orders) if (isPaid(o) && Date.parse(o.paidAt!) >= from - 86400_000) {
    const d = istDay(o.paidAt!);
    paidByDay.set(d, (paidByDay.get(d) ?? 0) + 1);
  }
  const perDay = new Map(a.perDay.map((d) => [d.day, d]));
  const series = Array.from({ length: days }, (_, i) => {
    const day = new Date(from + i * 86400_000 + 5.5 * 3600_000).toISOString().slice(0, 10);
    const r = perDay.get(day);
    const p = paidByDay.get(day) ?? 0;
    paid += p;
    return { day, visitors: r?.visitors ?? 0, views: r?.views ?? 0, bags: r?.bags ?? 0, checkouts: r?.checkouts ?? 0, paid: p };
  });
  const t = a.totals;
  const pct = (n: number, of: number) => (of ? `${Math.round((n / of) * 1000) / 10}%` : "–");

  return (
    <>
      <PageHead title="activity" sub="counted on this site only: no cookies, no outside trackers, no IP kept">
        {RANGES.map((r) => <A key={r} href={`?days=${r}`} className={r === days ? "text-ink" : "text-quiet"}>{r} days</A>)}
      </PageHead>

      <Section title="the way to a sale" aside={`last ${days} days, visitors counted once a day`}>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <Stat label="visitors" value={t.visitors} />
          <Stat label="saw a shirt" value={t.shirt} sub={pct(t.shirt, t.visitors)} />
          <Stat label="added to bag" value={t.bag} sub={pct(t.bag, t.visitors)} />
          <Stat label="opened checkout" value={t.checkout} sub={pct(t.checkout, t.visitors)} />
          <Stat label="paid orders" value={paid} tone="blue" sub={`${pct(paid, t.checkout)} of checkouts`} />
        </div>
      </Section>

      <Section title="per day"><Bars data={series} /></Section>

      <div className="grid gap-x-12 lg:grid-cols-2">
        <Top title="top pages" rows={a.pages} />
        <Top title="where they came from" rows={a.sources} />
        <Top title="devices" rows={a.devices} />
        <Top title="where (country-state)" rows={a.regions} />
      </div>

      <Section title="put in the bag" aside="by shirt and size">
        <Table head={["shirt", "size", "times"]} empty="nothing added yet">
          {a.bag.map((b) => (
            <tr key={`${b.design}-${b.size}`}>
              <td>{shirtName(b.design)}</td>
              <td>{b.size ?? "–"}</td>
              <td className="tnum">{b.n}</td>
            </tr>
          ))}
        </Table>
      </Section>

      <Section title="day by day">
        <Table head={["day", "visitors", "views", "bag", "checkout", "paid"]}>
          {[...series].reverse().map((d) => (
            <tr key={d.day}>
              <td className="tnum">{d.day}</td>
              <td className="tnum">{d.visitors}</td>
              <td className="tnum text-quiet">{d.views}</td>
              <td className="tnum">{d.bags}</td>
              <td className="tnum">{d.checkouts}</td>
              <td className="tnum font-semibold">{d.paid || ""}</td>
            </tr>
          ))}
        </Table>
      </Section>
    </>
  );
}
