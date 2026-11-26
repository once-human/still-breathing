"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { POLICIES_READY } from "@/content/policies";
import { SHOP } from "@/content/shop";
import { DESIGNS } from "@/content/tee";
import { bagCount, bagTotal, claimDrawer, releaseDrawer, shop, useShop } from "@/lib/shop/client";
import { rupees } from "@/lib/shop/money";

/** Mount anywhere; only one on the page draws (the bag button and every buy button include it). */
export function BagDrawerHost() {
  const [mine, setMine] = useState(false);
  useEffect(() => {
    const me = Symbol("drawer");
    claimDrawer(me, setMine);
    return () => releaseDrawer(me);
  }, []);
  return mine ? createPortal(<BagDrawer />, document.body) : null;
}

export const shirtName = (d: keyof typeof DESIGNS) => `${DESIGNS[d].no} ${DESIGNS[d].name}${DESIGNS[d].city ? ` ${DESIGNS[d].city}` : ""}`;

/** The bag: what's in it, how many of each, what it comes to, and on to checkout. */
function BagDrawer() {
  const { bag, catalog, drawer } = useShop();
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!drawer) return;
    const back = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") shop.close(); };
    window.addEventListener("keydown", key);
    const html = document.documentElement, was = html.style.overflow;
    html.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", key);
      html.style.overflow = was;
      back?.focus?.();
    };
  }, [drawer]);

  if (!drawer || !catalog?.open) return null;
  const n = bagCount(bag), full = n >= catalog.maxPerBag;
  const [m0, m1] = SHOP.make, [r0, r1] = SHOP.road;
  return (
    <div className="fixed inset-0 z-[100]" data-lenis-prevent>
      <button aria-label="Close the bag" onClick={shop.close} className="absolute inset-0 cursor-default bg-black/60 backdrop-blur-[2px]" tabIndex={-1} />
      <div ref={panel} tabIndex={-1} role="dialog" aria-modal="true" aria-label="Your bag"
        className="absolute inset-y-0 right-0 flex w-full max-w-[420px] flex-col border-l border-line bg-paper px-4 pt-3 pb-4 outline-none">
        <div className="flex items-baseline justify-between border-t border-line pt-1.5 text-[14px]">
          <p className="font-semibold">bag<span className="tnum font-normal text-quiet"> · {n}</span></p>
          <button onClick={shop.close} className="hit text-quiet hover:text-ink">close</button>
        </div>

        {bag.length === 0 ? (
          <p className="mt-8 text-quiet">nothing in it yet.</p>
        ) : (
          <ul className="mt-6 flex-1 overflow-y-auto">
            {bag.map((l) => {
              const name = shirtName(l.design), price = catalog.shirts[l.design]?.price ?? 0;
              return (
                <li key={`${l.design}-${l.size}`} className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-2 border-t border-line py-3 text-[14px]">
                  <p className="font-semibold">{name}<span className="block font-normal text-quiet">size {l.size}</span></p>
                  <p className="tnum text-right">{rupees(price * l.quantity)}</p>
                  <div className="flex items-center gap-1" role="group" aria-label={`How many ${name} in ${l.size}`}>
                    <button onClick={() => shop.setQuantity(l.design, l.size, l.quantity - 1)} aria-label="One fewer" className="h-8 w-8 border border-line hover:border-quiet">−</button>
                    <span className="tnum w-8 text-center" aria-live="polite">{l.quantity}</span>
                    <button disabled={full || l.quantity >= catalog.maxPerLine} onClick={() => shop.setQuantity(l.design, l.size, l.quantity + 1)} aria-label="One more"
                      className="h-8 w-8 border border-line hover:border-quiet disabled:opacity-40">+</button>
                  </div>
                  <button onClick={() => shop.setQuantity(l.design, l.size, 0)} className="hit text-right text-[13px] text-quiet hover:text-ink">remove</button>
                </li>
              );
            })}
          </ul>
        )}

        {bag.length > 0 && (
          <div className="mt-auto border-t border-line pt-3">
            <p className="flex items-baseline justify-between text-[15px]"><span>total</span><span className="tnum font-semibold">{rupees(bagTotal(bag, catalog))}</span></p>
            <p className="mt-1 text-[12px] text-quiet">GST included. Free shipping across {SHOP.shipsTo}. Made for you: {m0}–{m1} days to make, then {r0}–{r1} on the road.</p>
            <Link href="/checkout" onClick={shop.close}
              className="mt-4 flex h-12 w-full items-center justify-between bg-ink px-4 text-[15px] font-semibold text-paper transition hover:bg-ink/90">
              <span>checkout</span><span aria-hidden>→</span>
            </Link>
            <p className="mt-2 text-[12px] text-quiet">
              Pay by UPI, card or net banking.{POLICIES_READY ? <> <Link href="/policies/refunds" onClick={shop.close} className="draw hover:text-ink">returns</Link></> : null}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
