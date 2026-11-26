"use client";

import { bagCount, shop, useShop } from "@/lib/shop/client";
import { BagDrawerHost } from "./BagDrawer";

/** The header's bag: "bag · 2", opening the bag. Nothing while the shop can't take orders. */
export function BagButton({ className = "" }: { className?: string }) {
  const { catalog, bag } = useShop();
  if (!catalog?.open) return null;
  const n = bagCount(bag);
  return (
    <>
      <button type="button" onClick={shop.open} className={`hit hover:text-ink ${className}`} aria-label={`Bag, ${n} ${n === 1 ? "shirt" : "shirts"}`}>
        bag<span className="tnum text-quiet"> · {n}</span>
      </button>
      <BagDrawerHost />
    </>
  );
}
