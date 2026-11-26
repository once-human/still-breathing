import { requireAdmin } from "@/lib/admin/auth";
import { customers } from "@/lib/admin/data";
import { A, PageHead, Pill, Table, dateOnly, inr } from "../../ui/ui";

export const metadata = { title: "customers" };

export default async function Customers({ searchParams }: { searchParams: Promise<{ q?: string | string[]; who?: string | string[] }> }) {
  await requireAdmin();
  const sp = await searchParams;
  const q = (Array.isArray(sp.q) ? sp.q[0] : sp.q)?.toLowerCase().trim().slice(0, 100) ?? "";
  const who = (Array.isArray(sp.who) ? sp.who[0] : sp.who) ?? "";
  const all = await customers();
  const list = all.filter((c) => {
    if (who === "buyers" && !c.paid) return false;
    if (who === "accounts" && !c.account) return false;
    if (who === "never" && c.paid) return false;
    return !q || `${c.email} ${c.name} ${c.phone}`.toLowerCase().includes(q);
  });
  const buyers = all.filter((c) => c.paid).length;
  const repeat = all.filter((c) => c.paid > 1).length;
  const field = "h-9 bg-transparent px-2 text-[13px] ring-1 ring-line focus:ring-ink focus:outline-none";

  return (
    <>
      <PageHead title="customers" sub={`${all.length} people · ${buyers} bought · ${repeat} came back · ${all.filter((c) => c.account).length} with an account`} />
      <form className="mb-6 flex flex-wrap gap-2" method="get">
        <input name="q" defaultValue={q} placeholder="email, name or phone" className={`${field} w-72`} />
        <select name="who" defaultValue={who} className={field}>
          <option value="">everyone</option>
          <option value="buyers">bought</option>
          <option value="accounts">has an account</option>
          <option value="never">never paid</option>
        </select>
        <button className="h-9 bg-ink px-4 text-[13px] font-semibold text-paper">filter</button>
      </form>
      <Table head={["who", "contact", "orders", "spend", "first seen", "last order", ""]} empty="no one yet">
        {list.slice(0, 500).map((c) => (
          <tr key={c.email}>
            <td><A href={`/admin/customers/${encodeURIComponent(c.email)}`}>{c.name || c.email.split("@")[0]}</A></td>
            <td className="text-[12px]">{c.email}<div className="text-quiet">{c.phone ? `+91 ${c.phone}` : ""}</div></td>
            <td className="tnum">{c.paid}{c.orders.length > c.paid ? <span className="text-quiet"> (+{c.orders.length - c.paid} unpaid)</span> : null}</td>
            <td className="tnum">{inr(c.spend)}</td>
            <td className="whitespace-nowrap text-quiet">{dateOnly(c.first)}</td>
            <td className="whitespace-nowrap text-quiet">{c.last ? dateOnly(c.last) : "–"}</td>
            <td>{c.account ? <Pill>account</Pill> : null} {c.paid > 1 ? <Pill tone="blue">repeat</Pill> : null}</td>
          </tr>
        ))}
      </Table>
    </>
  );
}
