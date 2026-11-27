import { notFound } from "next/navigation";
import { SIZE_ORDER } from "@/content/tee";
import { requireAdmin } from "@/lib/admin/auth";
import { getSettings } from "@/lib/admin/settings";
import { payView } from "@/lib/shop/catalog";
import { productById } from "@/lib/shop/products";
import { Segmented } from "../../../ui/client";
import { KV, PageHead, Section } from "../../../ui/ui";
import { ProductForm } from "./ProductForm";

export const metadata = { title: "product" };
export const dynamic = "force-dynamic";

const STATUS = [
  { value: "live" as const, label: "on sale", tone: "ok" as const },
  { value: "soldout" as const, label: "sold out", tone: "warn" as const },
  { value: "draft" as const, label: "hidden", tone: "off" as const },
];
const MEANS = { live: "the buy button works in every size qikink has", soldout: "it stays on the site; its button says sold out", draft: "off the shop, the lineup and the header; its own page is not found" };

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  await requireAdmin();
  const { id } = await params;
  const [p, s, pay] = await Promise.all([productById(id), getSettings(), payView().catch(() => null)]);
  if (!p) notFound();
  const sellable = new Set(pay?.payable[p.id] ?? []);
  return (
    <>
      <PageHead title={`${p.no} ${p.name}${p.city ? ` ${p.city}` : ""}`} sub={<a href={`/${p.slug}`} target="_blank" rel="noreferrer" className="underline decoration-line underline-offset-4 hover:text-ink">sahn.in/{p.slug}</a>} />

      <Section title="status" aside="saved the moment you pick">
        <div className="flex flex-wrap items-center gap-4 rounded-xl border border-line p-4">
          <Segmented label={p.name} value={p.status} options={STATUS} url={`/api/admin/products/${p.id}`} field="status" />
          <span className="text-[13px] text-quiet">{MEANS[p.status]}</span>
        </div>
      </Section>

      <Section title="can it be bought now" aside={pay?.pay ? "the shop's own checkout answer" : "checkout is closed for every shirt"}>
        <div className="flex flex-wrap gap-2">
          {SIZE_ORDER.map((z) => {
            const on = sellable.has(z);
            return (
              <span key={z} title={on ? "on sale" : !p.skus[z] ? "qikink has no product for this size" : p.status !== "live" ? "the shirt isn't on sale" : "checkout is closed"}
                className={`tnum flex items-center gap-1.5 rounded-full px-3 py-1 text-[12px] ring-1 ${on ? "text-[#8fd19e] ring-[#8fd19e]/40" : "text-quiet ring-line"}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${on ? "bg-[#8fd19e]" : "bg-ink/25"}`} />{z}
              </span>
            );
          })}
        </div>
      </Section>

      <ProductForm p={p} shopMargin={s.margin} />

      <Section title="locked" className="mt-4" aside="from qikink and the code: they tie to the print files and the 3D">
        <KV items={[
          ["qikink sku", <span key="s" className="grid gap-0.5 font-mono text-[12px]">{SIZE_ORDER.map((z) => <span key={z}>{z.padEnd(4, " ")} {p.skus[z] ?? "– none: can't be bought"}</span>)}</span>],
          ["number", p.no], ["address", `/${p.slug}`], ["city", p.city ?? "the tour"], ["colour", p.colour === "cream" ? "off white" : p.colour],
        ]} />
      </Section>
    </>
  );
}
