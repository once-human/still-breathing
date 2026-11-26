import Link from "next/link";
import { COLOURS, DESIGNS, type Design } from "@/content/tee";
import { priceOf } from "@/content/shop";
import { rupees } from "@/lib/shop/money";
import { paperStill, shirtHref, shirtTitle, STILL_H, STILL_W } from "@/content/lineups";
import { CardArt } from "@/components/CardArt";

/**
 * One shirt in a grid: the back on the studio paper; point at it and the artwork itself loops, front then back
 * (CardArt). Stills only, never the 3D, so a page of them stays light.
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
        <CardArt d={d} />
        <span className="absolute top-2 left-2.5 text-[12px] text-black/60 tnum transition-colors duration-500 group-hover:opacity-0">{s.no}</span>
      </span>
      <span className={`mt-2 flex items-baseline justify-between gap-3 border-t border-line pt-1.5 ${big ? "text-[16px]" : "text-[14px]"}`}>
        <span className="min-w-0">
          <span className="block truncate font-semibold transition-colors group-hover:text-blue">{t.name}</span>
          <span className="block truncate text-quiet">{t.top}</span>
        </span>
        <span className="shrink-0 text-right">
          <span className="block tnum">{rupees(priceOf(d))}</span>
          <span className="flex items-center justify-end gap-1.5 text-[12px] text-quiet">
            <span className="inline-block h-2.5 w-2.5 rounded-full border border-line" style={{ background: COLOURS[s.colour].hex }} />
            {COLOURS[s.colour].name}
          </span>
        </span>
      </span>
    </Link>
  );
}
