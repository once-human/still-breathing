"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SHOP } from "@/content/shop";

const day = (t: number) => new Date(t).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).toLowerCase().replace(",", "");

/**
 * What a buyer wants to know right under the button, in plain words: when it arrives (worked out from today, the
 * making days and the days on the road, with a weekend's slack), that delivery is free, what happens if something's
 * wrong, and the size guide. No pressure, no countdown to buy.
 */
export function BuyFacts() {
  const [range, setRange] = useState<string | null>(null);
  useEffect(() => {
    const now = Date.now(), D = 86_400_000;
    const from = now + (SHOP.make[0] + SHOP.road[0]) * D, to = now + (SHOP.make[1] + SHOP.road[1] + 2) * D;
    setRange(`${day(from)} – ${day(to)}`);
  }, []);
  return (
    <ul data-seen="delivery and returns" className="mt-4 space-y-2 text-[13px]">
      <li className="flex gap-3">
        <Mark d="M2 6.5h8.5v6H2zM10.5 8.5h2.6l1.9 2.2v1.8h-4.5M4.5 14.5a1.2 1.2 0 1 0 0-.01M12.5 14.5a1.2 1.2 0 1 0 0-.01" />
        <span>order today, usually with you <span className="font-semibold text-ink tnum">{range ?? "in about 10 days"}</span><span className="block text-quiet">free delivery anywhere in {SHOP.where}. made for you first, then sent with tracking.</span></span>
      </li>
      <li className="flex gap-3">
        <Mark d="M8 2.2 13.5 4.4v3.8c0 3.1-2.3 5.1-5.5 6-3.2-.9-5.5-2.9-5.5-6V4.4zM5.7 8.2l1.6 1.6 3-3.1" />
        <span>something wrong with it when it comes? we make it right.<span className="block text-quiet">it&apos;s made for you, so there are no returns for a change of mind.</span></span>
      </li>
      <li className="flex gap-3">
        <Mark d="M2 5.5h12v5H2zM4.5 5.5v2M7 5.5v3M9.5 5.5v2M12 5.5v3" />
        <span>not sure of your size? <Link href="/size-guide" className="draw font-semibold hover:text-blue">size guide</Link><span className="block text-quiet">cut big: most people take their usual size.</span></span>
      </li>
    </ul>
  );
}

/** a small line drawing, 16 px, in the quiet colour */
function Mark({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden className="mt-[1px] size-4 shrink-0 text-quiet" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>
  );
}
