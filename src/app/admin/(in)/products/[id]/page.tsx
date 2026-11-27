import { notFound } from "next/navigation";
import { SIZE_ORDER } from "@/content/tee";
import { requireAdmin } from "@/lib/admin/auth";
import { getSettings } from "@/lib/admin/settings";
import { payView } from "@/lib/shop/catalog";
import { productById } from "@/lib/shop/products";
import { Segmented } from "../../../ui/client";
import { Field, Fixed, Group, Page, Section } from "../../../ui/ui";
import { ProductForm } from "./ProductForm";

export const metadata = { title: "shirt" };
export const dynamic = "force-dynamic";

const STATUS = [
  { value: "live" as const, label: "on sale", tone: "ok" as const },
  { value: "soldout" as const, label: "sold out", tone: "warn" as const },
  { value: "draft" as const, label: "hidden", tone: "off" as const },
];
const MEANS = { live: "the buy button works in every size qikink has", soldout: "it stays on the site; its button says sold out", draft: "off the shop, the lineup and the header; its own page is not found" };

/** one shirt: its status, which sizes can be bought, its words and price, and what's fixed by qikink and the code */
export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  await requireAdmin();
  const { id } = await params;
  const [p, s, pay] = await Promise.all([productById(id), getSettings(), payView().catch(() => null)]);
  if (!p) notFound();
  const sellable = new Set(pay?.payable[p.id] ?? []);
  return (
    <>
      <Page title={p.name.toLowerCase()} back={["/admin/products", "shirts"]}
        sub={<>{p.no}{p.city ? ` · ${p.city}` : ""} · <a href={`/${p.slug}`} target="_blank" rel="noreferrer" className="underline decoration-ink/25 underline-offset-4 hover:text-ink hover:decoration-ink">sahn.in/{p.slug}</a></>} />

      <Section title="status" aside="saves the moment you pick">
        <Group>
          <div className="grid gap-3 px-5 py-4">
            <Segmented label={p.name} value={p.status} options={STATUS} url={`/api/admin/products/${p.id}`} field="status" />
            <p className="text-[13px] text-quiet">{MEANS[p.status]}</p>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
            <span className="text-[15px]">can be bought now<span className="block text-[13px] text-quiet">{pay?.pay ? "checkout's own answer, size by size" : "checkout is closed for every shirt"}</span></span>
            <span className="flex gap-1.5">
              {SIZE_ORDER.map((z) => {
                const on = sellable.has(z);
                return <span key={z} title={on ? "can be bought" : !p.skus[z] ? "qikink has no product for this size" : p.status !== "live" ? "the shirt isn't on sale" : "checkout is closed"}
                  className={`tnum grid h-8 min-w-8 place-items-center rounded-full px-2 text-[13px] ${on ? "bg-s3 text-ink" : "text-quiet/60 line-through decoration-quiet/40"}`}>{z}</span>;
              })}
            </span>
          </div>
        </Group>
      </Section>

      <ProductForm p={p} shopMargin={s.margin} />

      <Section title="set by qikink and the code" aside="they tie to the print files and the 3D">
        <Group>
          {SIZE_ORDER.map((z) => <Field key={z} label={`qikink sku, ${z}`} hint={p.skus[z] ? undefined : "none, so this size can't be bought"}><Fixed><span className="font-mono text-[13px]">{p.skus[z] ?? "–"}</span></Fixed></Field>)}
          <Field label="number"><Fixed>{p.no}</Fixed></Field>
          <Field label="address"><Fixed>/{p.slug}</Fixed></Field>
          <Field label="city"><Fixed>{p.city ?? "the tour"}</Fixed></Field>
          <Field label="colour"><Fixed>{p.colour === "cream" ? "off white" : p.colour}</Fixed></Field>
        </Group>
      </Section>
    </>
  );
}
