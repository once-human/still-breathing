import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { COLOURS, DESIGNS } from "@/content/tee";
import { drafts, livePrices, named } from "@/lib/live";
import { rupees } from "@/lib/shop/money";
import { LINEUPS, lineupOf, paperStill, shirtBySlug, shirtsOf } from "@/content/lineups";
import { SHOP } from "@/content/shop";
import { shopOpen } from "@/lib/shop/config";
import { BRAND, SITE_URL, og, pageMeta } from "@/lib/site";
import { JsonLd } from "@/components/JsonLd";

type Params = { params: Promise<{ lineup: string; shirt: string }> };

export const dynamicParams = false;
export const generateStaticParams = () => LINEUPS.flatMap((l) => shirtsOf(l).map((d) => ({ lineup: l.slug, shirt: DESIGNS[d].slug })));

async function find(params: Params["params"]) {
  const p = await params, l = lineupOf(p.lineup), d = l ? shirtBySlug(l, p.shirt) : undefined;
  return l && d ? { l, d } : null;
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const f = await find(params);
  if (!f) return {};
  const { l, d } = f, t = await named(d), s = DESIGNS[d];
  return pageMeta({
    title: `${t.top} ${t.name}`,
    description: `${t.top}, ${t.name}: a ${COLOURS[s.colour].name} tee, ${l.title} (${l.tag}), ${rupees((await livePrices())[d])}. ${t.about.charAt(0).toUpperCase() + t.about.slice(1)} Heavy 240 gsm cotton, made to order and sent anywhere in India.`,
    path: `/${l.slug}/${s.slug}`,
    image: s.slug,
  });
}

const abs = (u: string) => (u.startsWith("http") ? u : `${SITE_URL}${u}`);

/**
 * The whole shirt page is the stage in the layout above (3D, the picks, the buy button); this only names it, and
 * tells search engines what it is: the shirt, its price, made to order, free delivery and the days it takes.
 */
export default async function ShirtPage({ params }: Params) {
  const f = await find(params);
  if (!f || (await drafts()).includes(f.d)) notFound();
  const { l, d } = f, t = await named(d), s = DESIGNS[d], url = `${SITE_URL}/${l.slug}/${s.slug}`;
  const days = (q: [number, number]) => ({ "@type": "QuantitativeValue", minValue: q[0], maxValue: q[1], unitCode: "DAY" });
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@graph": [
          {
            "@type": "Product",
            "@id": `${url}#shirt`,
            name: `${t.top} ${t.name}`,
            description: t.about,
            sku: s.slug,
            color: COLOURS[s.colour].name,
            material: "240 gsm cotton",
            image: [abs(paperStill(d, "back")), abs(paperStill(d, "front")), abs(og(s.slug).url)],
            brand: { "@type": "Brand", name: BRAND },
            offers: {
              "@type": "Offer",
              url,
              price: (await livePrices())[d],
              priceCurrency: "INR",
              availability: shopOpen() ? "https://schema.org/MadeToOrder" : "https://schema.org/OutOfStock",
              itemCondition: "https://schema.org/NewCondition",
              seller: { "@type": "Organization", name: BRAND },
              shippingDetails: {
                "@type": "OfferShippingDetails",
                shippingRate: { "@type": "MonetaryAmount", value: 0, currency: "INR" },
                shippingDestination: { "@type": "DefinedRegion", addressCountry: "IN" },
                deliveryTime: { "@type": "ShippingDeliveryTime", handlingTime: days(SHOP.make), transitTime: days(SHOP.road) },
              },
              hasMerchantReturnPolicy: { "@type": "MerchantReturnPolicy", applicableCountry: "IN", returnPolicyCategory: "https://schema.org/MerchantReturnNotPermitted" },
            },
          },
          {
            "@type": "BreadcrumbList",
            itemListElement: [
              { "@type": "ListItem", position: 1, name: BRAND, item: SITE_URL },
              { "@type": "ListItem", position: 2, name: l.title, item: `${SITE_URL}/${l.slug}` },
              { "@type": "ListItem", position: 3, name: `${t.top} ${t.name}`, item: url },
            ],
          },
        ],
      }}
    />
  );
}
