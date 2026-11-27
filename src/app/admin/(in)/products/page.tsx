import { SIZE_ORDER } from "@/content/tee";
import { requireAdmin } from "@/lib/admin/auth";
import { getSettings } from "@/lib/admin/settings";
import { payView } from "@/lib/shop/catalog";
import { products } from "@/lib/shop/products";
import { Segmented } from "../../ui/client";
import { A, PageHead, Table, dt, inr } from "../../ui/ui";

export const metadata = { title: "products" };
export const dynamic = "force-dynamic";

const STATUS = [
  { value: "live" as const, label: "on sale", tone: "ok" as const },
  { value: "soldout" as const, label: "sold out", tone: "warn" as const },
  { value: "draft" as const, label: "hidden", tone: "off" as const },
];

export default async function Products() {
  await requireAdmin();
  const [list, s, pay] = await Promise.all([products(), getSettings(), payView().catch(() => null)]);
  return (
    <>
      <PageHead title="products" sub={`price = qikink's cost + ${inr(s.margin)}, up to the next ₹10, unless a shirt has its own margin or price. status saves the moment you pick`}>
        {pay && !pay.pay ? <span className="rounded-full bg-[#f0a35b]/15 px-3 py-1 text-[12px] text-[#f0a35b]">checkout is closed: nothing can be bought</span> : null}
      </PageHead>
      <Table head={["shirt", "status", "price", "qikink cost", "margin", "can be bought", "changed"]}>
        {list.map((p) => {
          const sellable = new Set(pay?.payable[p.id] ?? []);
          return (
            <tr key={p.id}>
              <td><A href={`/admin/products/${p.id}`} className="font-medium">{p.no} {p.name}{p.city ? ` ${p.city}` : ""}</A><div className="text-[12px] text-quiet">{p.colour === "cream" ? "off white" : p.colour}</div></td>
              <td><Segmented compact label={p.name} value={p.status} options={STATUS} url={`/api/admin/products/${p.id}`} field="status" /></td>
              <td className="tnum font-semibold">{inr(p.price)}{p.fixedPrice != null ? <div className="text-[11px] font-normal text-quiet">fixed</div> : null}</td>
              <td className="tnum text-quiet" title="qikink's price, GST included: locked">🔒 {inr(p.cost, true)}</td>
              <td className="tnum">{inr(Math.round((p.price - p.cost) * 100) / 100, true)}<div className="text-[11px] text-quiet">{p.margin != null ? `own rule ${inr(p.margin)}` : "shop rule"}</div></td>
              <td>
                <div className="flex flex-wrap gap-1">
                  {SIZE_ORDER.map((z) => {
                    const on = sellable.has(z);
                    return <span key={z} title={on ? "on sale" : p.skus[z] ? "not on sale" : "no qikink product for this size"} className={`rounded px-1.5 py-0.5 text-[11px] ${on ? "bg-[#8fd19e]/15 text-[#8fd19e]" : "text-quiet line-through decoration-ink/30"}`}>{z}</span>;
                  })}
                </div>
              </td>
              <td className="text-[12px] text-quiet">{p.updatedAt ? dt(p.updatedAt) : "as in the code"}</td>
            </tr>
          );
        })}
      </Table>
    </>
  );
}
