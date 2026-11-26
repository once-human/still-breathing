"use client";

import { useRouter } from "next/navigation";
import type { Design, Size } from "@/content/tee";
import { notMade, priceIn, shop, useShop } from "@/lib/shop/client";
import { rupees } from "@/lib/shop/money";
import { BagDrawerHost } from "./BagDrawer";

/**
 * The buy controls for one shirt in the size picked: "add to bag · ₹1,270" (the main one) and "buy now" (into the
 * bag and straight to checkout). Always there; the bag works in the browser whether or not payment is connected,
 * and checkout says so plainly when it isn't. variant "bar": one slim row, for the fixed bar on phones.
 */
export function AddToBag({ design, size, variant }: { design: Design; size: Size; variant?: "bar" }) {
  const { pay } = useShop();
  const router = useRouter();
  const soldOut = pay?.status?.[design] === "soldout" || pay?.status?.[design] === "draft";
  const missing = soldOut || notMade(pay, design, size);
  const price = rupees(priceIn(pay, design));
  const bar = variant === "bar";
  const h = bar ? "h-11" : "h-12";

  const buyNow = () => {
    if (missing) return;
    shop.addQuietly(design, size);
    router.push("/checkout");
  };

  return (
    <div data-shop="add-to-bag" className={bar ? "flex gap-2" : "grid gap-2"}>
      <button
        type="button"
        onClick={() => !missing && shop.add(design, size)}
        disabled={missing}
        className={`${h} flex min-w-0 flex-1 items-center justify-between gap-3 bg-ink px-4 text-[15px] font-semibold text-paper transition hover:bg-ink/90 disabled:bg-transparent disabled:font-normal disabled:text-quiet disabled:ring-1 disabled:ring-line`}
      >
        <span className="truncate">{soldOut ? "sold out" : missing ? `not made in ${size}` : "add to bag"}</span>
        <span className="tnum">{price}</span>
      </button>
      <button
        type="button"
        onClick={buyNow}
        disabled={missing}
        className={`${h} ${bar ? "shrink-0 px-4" : "w-full px-4"} flex items-center justify-center border border-ink text-[15px] font-semibold text-ink transition hover:bg-ink hover:text-paper disabled:border-line disabled:text-quiet disabled:hover:bg-transparent`}
      >
        buy now
      </button>
      {!bar && <BagDrawerHost />}
    </div>
  );
}
