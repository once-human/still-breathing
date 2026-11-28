import Link from "next/link";
import { DESIGNS } from "@/content/tee";
import { requireAdmin } from "@/lib/admin/auth";
import { linkedPeople } from "@/lib/shop/account";
import { listPeople, listVisits, type VisitFilter } from "@/lib/visits/server";
import { span } from "@/lib/visits/shared";
import { BTN, FIELD, Picker } from "../../ui/client";
import { Icon } from "../../ui/icons";
import { Group, Page, Row, Section, Tabs } from "../../ui/ui";
import { Reached, VisitTable, shirtLabel, time } from "../../ui/visits";
import { PeriodTabs, pickPeriod } from "../period";

export const metadata = { title: "visits" };
export const dynamic = "force-dynamic";

const TABS = [["visits", "every visit"], ["people", "people"], ["bots", "programs"]] as const;
const REACH = [["", "anyone"], ["bag", "put in the bag"], ["checkout", "opened checkout"], ["pay", "opened payment"], ["paid", "paid"]] as const;

type SP = { tab?: string; p?: string; referrer?: string; device?: string; place?: string; shirt?: string; reached?: string; person?: string };

/** visits: every visit page by page, the people behind them, and the programs kept apart */
export default async function Visitors({ searchParams }: { searchParams: Promise<SP> }) {
  await requireAdmin();
  const sp = await searchParams;
  const tab = TABS.find(([t]) => t === sp.tab)?.[0] ?? "visits";
  const p = await pickPeriod(sp.p);
  const f: VisitFilter = { kind: tab === "bots" ? "bot" : "person", referrer: sp.referrer, device: sp.device, place: sp.place, shirt: sp.shirt, reached: sp.reached, person: sp.person };
  const link = (patch: Partial<SP>) => `?${new URLSearchParams(Object.entries({ ...sp, ...patch }).filter(([, v]) => v) as [string, string][])}`;
  const [visits, people, names] = await Promise.all([
    tab === "people" ? Promise.resolve([]) : listVisits(p, f, 500).catch(() => []),
    tab === "people" ? listPeople(p).catch(() => []) : Promise.resolve([]),
    linkedPeople().catch(() => new Map<string, { email: string; name: string }>()),
  ]);
  const filters = (["referrer", "device", "place", "shirt", "reached", "person"] as const).filter((k) => sp[k]);
  const range = p.label;

  return (
    <>
      <Page title="visits" sub="every visit page by page, kept 90 days. a person is a random code their browser made: no names, no IP addresses" />
      <div className="mb-5 flex flex-wrap gap-x-3 [&>nav]:mb-3">
        <Tabs active={tab} items={TABS.map(([t, l]) => ({ key: t, label: l, href: link({ tab: t }) }))} />
        <PeriodTabs p={p} keep={{ tab: sp.tab }} />
      </div>

      {tab === "visits" ? (
        <details open={filters.length > 0} className="group mb-8">
          <summary className="inline-flex cursor-pointer list-none items-center gap-1.5 px-1 text-[14px] text-quiet hover:text-ink">
            <Icon name="filter" className="h-4 w-4" />filters{filters.length ? ` (${filters.length})` : ""}<Icon name="down" className="h-4 w-4 transition group-open:rotate-180" />
          </summary>
          <form className="a-pop mt-3 grid gap-3 rounded-[14px] bg-s1 p-4 sm:grid-cols-2 lg:grid-cols-4">
            <input type="hidden" name="tab" value={tab} /><input type="hidden" name="p" value={p.key} />
            <label className="grid gap-1.5 text-[13px] text-quiet">came from<input name="referrer" defaultValue={sp.referrer} placeholder="instagram.com, direct" className={FIELD} /></label>
            <label className="grid gap-1.5 text-[13px] text-quiet">city or country<input name="place" defaultValue={sp.place} placeholder="Pune, IN" className={FIELD} /></label>
            <label className="grid gap-1.5 text-[13px] text-quiet">shirt
              <Picker name="shirt" value={sp.shirt ?? ""} label="shirt" options={[{ value: "", label: "any" }, ...Object.keys(DESIGNS).map((d) => ({ value: d, label: shirtLabel(d) }))]} />
            </label>
            <label className="grid gap-1.5 text-[13px] text-quiet">got to
              <Picker name="reached" value={sp.reached ?? ""} label="got to" options={REACH.map(([v, l]) => ({ value: v, label: l }))} />
            </label>
            <div className="flex gap-2 sm:col-span-2 lg:col-span-4">
              <button className={BTN.main}>apply</button>
              {filters.length ? <Link href={`?tab=${tab}&p=${p.key}`} className={BTN.plain}>clear</Link> : null}
            </div>
          </form>
        </details>
      ) : null}

      {tab === "people" ? (
        <Section title={`${people.length} ${people.length === 1 ? "person" : "people"}`} aside={`seen ${range === "all time" ? "in the kept 90 days" : range}, latest first`}>
          {people.length ? (
            <Group>
              {people.map((p) => (
                <Row key={p.id} icon={p.visits > 1 ? "return" : "user"} href={`/admin/visitors/person/${p.id}`}
                  title={<span className="flex flex-wrap items-center gap-2">{names.get(p.id) ? <span className="font-medium">{(names.get(p.id)!.name || names.get(p.id)!.email).toLowerCase()}<span className="font-normal text-quiet"> · {p.places.join(" · ") || "somewhere"}</span></span> : p.places.join(" · ") || "somewhere"}<Reached steps={p.reached} /></span>}
                  sub={`${p.devices.join(", ")} · ${p.visits} visit${p.visits === 1 ? "" : "s"}, ${p.pages} page${p.pages === 1 ? "" : "s"}, ${span(p.activeMs)} on screen`}
                  right={<span className="text-[13px] text-quiet">{time(p.lastAt)}</span>} />
              ))}
            </Group>
          ) : <p className="rounded-[14px] bg-s1 px-5 py-10 text-center text-[15px] text-quiet">nobody in this time</p>}
        </Section>
      ) : (
        <Section title={`${visits.length} ${tab === "bots" ? "program visits" : `visit${visits.length === 1 ? "" : "s"}`}`} aside={filters.length ? `filtered by ${filters.join(", ")}` : range === "all time" ? "the kept 90 days" : range}>
          <VisitTable visits={visits} names={names} empty={tab === "bots" ? "no programs in this time" : "no visits in this time"} />
        </Section>
      )}
    </>
  );
}
