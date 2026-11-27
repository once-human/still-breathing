import Link from "next/link";
import { DESIGNS, SIZE_ORDER, type Design } from "@/content/tee";
import { requireAdmin } from "@/lib/admin/auth";
import { allOrders, istDay, shirtName } from "@/lib/admin/data";
import { refunded, type Order, type Stage } from "@/lib/shop/orders";
import { BTN, FIELD } from "../../ui/client";
import { Icon } from "../../ui/icons";
import { Avatar, Empty, Group, Page, Row, StageBadge, Tabs, ago, inr } from "../../ui/ui";

export const metadata = { title: "orders" };
export const dynamic = "force-dynamic";

type Q = { q?: string; stage?: string; shirt?: string; size?: string; from?: string; to?: string; page?: string };
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";

/** search: order number, name, email, phone, city, pin, Razorpay or Qikink id, AWB */
const hay = (o: Order) =>
  [o.id, o.contact.name, o.contact.email, o.contact.phone, o.ship.city, o.ship.pin, o.ship.state, o.rzpOrderId, o.payment?.id, o.partnerId, o.tracking?.awb, ...(o.refunds ?? []).map((r) => r.id)]
    .filter(Boolean).join(" ").toLowerCase();

/** the views along the top: each a set of stages */
const VIEWS: { key: string; label: string; stages: Stage[] | null }[] = [
  { key: "", label: "all", stages: ["paid", "printing", "shipped", "out", "delivered", "attention", "cancelled"] },
  { key: "attention", label: "needs you", stages: ["attention"] },
  { key: "paid", label: "just paid", stages: ["paid"] },
  { key: "printing", label: "being made", stages: ["printing"] },
  { key: "way", label: "on the way", stages: ["shipped", "out"] },
  { key: "delivered", label: "delivered", stages: ["delivered"] },
  { key: "cancelled", label: "cancelled", stages: ["cancelled"] },
  { key: "paying", label: "not paid", stages: ["paying"] },
];
const PER = 40;

