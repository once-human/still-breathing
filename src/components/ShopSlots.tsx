"use client";

import { AddToBag, BagButton } from "@/components/shop";
import type { Design, Size } from "@/content/tee";

/*
 * Where the shop's controls sit on the site. The shop (src/components/shop/, owned by the shop session) draws them:
 *   AddToBag  { design, size }  -> every shirt page, under the size picker (ShirtStage)
 *   BagButton                   -> the right end of the header (Header)
 * Never build a second buy button outside these two slots.
 */

export function AddToBagSlot({ design, size }: { design: Design; size: Size }) {
  return <AddToBag design={design} size={size} />;
}

export function BagSlot() {
  return <BagButton />;
}
