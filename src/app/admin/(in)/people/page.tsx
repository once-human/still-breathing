import { requireAdmin } from "@/lib/admin/auth";
import { customers, type Customer } from "@/lib/admin/data";
import { FIELD } from "../../ui/client";
import { Icon } from "../../ui/icons";
import { Avatar, Empty, Group, Page, Row, Tabs, ago, inr } from "../../ui/ui";

export const metadata = { title: "people" };
export const dynamic = "force-dynamic";

/** the views: everyone who ever bought or signed up, and the slices of them worth looking at apart */
const VIEWS: { key: string; label: string; has: (c: Customer) => boolean }[] = [
  { key: "", label: "everyone", has: () => true },
  { key: "bought", label: "bought", has: (c) => c.paid > 0 },
  { key: "back", label: "came back", has: (c) => c.paid > 1 },
  { key: "accounts", label: "has an account", has: (c) => !!c.account },
  { key: "guests", label: "guests", has: (c) => !c.account && c.paid > 0 },
  { key: "never", label: "never paid", has: (c) => c.paid === 0 },
];
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";

/** people: everyone the shop knows by email, accounts and guest buyers together, best customers first */
export default async function People({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  await requireAdmin();
  const sp = await searchParams;
  const q = one(sp.q).toLowerCase().trim().slice(0, 100);
  const view = VIEWS.find((v) => v.key === one(sp.who)) ?? VIEWS[0];
  const all = await customers();
  const found = all.filter((c) => !q || `${c.email} ${c.name} ${c.phone}`.toLowerCase().includes(q));
  const list = found.filter(view.has);
  const qs = (who: string) => "?" + new URLSearchParams(Object.entries({ q, who }).filter(([, v]) => v) as [string, string][]).toString();
  const buyers = all.filter((c) => c.paid).length;

  return (
    <>
      <Page title="people" sub={`${all.length} ${all.length === 1 ? "person" : "people"}: ${buyers} bought, ${all.filter((c) => c.account).length} with an account`} />
      <Tabs active={view.key} items={VIEWS.map((v) => ({ key: v.key, label: v.label, href: qs(v.key), count: found.filter(v.has).length }))} />

      <form method="get" className="relative mb-8">
        {view.key ? <input type="hidden" name="who" value={view.key} /> : null}
        <Icon name="search" className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-quiet" />
        <input name="q" defaultValue={q} placeholder="search a name, email or phone" className={`${FIELD} !rounded-full !pl-12`} />
      </form>

      {list.length ? (
        <Group>
          {list.slice(0, 300).map((c) => (
            <Row key={c.email} href={`/admin/people/${encodeURIComponent(c.email)}`}
              title={<span className="flex items-center gap-4"><Avatar name={c.name || c.email} />
                <span className="min-w-0">
                  <span className="block truncate">{(c.name || c.email.split("@")[0]).toLowerCase()}</span>
                  <span className="block truncate text-[13px] text-quiet">{c.email}{c.account ? " · account" : ""}{c.paid > 1 ? ` · bought ${c.paid} times` : ""}</span>
                </span></span>}
              right={<span className="grid justify-items-end gap-1"><span className="tnum">{c.paid ? inr(c.spend) : <span className="text-quiet">no orders</span>}</span><span className="text-[13px] text-quiet">{ago(c.last || c.first)}</span></span>} />
          ))}
        </Group>
      ) : <Empty icon="people" title={q ? "nobody matches" : "nobody here yet"} sub={q ? "try part of the name or the email" : undefined} />}
      {list.length > 300 ? <p className="mt-4 px-1 text-[13px] text-quiet">the first 300 of {list.length}; search to find the rest</p> : null}
    </>
  );
}
