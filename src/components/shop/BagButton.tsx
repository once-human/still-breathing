"use client";

import { shop, useShop } from "@/lib/shop/client";
import { BagDrawerHost } from "./BagDrawer";

/** The header's bag: "bag" and how many shirts are in it; opens the bag. Nothing at all while the shop isn't open. */
export function BagButton({ className = "" }: { className?: string }) {
  const { catalog, bag } = useShop();
  if (!catalog?.open) return <span className={`text-quiet ${className}`} aria-hidden>&nbsp;</span>;
  return (
    <>
      <button type="button" onClick={shop.open} className={`hit hover:text-ink ${className}`} aria-label={`Bag, ${bag.count} ${bag.count === 1 ? "shirt" : "shirts"}`}>
        bag<span className="tnum text-quiet"> · {bag.count}</span>
      </button>
      <BagDrawerHost />
    </>
  );
}
