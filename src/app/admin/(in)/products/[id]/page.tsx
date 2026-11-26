import { notFound } from "next/navigation";
import { requireAdmin } from "@/lib/admin/auth";
import { getSettings } from "@/lib/admin/settings";
import { productById } from "@/lib/shop/products";
import { ProductForm } from "./ProductForm";
import { KV, PageHead, Section } from "../../../ui/ui";

export const metadata = { title: "product" };

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  await requireAdmin();
  const { id } = await params;
  const [p, s] = await Promise.all([productById(id), getSettings()]);
  if (!p) notFound();
  return (
    <>
      <PageHead title={`${p.no} ${p.name}${p.city ? ` ${p.city}` : ""}`} sub={`/${p.slug}`} />
      <ProductForm p={p} shopMargin={s.margin} />
      <Section title="fixed in the code" className="mt-12" aside="src/content/tee.ts: they tie to the print files and the 3D">
        <KV items={[["number", p.no], ["address", `/${p.slug}`], ["city", p.city ?? "the tour"], ["colour", p.colour === "cream" ? "off white" : p.colour]]} />
      </Section>
    </>
  );
}
