"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { setFocusCity } from "@/lib/city";
import { Viewer, warmDesign } from "@/components/Viewer";
import { Countdown } from "@/components/Countdown";
import { Fit, SHOP, WEARERS, type Wearer } from "@/components/Fit";
import { AddToBagSlot } from "@/components/ShopSlots";
import { priceIn, useShop } from "@/lib/shop/client";
import { BuyFacts } from "@/components/BuyFacts";
import { rupees } from "@/lib/shop/money";
import type { Variant } from "@/lib/viewer/raster";
import { COLOURS, DESIGNS, SIZES, SIZE_ORDER, THE_TEE, type Design, type Size } from "@/content/tee";
import { fmtDays, lineupOf, paperStill, shirtBySlug, shirtHref, shirtTitle, STILL_H, STILL_W } from "@/content/lineups";

/**
 * The shirt page: the tee in 3D on the left; on the right its name, price, what's on it, the size and the buy button,
 * and on a phone a buy bar that stays at the bottom once that button has scrolled away. It lives in the shirts'
 * layout, so going from one shirt to the next keeps the 3D running and only swaps the shirt on it.
 */
export function ShirtStage({ hidden = [] }: { hidden?: Design[] }) {
  const { pay } = useShop();
  const params = useParams<{ lineup: string; shirt: string }>();
  const lineup = lineupOf(params.lineup);
  const design = lineup ? shirtBySlug(lineup, params.shirt) : undefined;

  const [size, setSize] = useState<Size>("M");
  const [variant, setVariant] = useState<Variant>(SHOP);
  const [wearer, setWearer] = useState<Wearer>("him");
  const [shot, setShot] = useState("tee");
  const [barOn, setBarOn] = useState(false);
  const buyRef = useRef<HTMLDivElement>(null);
  const fromStage = useRef(false);
  const first = useRef(true);

  // a shirt page always opens at its top, on the tee (never part way down)
  useEffect(() => { if (!location.hash) requestAnimationFrame(() => scrollTo({ top: 0 })); }, []);
  // the phone's buy bar shows once the buy button itself is out of sight above
  useEffect(() => {
    const el = buyRef.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => setBarOn(!e.isIntersecting && e.boundingClientRect.top < 0));
    io.observe(el);
    return () => io.disconnect();
  }, [design]);

  // the page follows this shirt's city (countdown, the sky); a lineup-wide shirt follows the visitor's nearest show
  useEffect(() => { if (design) setFocusCity(DESIGNS[design].city ?? null); }, [design]);
  // a shirt picked from anywhere but the stage starts at the top; picked here, you stay where you are
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    if (!fromStage.current) requestAnimationFrame(() => scrollTo({ top: 0 }));
    fromStage.current = false;
  }, [design]);

  if (!lineup || !design || hidden.includes(design)) return null;
  const s = DESIGNS[design], tee = s.colour, t = shirtTitle(design), z = SIZES[size];
  const group = lineup.groups.find((g) => g.shirts.includes(design))!;
  const all = lineup.groups.flatMap((g) => g.shirts).filter((d) => !hidden.includes(d));

  return (
    <section aria-label={`${t.top} ${t.name}`} className="grid grid-cols-1 gap-x-4 gap-y-8 px-4 pt-4 md:grid-cols-12">
      <div className="page-in md:col-span-7 lg:col-span-7">
        <Viewer design={design} tee={tee} variant={variant} onShot={setShot} />
        <div className={`mt-2 items-baseline gap-4 text-[13px] ${shot === "worn" ? "flex" : "hidden"}`} role="group" aria-label="Worn by">
          <span className="text-quiet">worn by</span>
          {(Object.keys(WEARERS) as Wearer[]).map((w) => (
            <button key={w} onClick={() => setWearer(w)} aria-pressed={w === wearer}
              className={`hit ${w === wearer ? "border-b border-blue font-semibold text-ink" : "text-quiet hover:text-ink"}`}>{w}</button>
          ))}
        </div>
      </div>

      <div className="page-in-2 md:col-span-5 lg:col-span-4 lg:col-start-9">
        <div className="md:sticky md:top-28">
          <nav aria-label="Breadcrumb" className="border-t border-line pt-1.5 text-[13px] text-quiet">
            <Link href={`/${lineup.slug}`} className="draw hover:text-ink">{lineup.title}</Link>
            <span className="mx-1.5">/</span>{group.label}
          </nav>

          <h1 className="mt-5 text-[46px] leading-[0.88] font-extrabold tracking-[-0.045em] lg:text-[68px]">
            {t.top}<span className="block text-quiet">{t.name}</span>
          </h1>
          <p className="mt-5 flex items-baseline gap-3">
            <span className="text-[28px] font-extrabold tracking-[-0.03em] tnum">{rupees(priceIn(pay, design))}</span>
            <span className="text-[13px] text-quiet">all taxes and shipping included</span>
          </p>
          <p className="mt-4 max-w-[40ch] text-ink/85">{s.about}</p>

          <p className="mt-5 flex items-center gap-2 text-[13px]">
            <span className="inline-block h-3 w-3 rounded-full border border-line" style={{ background: COLOURS[tee].hex }} />
            <span>{COLOURS[tee].name}<span className="text-quiet">, the only colour this one comes in</span></span>
          </p>

          <div className="mt-8 border-t border-line pt-1.5">
            <div className="flex items-baseline justify-between text-[13px]">
              <p className="text-quiet">size · <span className="text-ink">{size}</span></p>
              <Link href="/size-guide" className="draw text-quiet hover:text-ink">size guide</Link>
            </div>
            <div className="mt-3 grid grid-cols-6 gap-1.5" role="radiogroup" aria-label="Size">
              {SIZE_ORDER.map((x) => (
                <button key={x} role="radio" aria-checked={x === size} onClick={() => setSize(x)}
                  className={`h-11 border text-[14px] transition-colors duration-200 ${x === size ? "border-ink bg-ink text-paper" : "border-line hover:border-quiet"}`}>{x}</button>
              ))}
            </div>
            <dl className="mt-4 grid grid-cols-3 gap-2 text-[13px] tnum">
              {([["chest", z.chest_round], ["length", z.length], ["shoulder", z.shoulder]] as const).map(([k, v]) => (
                <div key={k}><dt className="text-quiet">{k}</dt><dd className="text-[20px] font-semibold">{v}<span className="text-[13px] font-normal text-quiet"> cm</span></dd></div>
              ))}
            </dl>
            <p className="mt-2 text-[12px] text-quiet">measured on the garment, in cm.</p>
          </div>

          <div ref={buyRef} className="mt-6"><AddToBagSlot design={design} size={size} /></div>
          <BuyFacts />

          <Fit size={size} shop={WEARERS[wearer]} onVariant={setVariant} />

          <details className="group/d mt-8 border-t border-line pt-1.5 text-[13px]">
            <summary className="flex cursor-pointer list-none items-baseline justify-between text-quiet hover:text-ink [&::-webkit-details-marker]:hidden">
              <span>cloth and care</span><span className="transition-transform group-open/d:rotate-45">+</span>
            </summary>
            <dl className="mt-3 space-y-1.5">
              {THE_TEE.cloth.map(([k, v]) => <div key={k} className="grid grid-cols-[5.5rem_1fr] gap-3"><dt className="text-quiet">{k}</dt><dd>{v}</dd></div>)}
            </dl>
            <ul className="mt-4 space-y-0.5">{THE_TEE.care.map((c) => <li key={c}>{c}</li>)}</ul>
          </details>

          <div className="mt-8 border-t border-line pt-1.5 text-[13px]">
            <p className="text-quiet">{lineup.title} · the other shirts</p>
            <ul className="mt-3 grid grid-cols-5 gap-1.5">
              {all.map((d) => (
                <li key={d}>
                  <Link
                    href={shirtHref(d)} scroll={false} aria-current={d === design ? "page" : undefined}
                    onClick={() => { fromStage.current = true; }} onPointerEnter={() => warmDesign(d)} onFocus={() => warmDesign(d)}
                    className={`group block ${d === design ? "" : "opacity-70 hover:opacity-100"}`} title={`${shirtTitle(d).top} ${shirtTitle(d).name}`}
                  >
                    <img src={paperStill(d, "back")} alt="" width={STILL_W} height={STILL_H} loading="lazy" className={`aspect-[880/1120] w-full bg-studio object-cover ${d === design ? "ring-[1.5px] ring-ink ring-offset-2 ring-offset-paper" : ""}`} />
                    <span className="mt-1 block truncate text-[11px] text-quiet tnum group-hover:text-ink">{DESIGNS[d].no} {DESIGNS[d].name}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-8 border-t border-line pt-1.5 text-[13px]">
            <p className="text-quiet">the shows</p>
            <ul className="mt-2 space-y-0.5 tnum">
              {lineup.shows.map((x) => (
                <li key={x.city} className={`flex justify-between ${s.city && x.city !== s.city ? "text-quiet" : ""}`}><span>{x.city}</span><span className="text-quiet">{fmtDays(x.days)}</span></li>
              ))}
            </ul>
            <p className="mt-3 flex items-center gap-2"><span className="inline-block h-1.5 w-1.5 rounded-full bg-blue" /><Countdown /></p>
          </div>
        </div>
      </div>

      {/* phones: once the buy button has scrolled away, the shirt, its size and the button stay at the bottom */}
      <div className={`fixed inset-x-0 bottom-0 z-40 border-t border-line bg-paper/95 px-4 pt-2 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur-md transition-transform duration-500 ease-[cubic-bezier(.2,.7,.2,1)] md:hidden ${barOn ? "" : "translate-y-full"}`} inert={!barOn}>
        <p className="mb-2 truncate text-[13px]"><span className="font-semibold">{t.name}</span><span className="text-quiet"> · {t.top} · size {size}</span></p>
        <AddToBagSlot design={design} size={size} bar />
      </div>
    </section>
  );
}
