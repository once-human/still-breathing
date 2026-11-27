import Link from "next/link";
import { requireAdmin } from "@/lib/admin/auth";
import { listPeople, listVisits, type VisitFilter } from "@/lib/visits/server";
import { span } from "@/lib/visits/shared";
import { PageHead, Section } from "../../ui/ui";
import { Reached, VisitTable, shirtLabel, time } from "../../ui/visits";
import { DESIGNS } from "@/content/tee";

export const metadata = { title: "visitors" };
export const dynamic = "force-dynamic";

const TABS = [["visits", "every visit"], ["people", "people"], ["bots", "bots and previews"]] as const;
const RANGES = [[24, "24 h"], [24 * 7, "7 days"], [24 * 30, "30 days"], [24 * 90, "90 days"]] as const;
const REACH = [["", "anyone"], ["bag", "put in the bag"], ["checkout", "opened checkout"], ["pay", "opened payment"], ["paid", "paid"]] as const;

type SP = { tab?: string; h?: string; referrer?: string; device?: string; place?: string; shirt?: string; reached?: string; person?: string };

export default async function Visitors({ searchParams }: { searchParams: Promise<SP> }) {
  await requireAdmin();
  const sp = await searchParams;
  const tab = TABS.find(([t]) => t === sp.tab)?.[0] ?? "visits";
  const hours = RANGES.find(([h]) => String(h) === sp.h)?.[0] ?? 24 * 7;
  const f: VisitFilter = { kind: tab === "bots" ? "bot" : "person", referrer: sp.referrer, device: sp.device, place: sp.place, shirt: sp.shirt, reached: sp.reached, person: sp.person };
  const link = (patch: Partial<SP>) => {
    const q = new URLSearchParams(Object.entries({ ...sp, ...patch }).filter(([, v]) => v) as [string, string][]);
    return `?${q}`;
  };
  const [visits, people] = await Promise.all([
    tab === "people" ? Promise.resolve([]) : listVisits(hours, f, 500).catch(() => []),
    tab === "people" ? listPeople(hours).catch(() => []) : Promise.resolve([]),
  ]);
  const filters = (["referrer", "device", "place", "shirt", "reached", "person"] as const).filter((k) => sp[k]);
  const pill = (on: boolean) => `rounded-full px-3 py-1 text-[12px] ring-1 transition ${on ? "bg-ink text-paper ring-ink" : "text-quiet ring-line hover:text-ink hover:ring-ink"}`;

  return (
    <>
      <PageHead title="visitors" sub="every visit, page by page, kept 90 days. a person is a random code their browser made: no names, no IP addresses" />
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1.5">{TABS.map(([t, l]) => <Link key={t} href={link({ tab: t })} className={pill(t === tab)}>{l}</Link>)}</div>
        <div className="flex flex-wrap gap-1.5">{RANGES.map(([h, l]) => <Link key={h} href={link({ h: String(h) })} className={pill(h === hours)}>{l}</Link>)}</div>
      </div>

      {tab !== "people" ? (
        <form className="mb-6 flex flex-wrap items-end gap-2 text-[12px]">
          <input type="hidden" name="tab" value={tab} /><input type="hidden" name="h" value={hours} />
          {tab === "visits" ? (
            <>
              <label className="grid gap-1 text-quiet">came from<input name="referrer" defaultValue={sp.referrer} placeholder="instagram.com, direct" className="h-8 w-40 rounded-md bg-ink/[0.03] px-2 text-ink ring-1 ring-line focus:outline-none focus:ring-ink" /></label>
              <label className="grid gap-1 text-quiet">city or country<input name="place" defaultValue={sp.place} placeholder="Pune, IN" className="h-8 w-32 rounded-md bg-ink/[0.03] px-2 text-ink ring-1 ring-line focus:outline-none focus:ring-ink" /></label>
              <label className="grid gap-1 text-quiet">shirt
                <select name="shirt" defaultValue={sp.shirt ?? ""} className="h-8 rounded-md bg-paper px-2 text-ink ring-1 ring-line focus:outline-none focus:ring-ink">
                  <option value="">any</option>{Object.keys(DESIGNS).map((d) => <option key={d} value={d}>{shirtLabel(d)}</option>)}
                </select>
              </label>
              <label className="grid gap-1 text-quiet">got to
                <select name="reached" defaultValue={sp.reached ?? ""} className="h-8 rounded-md bg-paper px-2 text-ink ring-1 ring-line focus:outline-none focus:ring-ink">
                  {REACH.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </label>
            </>
          ) : null}
          <button className="h-8 rounded-md bg-ink px-3 font-semibold text-paper">filter</button>
          {filters.length ? <Link href={`?tab=${tab}&h=${hours}`} className="h-8 px-2 leading-8 text-quiet hover:text-ink">clear</Link> : null}
        </form>
      ) : null}

      {tab === "people" ? (
        <Section title={`${people.length} people`} aside="most recent first, with everything they did in the kept 90 days">
          {people.length ? (
            <div className="-mx-4 overflow-x-auto px-4 md:mx-0 md:px-0">
              <table className="w-full min-w-[720px] text-left text-[13px]">
                <thead><tr className="border-b border-line text-[11px] uppercase tracking-[0.1em] text-quiet">{["person", "last seen", "visits", "pages", "time", "where", "device", "got to"].map((h) => <th key={h} className="py-2 pr-4 font-medium">{h}</th>)}</tr></thead>
                <tbody className="[&_td]:py-2.5 [&_td]:pr-4 [&_td]:align-top [&_tr]:border-b [&_tr]:border-line/60">
                  {people.map((p) => (
                    <tr key={p.id} className="hover:bg-ink/[0.03]">
                      <td><Link href={`/admin/visitors/person/${p.id}`} className="font-mono underline decoration-line underline-offset-4">{p.id.slice(0, 6)}</Link></td>
                      <td className="whitespace-nowrap text-quiet">{time(p.lastAt)}</td>
                      <td className="tnum">{p.visits}{p.visits > 1 ? <span className="ml-1 text-[11px] text-[#8fd19e]">returning</span> : null}</td>
                      <td className="tnum">{p.pages}</td>
                      <td className="tnum text-quiet">{span(p.activeMs)}</td>
                      <td className="text-quiet">{p.places.join(" · ") || "–"}</td>
                      <td className="text-quiet">{p.devices.join(", ")}</td>
                      <td><Reached steps={p.reached} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p className="text-[13px] text-quiet">nobody in this time.</p>}
        </Section>
      ) : (
        <Section title={`${visits.length} ${tab === "bots" ? "programs" : "visits"}`} aside={filters.length ? `filtered by ${filters.join(", ")}` : undefined}>
          <VisitTable visits={visits} empty={tab === "bots" ? "no programs in this time" : "no visits in this time"} />
        </Section>
      )}
    </>
  );
}
