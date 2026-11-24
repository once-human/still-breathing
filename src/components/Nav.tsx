"use client";

import { Countdown } from "@/components/Countdown";

type Show = "all" | "md" | "lg";
const SHOW: Record<Show, string> = { all: "block", md: "hidden md:block", lg: "hidden lg:block" };
const ITEMS: { id: string; label: string; show: Show }[] = [
  { id: "studio", label: "the tee", show: "all" },
  { id: "sizes", label: "sizes", show: "all" },
  { id: "cloth", label: "cloth", show: "md" },
  { id: "care", label: "care", show: "md" },
  { id: "shows", label: "shows", show: "lg" },
];
const cell = "border-t border-line pt-1.5 truncate";

/** A contents line like 1618's: a rule above each item, the next show at the end. */
export function Nav() {
  const go = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  return (
    <nav aria-label="Main" className="fixed inset-x-0 top-0 z-50 grid grid-cols-4 gap-3 bg-paper px-4 pt-3 pb-2 text-[13px] sm:gap-4 sm:text-[15px] md:grid-cols-7 lg:grid-cols-9">
      <a href="#top" onClick={go("top")} className={`${cell} font-semibold`}>still breathing</a>
      <span className={`${cell} ${SHOW.lg} text-quiet`}>lineup 01</span>
      {ITEMS.map((i) => (
        <a key={i.id} href={`#${i.id}`} onClick={go(i.id)} className={`${cell} ${SHOW[i.show]}`}>{i.label}</a>
      ))}
      <a href="/made" className={`${cell} ${SHOW.lg} text-quiet hover:text-ink`}>how it&apos;s made</a>
      <span className={`${cell} tnum text-right md:text-left`}><Countdown short /></span>
    </nav>
  );
}
