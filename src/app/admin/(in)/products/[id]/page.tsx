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
      <Section title="on the shirt's page" className="mt-12" aside="from the code today (src/content/tee.ts)">
        <KV items={[["about", p.about], ["front", p.frontText], ["back", p.backText], ["colour", p.colour === "cream" ? "off white" : p.colour]]} />
      </Section>
    </>
  );
}
