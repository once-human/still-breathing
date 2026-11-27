"use client";

import Link from "next/link";
import { usePoll } from "../ui/client";

type Count = { now: number; hour: number; today: number; yesterday: number };

/** the home page's live line: on the site now, this hour, today against yesterday, every 10 seconds */
export function LiveStrip({ initial }: { initial: Count }) {
  const { data: c } = usePoll<Count>("/api/admin/live?count=1", 10_000, initial);
  const diff = c.today - c.yesterday;
  return (
    <Link href="/admin/live" className="mb-8 flex flex-wrap items-center gap-x-8 gap-y-2 rounded-xl border border-line px-4 py-3 text-[13px] transition hover:border-quiet">
      <span className="flex items-center gap-2 font-semibold">
        <span className="relative flex h-2.5 w-2.5">
          {c.now ? <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#8fd19e] opacity-60" /> : null}
          <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${c.now ? "bg-[#8fd19e]" : "bg-ink/20"}`} />
        </span>
        <span className="tnum text-[18px]">{c.now}</span> on the site now
      </span>
      <span className="text-quiet"><span className="tnum text-ink">{c.hour}</span> this hour</span>
      <span className="text-quiet">
        <span className="tnum text-ink">{c.today}</span> people today
        <span className={`ml-1.5 text-[12px] ${diff > 0 ? "text-[#8fd19e]" : diff < 0 ? "text-[#f0a35b]" : ""}`}>{diff > 0 ? `${diff} more than` : diff < 0 ? `${-diff} fewer than` : "same as"} yesterday ({c.yesterday})</span>
      </span>
      <span className="ml-auto text-[12px] text-quiet">watch live →</span>
    </Link>
  );
}