export default async function Orders({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  await requireAdmin();
  const sp = await searchParams;
  const f: Q = Object.fromEntries(["q", "stage", "shirt", "size", "from", "to", "page"].map((k) => [k, one(sp[k]).slice(0, 100)]));
  const all = await allOrders();
  const view = VIEWS.find((v) => v.key === (f.stage === "open" ? "printing" : f.stage)) ?? VIEWS[0];
  const q = f.q?.toLowerCase().trim();
  const match = (o: Order) => {
    if (f.shirt && !o.lines.some((l) => l.design === f.shirt)) return false;
    if (f.size && !o.lines.some((l) => l.size === f.size)) return false;
    const day = istDay(o.createdAt);
    if (f.from && day < f.from) return false;
    if (f.to && day > f.to) return false;
    return !q || hay(o).includes(q);
  };
  const matched = all.filter(match);
  const list = matched.filter((o) => view.stages!.includes(o.stage));
  const page = Math.max(1, Number(f.page) || 1);
  const shown = list.slice((page - 1) * PER, page * PER);
  const total = list.reduce((t, o) => t + (o.stage === "paying" || o.stage === "cancelled" ? 0 : o.total - refunded(o)), 0);
  const qs = (patch: Partial<Q>) => "?" + new URLSearchParams(Object.entries({ ...f, ...patch }).filter(([, v]) => v) as [string, string][]).toString();
  const more = !!(f.shirt || f.size || f.from || f.to);

  return (
    <>
      <Page title="orders" sub={`${list.length} order${list.length === 1 ? "" : "s"}${total ? ` · ${inr(total)}` : ""}`}
        actions={<a href={"/api/admin/orders/export" + qs({ page: "" })} className={BTN.plain}><Icon name="download" className="h-[18px] w-[18px]" />export</a>} />

      <Tabs active={view.key} items={VIEWS.map((v) => ({ key: v.key, label: v.label, href: qs({ stage: v.key, page: "" }), count: matched.filter((o) => v.stages!.includes(o.stage)).length }))} />

      <form method="get" className="mb-8 grid gap-3">
        {f.stage ? <input type="hidden" name="stage" value={f.stage} /> : null}
        <div className="relative">
          <Icon name="search" className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-quiet" />
          <input name="q" defaultValue={f.q} placeholder="search a number, name, email, phone, pin or tracking" className={`${FIELD} !pl-12`} />
        </div>
        <details open={more} className="group">
          <summary className="inline-flex cursor-pointer list-none items-center gap-1.5 px-1 text-[14px] text-quiet hover:text-ink">
            <Icon name="filter" className="h-4 w-4" />more filters<Icon name="down" className="h-4 w-4 transition group-open:rotate-180" />
          </summary>
          <div className="a-pop mt-3 grid gap-3 rounded-[14px] bg-s1 p-4 sm:grid-cols-2 lg:grid-cols-4">
            <label className="grid gap-1.5 text-[13px] text-quiet">shirt
              <select name="shirt" defaultValue={f.shirt} className={FIELD}><option value="">any shirt</option>{(Object.keys(DESIGNS) as Design[]).map((d) => <option key={d} value={d}>{shirtName(d)}</option>)}</select>
            </label>
            <label className="grid gap-1.5 text-[13px] text-quiet">size
              <select name="size" defaultValue={f.size} className={FIELD}><option value="">any size</option>{SIZE_ORDER.map((s) => <option key={s}>{s}</option>)}</select>
            </label>
            <label className="grid gap-1.5 text-[13px] text-quiet">from<input type="date" name="from" defaultValue={f.from} className={FIELD} /></label>
            <label className="grid gap-1.5 text-[13px] text-quiet">to<input type="date" name="to" defaultValue={f.to} className={FIELD} /></label>
            <div className="flex gap-2 sm:col-span-2 lg:col-span-4">
              <button className={BTN.main}>apply</button>
              <Link href="/admin/orders" className={BTN.plain}>clear</Link>
            </div>
          </div>
        </details>
      </form>

      {shown.length ? (
        <Group>
          {shown.map((o) => {
            const back = refunded(o);
            return (
              <Row key={o.id} href={`/admin/orders/${o.id}`}
                title={<span className="flex items-center gap-4"><Avatar name={o.contact.name} tone={o.stage === "attention" ? "warn" : "quiet"} />
                  <span className="min-w-0">
                    <span className={`block truncate ${o.stage === "cancelled" ? "text-quiet line-through" : ""}`}>{o.contact.name.toLowerCase()}<span className="text-quiet">, {o.ship.city.toLowerCase()}</span></span>
                    <span className="block truncate text-[13px] text-quiet">{o.lines.map((l) => `${shirtName(l.design)} ${l.size}${l.quantity > 1 ? ` ×${l.quantity}` : ""}`).join(", ")} · {ago(o.paidAt ?? o.createdAt)} · <span className="font-mono">{o.id}</span></span>
                  </span></span>}
                right={<span className="grid justify-items-end gap-1.5"><span className="tnum">{inr(o.total)}</span>{back > 0 && o.stage !== "cancelled" ? <span className="text-[12.5px] text-warn">{inr(back)} refunded</span> : <StageBadge stage={o.stage} />}</span>} />
            );
          })}
        </Group>
      ) : <Empty icon="orders" title={q || more ? "no orders match" : view.key === "attention" ? "nothing needs you" : "no orders here yet"} sub={q || more ? "try fewer words or clear the filters" : undefined} />}

      {list.length > PER ? (
        <div className="mt-6 flex items-center justify-between text-[14px]">
          {page > 1 ? <Link href={qs({ page: String(page - 1) })} className={BTN.plain}>newer</Link> : <span />}
          <span className="text-quiet">page {page} of {Math.ceil(list.length / PER)}</span>
          {page * PER < list.length ? <Link href={qs({ page: String(page + 1) })} className={BTN.plain}>older</Link> : <span />}
        </div>
      ) : null}
    </>
  );
}
