import { requireAdmin } from "@/lib/admin/auth";
import { getSettings } from "@/lib/admin/settings";
import { products } from "@/lib/shop/products";
import { Group, Page, Row, Section, inr } from "../../ui/ui";
import { PricesForm } from "../settings/Fields";

export const metadata = { title: "prices" };
export const dynamic = "force-dynamic";

/** prices: the shop's rule, then what each shirt sells at and what it leaves, each a tap from its own price */
export default async function Prices() {
  await requireAdmin();
  const [s, list] = await Promise.all([getSettings(true), products()]);
  return (
    <>
      <Page title="prices" sub={`every shirt sells at qikink's cost + ${inr(s.margin)}, up to the next ₹10, unless it has its own margin or price`} />
      <Section title="the rule">
        <PricesForm initial={s} />
      </Section>
      <Section title="each shirt" aside="tap one to give it its own margin or price">
        <Group>
          {list.map((p) => (
            <Row key={p.id} icon="shirt" muted={p.status === "draft"} href={`/admin/products/${p.id}#price`}
              title={`${p.no} ${p.name}${p.city ? ` ${p.city}` : ""}`}
              sub={`qikink ${inr(p.cost, true)} · leaves ${inr(Math.round((p.price - p.cost) * 100) / 100, true)} · ${p.fixedPrice != null ? "fixed price" : p.margin != null ? `own margin ${inr(p.margin)}` : "the rule"}`}
              right={<span className="tnum font-semibold">{inr(p.price)}</span>} />
          ))}
        </Group>
        <p className="mt-3 px-1 text-[13px] text-quiet">what a shirt leaves is before post and the payment fee; the money page shows what you keep after them.</p>
      </Section>
    </>
  );
}
