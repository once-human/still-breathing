"use client";

import Link from "next/link";
import { span } from "@/lib/visits/shared";
import type { LiveVisit } from "@/lib/visits/server";
import { STEP_WORD } from "@/lib/visits/shared";
import { usePoll } from "../../ui/client";
import { Reached, Trail, pageName, shirtLabel, where } from "../../ui/visits";

type Data = { people: LiveVisit[]; count: { now: number; hour: number; today: number } };

/** who is on the site now, every 5 seconds */
export function Live({ initial }: { initial: Data }) {
  const { data, at } = usePoll<Data>("/api/admin/live", 5000, initial);
  const c = data.count;
  return (
    <>
      <div className="mb-8 grid grid-cols-3 gap-4">
        {([["on the site now", c.now, true], ["in the last hour", c.hour, false], ["today", c.today, false]] as const).map(([l, n, live]) => (
          <div key={l} className="rounded-xl border border-line p-4">
            <div className="text-[12px] text-quiet">{l}</div>
            <div className={`tnum mt-1 text-[34px] font-bold leading-none ${live && n ? "text-[#8fd19e]" : ""}`}>{n}</div>
          </div>
        ))}
      </div>
      <p className="mb-3 text-[12px] text-quiet">updates every 5 seconds{at ? ` · last ${new Date(at).toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata" })}` : ""} · someone counts as here for a minute after their last move</p>
      {data.people.length ? (
        <ul className="grid gap-3">
          {data.people.map((v) => (
            <li key={v.id} className="rounded-xl border border-line p-4 transition hover:border-quiet">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2 text-[15px] font-semibold">
                    <span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#8fd19e] opacity-60" /><span className="relative inline-flex h-2 w-2 rounded-full bg-[#8fd19e]" /></span>
                    on <span className="text-blue">{pageName(v.now)}</span>
                    <Reached steps={v.reached} />
                  </div>
                  <div className="mt-1 text-[12px] text-quiet">
                    {where(v)} · {v.device} · from {v.referrer ?? "direct"} · {v.nth && v.nth > 1 ? `visit ${v.nth}` : "first visit"} · here {span(Date.now() - Date.parse(v.startedAt))}, {v.pages} page{v.pages === 1 ? "" : "s"}
                  </div>
                </div>
                <Link href={`/admin/visitors/${v.id}`} className="shrink-0 text-[12px] text-quiet underline decoration-line underline-offset-4 hover:text-ink">every step →</Link>
              </div>
              <div className="mt-3 text-[12px]"><Trail trail={v.trail} max={8} /></div>
              {v.bag.length || v.last ? (
                <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-[12px]">
                  {v.bag.length ? <span><span className="text-quiet">in the bag: </span>{v.bag.map((b) => `${shirtLabel(b.design)} ${b.size ?? ""}${b.n > 1 ? ` ×${b.n}` : ""}`).join(", ")}</span> : null}
                  {v.last?.step ? <span><span className="text-quiet">last: </span>{STEP_WORD[v.last.step]}{v.last.detail ? ` · ${shirtLabel(v.last.detail) || v.last.detail}` : ""}</span> : null}
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="rounded-xl border border-dashed border-line px-4 py-10 text-center text-[13px] text-quiet">nobody on the site right now. this fills in the moment someone opens a page.</p>
      )}
    </>
  );
}
