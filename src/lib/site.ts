import { CURRENT } from "@/content/lineups";
import { POLICIES, POLICIES_READY, POLICY_ORDER } from "@/content/policies";

/** The address the site is served from, for metadata, Open Graph and the sitemap. */
export const SITE_URL = "https://sahn.in";

export const BRAND = "sahn";

/** The header, left to right (the bag sits apart, on the right). */
export const NAV = [
  { href: "/lineups", label: "lineups" },
  { href: `/${CURRENT.slug}`, label: `lineup ${CURRENT.no}`, lineup: true },
  { href: "/made", label: "how it's made" },
  { href: "/size-guide", label: "sizes" },
  { href: "/help", label: "help" },
] as const;

/**
 * The policy pages, from the shop's src/content/policies.ts. They exist only once the shop's words are complete
 * (POLICIES_READY: who runs it, where, the email); until then nothing links to them and the routes are 404s.
 */
export const POLICY_LINKS: { href: string; label: string }[] = POLICIES_READY
  ? POLICY_ORDER.map((s) => ({ href: `/policies/${s}`, label: POLICIES[s].title }))
  : [];

export const HELP_LINKS = [
  { href: "/size-guide", label: "size guide" },
  { href: "/help#orders", label: "orders" },
  { href: "/help#shipping", label: "shipping" },
  { href: "/help#care", label: "care" },
  ...(POLICIES_READY ? [{ href: "/help#contact", label: "contact" }] : []),
  { href: "/order", label: "find your order" },
];

/** Open Graph pictures, made from the studio renders by scripts/og.mjs */
export const og = (name: string) => ({ url: `/og/${name}.jpg`, width: 1200, height: 630 });

/**
 * A page's metadata in full. Next replaces openGraph wholesale when a page sets it, so every page gets the whole set:
 * its title, words, address and picture.
 */
export function pageMeta({ title, description, path, image = "home" }: { title?: string; description: string; path: string; image?: string }) {
  const t = title ?? BRAND;
  return {
    ...(title ? { title } : {}),
    description,
    alternates: { canonical: path },
    openGraph: { type: "website" as const, siteName: BRAND, title: title ? `${title} · ${BRAND}` : BRAND, description, url: path, locale: "en_IN", images: [og(image)] },
    twitter: { card: "summary_large_image" as const, title: t, description, images: [og(image).url] },
  };
}
