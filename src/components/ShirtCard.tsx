import Link from "next/link";
import { COLOURS, DESIGNS, type Design } from "@/content/tee";
import { paperStill, shirtHref, shirtTitle, wornStill, STILL_H, STILL_W } from "@/content/lineups";

/**
 * One shirt in a grid: the back on the studio paper; point at it and it's worn at the show. Stills only, never the 3D,
 * so a page of them stays light.
 */
export function ShirtCard({ d, eager = false, big = false }: { d: Design; eager?: boolean; big?: boolean }) {
  const t = shirtTitle(d), s = DESIGNS[d];
  return (
    <Link href={shirtHref(d)} className="group block focus-visible:outline-offset-4">
      <span className="relative block overflow-hidden bg-studio">
        <img
          src={paperStill(d, "back")} alt={`${t.top} ${t.name}, the back`} width={STILL_W} height={STILL_H}
          loading={eager ? "eager" : "lazy"} decoding="async" fetchPriority={eager ? "high" : "auto"}
          className="aspect-[880/1120] w-full object-cover transition-transform duration-[1.2s] ease-[cubic-bezier(.2,.7,.2,1)] group-hover:scale-[1.03]"
        />
        <img
          src={wornStill(d, 180)} alt="" width={STILL_W} height={STILL_H} loading="lazy" decoding="async"
          className="absolute inset-0 h-full w-full object-cover opacity-0 transition-opacity duration-700 ease-out group-hover:opacity-100 group-focus-visible:opacity-100"
        />
        <span className="absolute top-2 left-2.5 text-[12px] text-black/60 tnum transition-colors duration-700 group-hover:text-white/70">{s.no}</span>
      </span>
      <span className={`mt-2 flex items-baseline justify-between gap-3 border-t border-line pt-1.5 ${big ? "text-[16px]" : "text-[14px]"}`}>
        <span className="min-w-0">
          <span className="block truncate font-semibold transition-colors group-hover:text-blue">{t.name}</span>
          <span className="block truncate text-quiet">{t.top}</span>
        </span>
        <span className="flex shrink-0 items-center gap-1.5 text-[12px] text-quiet">
          <span className="inline-block h-2.5 w-2.5 rounded-full border border-line" style={{ background: COLOURS[s.colour].hex }} />
          {COLOURS[s.colour].name}
        </span>
      </span>
    </Link>
  );
}
