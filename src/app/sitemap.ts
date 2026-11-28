import type { MetadataRoute } from "next";
import { LINEUPS, shirtsOf } from "@/content/lineups";
import { shown } from "@/lib/live";
import { DESIGNS } from "@/content/tee";
import { POLICY_LINKS, SITE_URL } from "@/lib/site";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const on = await shown();
  const at = (path: string, priority: number) => ({ url: `${SITE_URL}${path}`, changeFrequency: "weekly" as const, priority });
  return [
    at("/", 1),
    at("/shop", 0.9),
    ...LINEUPS.flatMap((l) => [at(`/${l.slug}`, 0.9), ...shirtsOf(l).filter((d) => on.has(d)).map((d) => at(`/${l.slug}/${DESIGNS[d].slug}`, 0.9))]),
    at("/size-guide", 0.5),
    at("/made", 0.5),
    at("/help", 0.4),
    at("/contact", 0.4),
    ...POLICY_LINKS.map((p) => at(p.href, 0.2)),
  ];
}
