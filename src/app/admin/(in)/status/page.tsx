import { DESIGNS, SIZE_ORDER, type Design } from "@/content/tee";
import { requireAdmin } from "@/lib/admin/auth";
import { shirtName } from "@/lib/admin/data";
import { health, problems, type Check } from "@/lib/admin/health";
import { payView } from "@/lib/shop/catalog";
import { products } from "@/lib/shop/products";
import type { IconName } from "../../ui/icons";
import { Card, Group, Light, Page, Row, Section, type Tone } from "../../ui/ui";

export const metadata = { title: "health" };
export const dynamic = "force-dynamic";

const ICON: Record<string, IconName> = { open: "shop", pay: "card", hook: "refresh", print: "print", sync: "truck", db: "shield", mail: "mail", alerts: "alert", secret: "key", admin: "user" };
const TONE: Record<Check["tone"], Tone> = { ok: "ok", warn: "warn", bad: "bad", quiet: "quiet" };

function CheckRow({ c }: { c: Check }) {
  return <Row icon={ICON[c.key] ?? "dot"} tone={TONE[c.tone]} title={c.name} sub={c.fix ? <><span className="text-ink/80">{c.fix}</span><br />{c.detail}</> : c.detail} right={<Light tone={c.tone}>{c.state}</Light>} />;
}

/** every service, asked just now: what needs you first, then everything that's fine, then what can be bought */
export default async function Status() {
  await requireAdmin();
  const [checks, pay, list] = await Promise.all([health(true), payView().catch(() => null), products().catch(() => [])]);
  const bad = problems(checks);
  const fine = checks.filter((c) => !bad.includes(c));
  const byId = new Map(list.map((p) => [p.id, p]));
  return (
    <>
      <Page title="health" back={["/admin/settings", "settings"]}
        sub={bad.length ? `${bad.length} thing${bad.length > 1 ? "s" : ""} to look at` : "everything is working, asked just now"} />

      {bad.length ? (
        <Section title="needs you"><Group>{bad.map((c) => <CheckRow key={c.key} c={c} />)}</Group></Section>
      ) : null}

      <Section title={bad.length ? "working" : "every service"}><Group>{fine.map((c) => <CheckRow key={c.key} c={c} />)}</Group></Section>

      <Section title="can be bought now" aside={pay?.pay ? "checkout's own answer, size by size" : "checkout is closed"}>
        <Card pad={false} className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-[15px]">
            <thead><tr className="text-[13px] text-quiet"><th className="px-5 pb-2 pt-4 font-medium">shirt</th>{SIZE_ORDER.map((z) => <th key={z} className="px-2 pb-2 pt-4 text-center font-medium">{z}</th>)}</tr></thead>
            <tbody>
              {(Object.keys(DESIGNS) as Design[]).map((d) => {
                const p = byId.get(d), ok = new Set(pay?.payable[d] ?? []);
                return (
                  <tr key={d} className="border-t border-line/40">
                    <td className="px-5 py-3.5">{shirtName(d)}<div className="text-[13px] text-quiet">{p ? { live: "on sale", soldout: "sold out", draft: "hidden" }[p.status] : "–"}</div></td>
                    {SIZE_ORDER.map((z) => <td key={z} className="px-2 text-center"><span className={`inline-block h-3 w-3 rounded-full ${ok.has(z) ? "bg-ok" : p?.skus[z] ? "bg-s3" : "ring-1 ring-inset ring-line"}`} /></td>)}
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="border-t border-line/40 px-5 py-3.5 text-[13px] text-quiet">green: anyone can buy it now · grey: not on sale · ring: qikink has no product in that size</p>
        </Card>
      </Section>
    </>
  );
}
