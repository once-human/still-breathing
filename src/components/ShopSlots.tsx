import type { Design, Size } from "@/content/tee";

/*
 * MOUNT POINTS FOR THE SHOP. The shop session (src/components/shop/) owns the buy controls:
 *   AddToBag  { design, size }  -> mounted on every shirt page, under the size picker (ShirtStage)
 *   BagButton                   -> mounted at the right end of the header (Header)
 * When they land, render them here and nothing else on the site changes. Until then the shirt page says orders
 * aren't open yet and the header's bag cell stays empty. Never build a second buy button outside these two slots.
 */

export function AddToBagSlot({ design, size }: { design: Design; size: Size }) {
  void design; void size;
  return (
    <div className="flex h-12 items-center justify-between border border-line px-4 text-[14px]" data-shop-slot="add-to-bag">
      <span className="font-semibold">add to bag</span>
      <span className="text-quiet">orders open soon</span>
    </div>
  );
}

export function BagSlot() {
  return <span data-shop-slot="bag" className="text-quiet">&nbsp;</span>;
}
