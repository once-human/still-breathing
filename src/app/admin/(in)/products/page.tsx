import Link from "next/link";
import { SIZE_ORDER } from "@/content/tee";
import { requireAdmin } from "@/lib/admin/auth";
import { payView } from "@/lib/shop/catalog";
import { products } from "@/lib/shop/products";
import { Segmented } from "../../ui/client";
import { Icon } from "../../ui/icons";
import { Page, inr } from "../../ui/ui";

export const metadata = { title: "shirts" };
export const dynamic = "force-dynamic";

const STATUS = [
  { value: "live" as const, label: "on sale", tone: "ok" as const },
  { value: "soldout" as const, label: "sold out", tone: "warn" as const },
  { value: "draft" as const, label: "hidden", tone: "off" as const },
];

/** shirts: one card each with its price, its status (saved the moment you pick) and the sizes that can be bought now */
export default async function Products() {
  await requireAdmin();
  const [list, pay] = await Promise.all([products(), payView().catch(() => null)]);
  return (
    <>
      <Page title="shirts" sub={pay && !pay.pay ? "checkout is closed, so nothing can be bought right now. status saves the moment you pick." : "status saves the moment you pick; tap a shirt for its words and price"} />
      <div className="grid gap-3 md:grid-cols-2">
        {list.map((p) => {
          const sellable = new Set(pay?.payable[p.id] ?? []);
          return (
            <div key={p.id} className={`rounded-[22px] bg-s1 ${p.status === "draft" ? "opacity-70" : ""}`}>
              <Link href={`/admin/products/${p.id}`} className="group flex items-start gap-4 rounded-t-[22px] px-5 pb-4 pt-5 transition hover:bg-s2">
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] text-quiet">{p.no} · {p.colour === "cream" ? "off white" : p.colour}{p.city ? ` · ${p.city}` : ""}</div>
                  <div className="mt-1 truncate text-[20px] font-semibold tracking-[-0.02em]">{p.name}</div>
                </div>
                <div className="text-right">
                  <div className="tnum text-[20px] font-semibold">{inr(p.price)}</div>
                  <div className="tnum text-[13px] text-quiet">leaves {inr(Math.round(p.price - p.cost))}</div>
                </div>
                <Icon name="chevron" className="mt-1 h-[18px] w-[18px] text-quiet transition group-hover:translate-x-0.5 group-hover:text-ink" />
              </Link>
              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line/50 px-5 py-4">
                <Segmented compact label={p.name} value={p.status} options={STATUS} url={`/api/admin/products/${p.id}`} field="status" />
                <div className="flex gap-1.5" aria-label="sizes that can be bought now">
                  {SIZE_ORDER.map((z) => {
                    const on = sellable.has(z);
                    return <span key={z} title={on ? "can be bought" : p.skus[z] ? "not on sale" : "qikink has no product for this size"}
                      className={`tnum grid h-7 min-w-7 place-items-center rounded-full px-1.5 text-[12px] ${on ? "bg-s3 text-ink" : "text-quiet/60 line-through decoration-quiet/40"}`}>{z}</span>;
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
