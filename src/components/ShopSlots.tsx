import type { Design, Size } from "@/content/tee";

/*
 * MOUNT POINTS FOR THE SHOP. The shop session (src/components/shop/) owns the buy controls:
 *   AddToBag  { design, size }  -> mounted on every shirt page, under the size picker (ShirtStage)
 *   BagButton                   -> mounted at the right end of the header (Header)
 * When they land, render them here and nothing else on the site changes. Until then both slots show nothing: no
 * teaser, no "soon" (everything on the site is real). Never build a second buy button outside these two slots.
 */

export function AddToBagSlot({ design, size }: { design: Design; size: Size }) {
  void design; void size;
  return null;
}

export function BagSlot() {
  return <span data-shop-slot="bag" className="text-quiet">&nbsp;</span>;
}
