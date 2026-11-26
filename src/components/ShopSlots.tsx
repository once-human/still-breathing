"use client";

import { AccountButton, AddToBag, BagButton } from "@/components/shop";
import type { Design, Size } from "@/content/tee";

/*
 * Where the shop's controls sit on the site. The shop (src/components/shop/, owned by the shop session) draws them:
 *   AddToBag  { design, size }  -> every shirt page, under the size picker (ShirtStage)
 *   BagButton                   -> the right end of the header (Header)
 *   AccountButton               -> beside the bag, and in the phone menu (nothing until accounts are set up)
 * Never build a second buy button outside these two slots.
 */

/** `bar`: the slim one-row pair for the phone's bottom bar (it doesn't host the bag drawer; the header's bag does) */
export function AddToBagSlot({ design, size, bar = false }: { design: Design; size: Size; bar?: boolean }) {
  return <AddToBag design={design} size={size} variant={bar ? "bar" : undefined} />;
}

export function BagSlot() {
  return <BagButton />;
}

export function AccountSlot({ className = "" }: { className?: string }) {
  return <AccountButton className={className} />;
}
