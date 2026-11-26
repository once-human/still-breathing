"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { SHOP } from "@/content/shop";
import { claimDrawer, releaseDrawer, shop, useShop } from "@/lib/shop/client";
import { rupees } from "@/lib/shop/money";

/** Mount anywhere; only the first one on the page draws (the bag button and every buy button include it). */
export function BagDrawerHost() {
  const [mine, setMine] = useState(false);
  useEffect(() => {
    const me = Symbol("drawer");
    claimDrawer(me, setMine);
    return () => releaseDrawer(me);
  }, []);
  return mine ? createPortal(<BagDrawer />, document.body) : null;
}

/** The bag: what's in it, how many of each, the total Shopify gives, and the way to pay. */
function BagDrawer() {
  const { bag, busy, error, drawer } = useShop();
  const panel = useRef<HTMLDivElement>(null);
  const back = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!drawer) return;
    back.current = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") shop.close(); };
    window.addEventListener("keydown", key);
    const html = document.documentElement, was = html.style.overflow;
    html.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", key);
      html.style.overflow = was;
      back.current?.focus?.();
    };
  }, [drawer]);

  if (!drawer) return null;
  const [m0, m1] = SHOP.make, [r0, r1] = SHOP.road;
  return (
    <div className="fixed inset-0 z-[100]" data-lenis-prevent>
      <button aria-label="Close the bag" onClick={shop.close} className="absolute inset-0 cursor-default bg-black/60 backdrop-blur-[2px]" tabIndex={-1} />
      <div ref={panel} tabIndex={-1} role="dialog" aria-modal="true" aria-label="Your bag"
        className="absolute inset-y-0 right-0 flex w-full max-w-[420px] flex-col border-l border-line bg-paper px-4 pt-3 pb-4 outline-none">
        <div className="flex items-baseline justify-between border-t border-line pt-1.5 text-[14px]">
          <p className="font-semibold">bag<span className="tnum font-normal text-quiet"> · {bag.count}</span></p>
          <button onClick={shop.close} className="hit text-quiet hover:text-ink">close</button>
        </div>

        {bag.lines.length === 0 ? (
          <p className="mt-8 text-quiet">nothing in it yet.</p>
        ) : (
          <ul className="mt-6 flex-1 overflow-y-auto">
            {bag.lines.map((l) => (
              <li key={l.id} className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-2 border-t border-line py-3 text-[14px]">
                <p className="font-semibold">{l.name}<span className="block font-normal text-quiet">size {l.size}</span></p>
                <p className="tnum text-right">{rupees(l.total)}</p>
                <div className="flex items-center gap-1" role="group" aria-label={`How many ${l.name} in ${l.size}`}>
                  <button disabled={busy} onClick={() => shop.setQuantity(l.design, l.size, l.quantity - 1)} aria-label="One fewer"
                    className="h-8 w-8 border border-line hover:border-quiet disabled:opacity-40">−</button>
                  <span className="tnum w-8 text-center" aria-live="polite">{l.quantity}</span>
                  <button disabled={busy || l.quantity >= SHOP.maxPerLine || bag.count >= SHOP.maxPerBag} onClick={() => shop.setQuantity(l.design, l.size, l.quantity + 1)} aria-label="One more"
                    className="h-8 w-8 border border-line hover:border-quiet disabled:opacity-40">+</button>
                </div>
                <button disabled={busy} onClick={() => shop.setQuantity(l.design, l.size, 0)} className="hit text-right text-[13px] text-quiet hover:text-ink disabled:opacity-40">remove</button>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-auto border-t border-line pt-3">
          {error && <p role="alert" className="mb-3 text-[13px] text-ink">{error}</p>}
          {bag.lines.length > 0 && (
            <>
              <p className="flex items-baseline justify-between text-[15px]"><span>total</span><span className="tnum font-semibold">{rupees(bag.subtotal)}</span></p>
              <p className="mt-1 text-[12px] text-quiet">GST included. Free shipping across {SHOP.shipsTo}. Made for you: {m0}–{m1} days to make, then {r0}–{r1} on the road.</p>
              <button onClick={shop.checkout} disabled={busy}
                className="mt-4 flex h-12 w-full items-center justify-between bg-ink px-4 text-[15px] font-semibold text-paper transition hover:bg-ink/90 disabled:opacity-60">
                <span>{busy ? "one moment.." : "checkout"}</span><span aria-hidden>→</span>
              </button>
              <p className="mt-2 text-[12px] text-quiet">
                You pay on a secure checkout by UPI, card, net banking or wallet. <Link href="/help#shipping" onClick={shop.close} className="draw hover:text-ink">shipping and returns</Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
