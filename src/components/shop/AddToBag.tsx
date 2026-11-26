"use client";

import type { Design, Size } from "@/content/tee";
import { shop, useShop } from "@/lib/shop/client";
import { rupees } from "@/lib/shop/money";
import { BagDrawerHost } from "./BagDrawer";

/**
 * The buy button for one shirt in one size: its price, and into the bag. While the shop can't take an order (its
 * payment and printing aren't set up, or this shirt isn't) nothing is drawn at all: no teaser, no pretend button.
 */
export function AddToBag({ design, size }: { design: Design; size: Size }) {
  const { catalog } = useShop();
  const shirt = catalog?.open ? catalog.shirts[design] : undefined;
  if (!shirt) return null;
  const can = shirt.sizes.includes(size);
  return (
    <div data-shop="add-to-bag">
      <button
        type="button"
        onClick={() => can && shop.add(design, size)}
        disabled={!can}
        className={`flex h-12 w-full items-center justify-between px-4 text-[15px] transition ${can ? "bg-ink font-semibold text-paper hover:bg-ink/90" : "border border-line text-quiet"}`}
      >
        <span>{can ? "add to bag" : `not made in ${size}`}</span>
        <span className="tnum">{rupees(shirt.price)}</span>
      </button>
      <BagDrawerHost />
    </div>
  );
}
