"use client";

import { useRouter } from "next/navigation";
import { shop } from "@/lib/shop/client";
import type { BagItem } from "@/lib/shop/types";

/** the same shirts and sizes back in the bag, then checkout (priced again there, at today's price) */
export function Reorder({ lines, className = "" }: { lines: BagItem[]; className?: string }) {
  const router = useRouter();
  return (
    <button type="button" className={`hit hover:text-ink ${className}`} onClick={() => { shop.addLines(lines.map(({ design, size, quantity }) => ({ design, size, quantity }))); router.push("/checkout"); }}>
      order these again
    </button>
  );
}
