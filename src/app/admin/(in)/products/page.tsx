import { SIZE_ORDER } from "@/content/tee";
import { requireAdmin } from "@/lib/admin/auth";
import { getSettings } from "@/lib/admin/settings";
import { products } from "@/lib/shop/products";
import { A, PageHead, Pill, Table, dt, inr } from "../../ui/ui";

export const metadata = { title: "products" };

const STATUS = { live: ["on sale", "ok"], soldout: ["sold out", "warn"], draft: ["draft", undefined] } as const;

export default async function Products() {
  await requireAdmin();
  const [list, s] = await Promise.all([products(), getSettings()]);
  return (
    <>
      <PageHead title="products" sub={`price = ${inr(s.margin)} over qikink's cost, up to the next ₹10, unless a shirt has its own margin or price`} />
      <Table head={["shirt", "status", "price", "qikink cost", "margin", "sizes with a sku", "changed"]}>
        {list.map((p) => {
          const [word, tone] = STATUS[p.status];
          const skus = SIZE_ORDER.filter((z) => p.skus[z]);
          return (
            <tr key={p.id}>
              <td><A href={`/admin/products/${p.id}`}>{p.no} {p.name}{p.city ? ` ${p.city}` : ""}</A><div className="text-[12px] text-quiet">{p.colour === "cream" ? "off white" : p.colour}</div></td>
              <td><Pill tone={tone}>{word}</Pill></td>
              <td className="tnum font-semibold">{inr(p.price)}{p.fixedPrice != null ? <div className="text-[11px] font-normal text-quiet">fixed</div> : null}</td>
              <td className="tnum">{inr(p.cost, true)}</td>
              <td className="tnum">{inr(Math.round((p.price - p.cost) * 100) / 100, true)}<div className="text-[11px] text-quiet">{p.margin != null ? `own rule ${inr(p.margin)}` : "shop rule"}</div></td>
              <td>{skus.length ? skus.join(" ") : <span className="text-[#f0a35b]">none: can&apos;t be bought</span>}</td>
              <td className="text-[12px] text-quiet">{p.updatedAt ? dt(p.updatedAt) : "as in the code"}</td>
            </tr>
          );
        })}
      </Table>
    </>
  );
}
