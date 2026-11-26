import Link from "next/link";
import { CURRENT, shirtHref, shirtLabel, shirtsOf } from "@/content/lineups";
import { HELP_LINKS, POLICY_LINKS } from "@/lib/site";
import { shopOpen } from "@/lib/shop/config";
import pkg from "../../package.json";
import { SHOP } from "@/content/shop";
import { shown } from "@/lib/live";

const col = "border-t border-line pt-1.5";
const link = "text-quiet transition-colors hover:text-ink";

/** Every page ends the same way: the shirts, help, the house and the small print, then the name, as big as it gets. */
export async function Footer() {
  const on = await shown();
  return (
    <footer className="mt-40 overflow-hidden" aria-label="Site">
      <div className="grid grid-cols-2 gap-x-4 gap-y-10 px-4 text-[14px] md:grid-cols-4 lg:grid-cols-12">
        <div className={`${col} lg:col-span-3`}>
          <p className="font-semibold">{CURRENT.title}</p>
          <ul className="mt-3 space-y-1">
            {shirtsOf(CURRENT).filter((d) => on.has(d)).map((d) => (
              <li key={d}><Link href={shirtHref(d)} className={link}>{shirtLabel(d)}</Link></li>
            ))}
            <li className="pt-2"><Link href={`/${CURRENT.slug}`} className="text-blue hover:text-ink">all five, with the shows →</Link></li>
          </ul>
        </div>
        <div className={`${col} lg:col-span-3`}>
          <p className="font-semibold">help</p>
          <ul className="mt-3 space-y-1">
            {HELP_LINKS.map((l) => <li key={l.href}><Link href={l.href} className={link}>{l.label}</Link></li>)}
            {shopOpen() ? <li><Link href="/order" className={link}>find your order</Link></li> : null}
          </ul>
        </div>
        <div className={`${col} lg:col-span-3`}>
          <p className="font-semibold">sahn</p>
          <ul className="mt-3 space-y-1">
            <li><Link href="/" className={link}>home</Link></li>
            <li><Link href="/shop" className={link}>shop</Link></li>
            <li><Link href="/made" className={link}>how it&apos;s made</Link></li>
          </ul>
        </div>
        {POLICY_LINKS.length ? (
          <div className={`${col} lg:col-span-3`}>
            <p className="font-semibold">policies</p>
            <ul className="mt-3 space-y-1">{POLICY_LINKS.map((l) => <li key={l.href}><Link href={l.href} className={link}>{l.label}</Link></li>)}</ul>
          </div>
        ) : null}
      </div>

      <p className="mt-16 max-w-[70ch] px-4 text-[13px] text-quiet">
        fan made. sahn is an independent label: these shirts are drawn by a fan for the shows, and are not official merchandise of fred again.., his team or the shows&apos; promoters.
      </p>

      <div className="mt-6 grid grid-cols-2 gap-x-4 px-4 text-[13px] text-quiet md:grid-cols-4">
        <span className={col}>© {new Date().getFullYear()} sahn</span>
        <span className={col}>made to order in india</span>
        <span className={`${col} hidden md:block`}>sent anywhere in {SHOP.where}</span>
        <span className={`${col} hidden text-right tnum md:block`}>v{pkg.version}</span>
      </div>

      <p aria-hidden className="bigword mt-10 -mb-[0.1em] px-3 text-[46vw] text-ink/95 whitespace-nowrap select-none">sahn</p>
    </footer>
  );
}
