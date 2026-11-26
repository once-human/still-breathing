import Link from "next/link";
import { CURRENT, shirtHref, shirtLabel, shirtsOf } from "@/content/lineups";
import { DESIGNS } from "@/content/tee";
import { HELP_LINKS, POLICY_LINKS } from "@/lib/site";
import pkg from "../../package.json";

const col = "border-t border-line pt-1.5";
const link = "text-quiet transition-colors hover:text-ink";

/** Every page ends the same way: the shirts, help, the house and the small print, then the name, as big as it gets. */
export function Footer() {
  return (
    <footer className="mt-40 overflow-hidden" aria-label="Site">
      <div className="grid grid-cols-2 gap-x-4 gap-y-10 px-4 text-[14px] md:grid-cols-4 lg:grid-cols-12">
        <div className={`${col} lg:col-span-3`}>
          <p className="font-semibold">lineup {CURRENT.no}</p>
          <ul className="mt-3 space-y-1">
            {shirtsOf(CURRENT).map((d) => (
              <li key={d}><Link href={shirtHref(d)} className={link}><span className="mr-2 tnum">{DESIGNS[d].no}</span>{shirtLabel(d)}</Link></li>
            ))}
            <li className="pt-2"><Link href={`/${CURRENT.slug}`} className="text-blue hover:text-ink">the whole lineup →</Link></li>
          </ul>
        </div>
        <div className={`${col} lg:col-span-3`}>
          <p className="font-semibold">help</p>
          <ul className="mt-3 space-y-1">{HELP_LINKS.map((l) => <li key={l.href}><Link href={l.href} className={link}>{l.label}</Link></li>)}</ul>
        </div>
        <div className={`${col} lg:col-span-3`}>
          <p className="font-semibold">still breathing</p>
          <ul className="mt-3 space-y-1">
            <li><Link href="/" className={link}>home</Link></li>
            <li><Link href="/lineups" className={link}>lineups</Link></li>
            <li><Link href="/made" className={link}>how it&apos;s made</Link></li>
          </ul>
        </div>
        <div className={`${col} lg:col-span-3`}>
          <p className="font-semibold">policies</p>
          <ul className="mt-3 space-y-1">{POLICY_LINKS.map((l) => <li key={l.href}><Link href={l.href} className={link}>{l.label}</Link></li>)}</ul>
        </div>
      </div>

      <p className="mt-16 max-w-[70ch] px-4 text-[13px] text-quiet">
        fan made. still breathing is an independent label: these shirts are drawn by a fan for the shows, and are not official merchandise of fred again.., his team or the shows&apos; promoters.
      </p>

      <div className="mt-6 grid grid-cols-2 gap-x-4 px-4 text-[13px] text-quiet md:grid-cols-4">
        <span className={col}>© {new Date().getFullYear()} still breathing</span>
        <span className={col}>made to order in india</span>
        <span className={`${col} hidden md:block`}>sent anywhere in india</span>
        <span className={`${col} hidden text-right tnum md:block`}>v{pkg.version}</span>
      </div>

      <p aria-hidden className="bigword mt-10 -mb-[0.12em] px-3 text-[17vw] text-ink/95 whitespace-nowrap select-none">still breathing</p>
    </footer>
  );
}
