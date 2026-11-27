import { requireAdmin } from "@/lib/admin/auth";
import { rows } from "@/lib/admin/db";
import { allAccounts } from "@/lib/admin/data";
import { FIELD } from "../../ui/client";
import { Icon } from "../../ui/icons";
import { Avatar, Empty, Group, Page, Row, Tabs, ago, dateOnly } from "../../ui/ui";

export const metadata = { title: "accounts" };
export const dynamic = "force-dynamic";

const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";

/** accounts: everyone who signed up at /account, newest first, with how many devices they're signed in on now */
export default async function Accounts({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  await requireAdmin();
  const sp = await searchParams;
  const q = one(sp.q).toLowerCase().trim().slice(0, 100);
  const who = one(sp.who);
  const [all, sess] = await Promise.all([
    allAccounts(),
    rows<{ email: string; n: string }>("SELECT value AS email, count(*)::text AS n FROM kv WHERE key LIKE 'sess:%' AND (expires_at IS NULL OR expires_at > now()) GROUP BY value").catch(() => []),
  ]);
  const on = new Map(sess.map((r) => [r.email, Number(r.n)]));
  const found = all.filter((a) => !q || `${a.email} ${a.name} ${a.phone}`.toLowerCase().includes(q));
  const VIEWS = [
    { key: "", label: "all", has: () => true },
    { key: "in", label: "signed in now", has: (a: (typeof all)[number]) => (on.get(a.email) ?? 0) > 0 },
    { key: "ordered", label: "ordered", has: (a: (typeof all)[number]) => a.orders > 0 },
    { key: "none", label: "never ordered", has: (a: (typeof all)[number]) => a.orders === 0 },
  ];
  const view = VIEWS.find((v) => v.key === who) ?? VIEWS[0];
  const list = found.filter(view.has);
  const qs = (w: string) => "?" + new URLSearchParams(Object.entries({ q, who: w }).filter(([, v]) => v) as [string, string][]).toString();
  const week = all.filter((a) => Date.now() - Date.parse(a.createdAt) < 7 * 86400_000).length;

  return (
    <>
      <Page title="accounts" sub={`${all.length} account${all.length === 1 ? "" : "s"}${week ? `, ${week} new this week` : ""}. sign-in is by an emailed code, no passwords.`} />
      <Tabs active={view.key} items={VIEWS.map((v) => ({ key: v.key, label: v.label, href: qs(v.key), count: found.filter(v.has).length }))} />

      <form method="get" className="relative mb-8">
        {view.key ? <input type="hidden" name="who" value={view.key} /> : null}
        <Icon name="search" className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-quiet" />
        <input name="q" defaultValue={q} placeholder="search a name, email or phone" className={`${FIELD} !rounded-full !pl-12`} />
      </form>

      {list.length ? (
        <Group>
          {list.slice(0, 300).map((a) => {
            const n = on.get(a.email) ?? 0;
            return (
              <Row key={a.email} href={`/admin/people/${encodeURIComponent(a.email)}`}
                title={<span className="flex items-center gap-4"><Avatar name={a.name || a.email} />
                  <span className="min-w-0">
                    <span className="block truncate">{(a.name || a.email.split("@")[0]).toLowerCase()}</span>
                    <span className="block truncate text-[13px] text-quiet">{a.email}{a.phone ? ` · +91 ${a.phone}` : ""}</span>
                  </span></span>}
                right={<span className="grid justify-items-end gap-1 text-[13px] text-quiet">
                  <span className="text-[15px] text-ink">{a.orders ? `${a.orders} order${a.orders === 1 ? "" : "s"}` : <span className="text-quiet">no orders</span>}</span>
                  <span title={dateOnly(a.createdAt)}>{n ? `signed in on ${n}` : `joined ${ago(a.createdAt)}`}</span>
                </span>} />
            );
          })}
        </Group>
      ) : <Empty icon="user" title={q ? "no account matches" : "no accounts yet"} sub={q ? "try part of the name or the email" : "they show here once someone signs in at /account"} />}
    </>
  );
}
