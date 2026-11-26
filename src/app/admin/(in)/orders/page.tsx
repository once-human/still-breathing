import Link from "next/link";
import { DESIGNS, SIZE_ORDER, type Design } from "@/content/tee";
import { requireAdmin } from "@/lib/admin/auth";
import { allOrders, istDay, shirtName } from "@/lib/admin/data";
import { refunded, type Order, type Stage } from "@/lib/shop/orders";
import { A, PageHead, STAGE_ADMIN, StageBadge, Table, dt, inr } from "../../ui/ui";

export const metadata = { title: "orders" };

type Q = { q?: string; stage?: string; shirt?: string; size?: string; from?: string; to?: string; page?: string };
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";

/** search: order number, name, email, phone, city, pin, Razorpay or Qikink id, AWB */
const hay = (o: Order) =>
  [o.id, o.contact.name, o.contact.email, o.contact.phone, o.ship.city, o.ship.pin, o.ship.state, o.rzpOrderId, o.payment?.id, o.partnerId, o.tracking?.awb, ...(o.refunds ?? []).map((r) => r.id)]
    .filter(Boolean).join(" ").toLowerCase();

const PER = 50;

export default async function Orders({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  await requireAdmin();
  const sp = await searchParams;
  const f: Q = Object.fromEntries(["q", "stage", "shirt", "size", "from", "to", "page"].map((k) => [k, one(sp[k]).slice(0, 100)]));
  const all = await allOrders();
  const q = f.q?.toLowerCase().trim();
  const list = all.filter((o) => {
    if (f.stage === "open" ? !["paid", "printing", "shipped", "out", "attention"].includes(o.stage) : f.stage ? o.stage !== f.stage : o.stage === "paying") return false;
    if (f.shirt && !o.lines.some((l) => l.design === f.shirt)) return false;
    if (f.size && !o.lines.some((l) => l.size === f.size)) return false;
    const day = istDay(o.createdAt);
    if (f.from && day < f.from) return false;
    if (f.to && day > f.to) return false;
    return !q || hay(o).includes(q);
  });
  const page = Math.max(1, Number(f.page) || 1);
  const shown = list.slice((page - 1) * PER, page * PER);
  const total = list.reduce((t, o) => t + (o.stage === "paying" ? 0 : o.total), 0);
  const qs = (patch: Partial<Q>) => "?" + new URLSearchParams(Object.entries({ ...f, ...patch }).filter(([, v]) => v) as [string, string][]).toString();
  const csv = "/api/admin/orders/export" + qs({ page: "" });

  const field = "h-9 bg-transparent px-2 text-[13px] ring-1 ring-line focus:ring-ink focus:outline-none";
  return (
    <>
      <PageHead title="orders" sub={`${list.length} order${list.length === 1 ? "" : "s"} · ${inr(total)}`}>
        <a href={csv} className="inline-flex h-9 items-center px-3 text-[13px] ring-1 ring-line hover:ring-ink">export csv</a>
      </PageHead>

      <form className="mb-6 grid gap-2 sm:flex sm:flex-wrap sm:items-end" method="get">
        <input name="q" defaultValue={f.q} placeholder="number, name, email, phone, pin, awb, payment id" className={`${field} sm:w-80`} />
        <select name="stage" defaultValue={f.stage} className={field}>
          <option value="">paid (any stage)</option>
          <option value="open">open (not delivered)</option>
          {(Object.keys(STAGE_ADMIN) as Stage[]).map((s) => <option key={s} value={s}>{STAGE_ADMIN[s]}</option>)}
        </select>
        <select name="shirt" defaultValue={f.shirt} className={field}>
          <option value="">any shirt</option>
          {(Object.keys(DESIGNS) as Design[]).map((d) => <option key={d} value={d}>{shirtName(d)}</option>)}
        </select>
        <select name="size" defaultValue={f.size} className={field}>
          <option value="">any size</option>
          {SIZE_ORDER.map((s) => <option key={s}>{s}</option>)}
        </select>
        <label className="flex items-center gap-1 text-[12px] text-quiet">from <input type="date" name="from" defaultValue={f.from} className={field} /></label>
        <label className="flex items-center gap-1 text-[12px] text-quiet">to <input type="date" name="to" defaultValue={f.to} className={field} /></label>
        <button className="h-9 bg-ink px-4 text-[13px] font-semibold text-paper">filter</button>
        {Object.values(f).some(Boolean) ? <Link href="/admin/orders" className="h-9 px-2 text-[13px] leading-9 text-quiet hover:text-ink">clear</Link> : null}
      </form>

      <Table head={["order", "placed", "buyer", "contact", "shirts", "total", "payment", "qikink", "stage"]} empty="no orders match">
        {shown.map((o) => (
          <tr key={o.id}>
            <td><A href={`/admin/orders/${o.id}`} className="font-mono">{o.id}</A></td>
            <td className="whitespace-nowrap text-quiet">{dt(o.createdAt)}</td>
            <td>{o.contact.name}<div className="text-[12px] text-quiet">{o.ship.city} {o.ship.pin}</div></td>
            <td className="text-[12px]">{o.contact.email}<div className="text-quiet">{o.contact.phone}</div></td>
            <td>{o.lines.map((l, i) => <div key={i} className="whitespace-nowrap">{shirtName(l.design)} · {l.size}{l.quantity > 1 ? ` ×${l.quantity}` : ""}</div>)}</td>
            <td className="tnum">{inr(o.total)}{refunded(o) ? <div className="text-[12px] text-quiet">−{inr(refunded(o))}</div> : null}</td>
            <td className="text-[12px] text-quiet">{o.payment?.label ?? "–"}</td>
            <td className="font-mono text-[12px] text-quiet">{o.partnerId ?? "–"}{o.tracking?.awb ? <div>{o.tracking.awb}</div> : null}</td>
            <td><StageBadge stage={o.stage} /></td>
          </tr>
        ))}
      </Table>

      {list.length > PER ? (
        <div className="mt-6 flex gap-4 text-[13px]">
          {page > 1 ? <A href={qs({ page: String(page - 1) })}>← newer</A> : null}
          <span className="text-quiet">page {page} of {Math.ceil(list.length / PER)}</span>
          {page * PER < list.length ? <A href={qs({ page: String(page + 1) })}>older →</A> : null}
        </div>
      ) : null}
    </>
  );
}
