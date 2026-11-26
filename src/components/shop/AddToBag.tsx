"use client";

import { OPENING_SOON, SHOP } from "@/content/shop";
import type { Design, Size } from "@/content/tee";
import { shop, useShop } from "@/lib/shop/client";
import { rupees } from "@/lib/shop/money";
import { BagDrawerHost } from "./BagDrawer";

/**
 * The buy button for one shirt in one size. It shows Shopify's price and puts the shirt in the bag; until the shop
 * has its keys (or while Shopify can't be reached) it reads "opening soon" and does nothing, never a pretend checkout.
 */
export function AddToBag({ design, size }: { design: Design; size: Size }) {
  const { catalog, busy, error, drawer } = useShop();
  const shirt = catalog?.open ? catalog.shirts[design] : undefined;
  const loading = catalog === null;
  const open = !!shirt;
  const canBuy = open && shirt.sizes[size] === true;
  const price = shirt?.price ?? SHOP.price;
  const label = loading ? "\u00a0" : !open ? OPENING_SOON : shirt.sizes[size] === undefined ? `not made in ${size}` : !canBuy ? `${size} sold out` : busy ? "adding.." : "add to bag";

  return (
    <div data-shop="add-to-bag">
      <button
        type="button"
        onClick={() => canBuy && shop.add(design, size)}
        disabled={!canBuy || busy}
        aria-disabled={!canBuy}
        className={`flex h-12 w-full items-center justify-between px-4 text-[15px] transition ${canBuy ? "bg-ink font-semibold text-paper hover:bg-ink/90" : "border border-line text-quiet"} ${loading ? "opacity-60" : ""}`}
      >
        <span>{label}</span>
        <span className="tnum">{rupees(price)}</span>
      </button>
      {error && !drawer && <p role="alert" className="mt-2 text-[13px]">{error}</p>}
      <BagDrawerHost />
    </div>
  );
}
