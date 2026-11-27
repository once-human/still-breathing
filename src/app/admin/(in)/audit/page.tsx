import { requireAdmin } from "@/lib/admin/auth";
import { auditPage } from "@/lib/admin/log";
import { A, PageHead, Table, dt } from "../../ui/ui";

export const metadata = { title: "audit log" };

const target = (t: string | null) =>
  !t ? "–" : /^S\d{6}[A-Z0-9]{4}$/.test(t) ? <A href={`/admin/orders/${t}`} className="font-mono">{t}</A>
  : t.startsWith("customer:") ? <A href={`/admin/people/${encodeURIComponent(t.slice(9))}`}>{t.slice(9)}</A>
  : t.startsWith("product:") ? <A href={`/admin/products/${t.slice(8)}`}>{t.slice(8)}</A>
  : t;

/** every admin action and sign-in, newest first; nothing in it can be edited or removed from the admin */
export default async function Audit({ searchParams }: { searchParams: Promise<{ q?: string; before?: string }> }) {
  await requireAdmin();
  const sp = await searchParams;
  const q = typeof sp.q === "string" ? sp.q.slice(0, 100) : "";
  const before = Number(sp.before) || undefined;
  const list = await auditPage({ q, before, limit: 100 });
  return (
    <>
      <PageHead title="audit log" sub="every sign-in and every change made here, with who and when" />
      <form className="mb-6 flex gap-2" method="get">
        <input name="q" defaultValue={q} placeholder="action, order, email" className="h-9 w-72 bg-transparent px-2 text-[13px] ring-1 ring-line focus:ring-ink focus:outline-none" />
        <button className="h-9 bg-ink px-4 text-[13px] font-semibold text-paper">search</button>
      </form>
      <Table head={["when", "who", "what", "on", "detail", "from"]} empty="nothing logged yet">
        {list.map((r) => (
          <tr key={r.id}>
            <td className="whitespace-nowrap text-quiet">{dt(r.at)}</td>
            <td className="text-[12px]">{r.who}</td>
            <td className={`font-mono text-[12px] ${r.action.endsWith(".failed") || r.action === "login.refused" ? "text-[#f08a7a]" : ""}`}>{r.action}</td>
            <td>{target(r.target)}</td>
            <td className="max-w-[28rem] break-words font-mono text-[11px] text-quiet">{r.detail ? JSON.stringify(r.detail) : ""}</td>
            <td className="font-mono text-[11px] text-quiet">{r.ip ?? ""}</td>
          </tr>
        ))}
      </Table>
      {list.length === 100 ? <div className="mt-6 text-[13px]"><A href={`?${new URLSearchParams({ ...(q ? { q } : {}), before: String(list[list.length - 1].id) })}`}>older →</A></div> : null}
    </>
  );
}
