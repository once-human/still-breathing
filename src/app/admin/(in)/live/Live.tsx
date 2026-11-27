"use client";

import Link from "next/link";
import { STEP_WORD, span } from "@/lib/visits/shared";
import type { LiveVisit } from "@/lib/visits/server";
import { usePoll } from "../../ui/client";
import { Icon } from "../../ui/icons";
import { Reached, Trail, deviceIcon, pageName, shirtLabel, where } from "../../ui/visits";

type Data = { people: LiveVisit[]; count: { now: number; hour: number; today: number } };

/** who is on the site now, every 5 seconds */
export function Live({ initial }: { initial: Data }) {
  const { data, at } = usePoll<Data>("/api/admin/live", 5000, initial);
  const c = data.count;
  return (
    <>
      <div className="mb-10 grid grid-cols-3 gap-3 md:mb-12">
        {([["on the site now", c.now, true], ["in the last hour", c.hour, false], ["today", c.today, false]] as const).map(([l, n, live]) => (
          <div key={l} className="rounded-[22px] bg-s1 p-5 md:p-6">
            <div className="flex items-center gap-2 text-[14px] text-quiet">{live && n ? <span className="h-2 w-2 rounded-full bg-ok" /> : null}{l}</div>
            <div className="tnum mt-6 text-[clamp(34px,4.2vw,52px)] font-extrabold leading-none tracking-[-0.045em]">{n}</div>
          </div>
        ))}
      </div>
      <div className="mb-3 flex items-baseline justify-between gap-4 px-1">
        <h2 className="text-[17px] font-semibold tracking-[-0.01em]">here now</h2>
        <span className="text-right text-[13px] text-quiet">every 5 seconds{at ? `, last ${new Date(at).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", second: "2-digit", timeZone: "Asia/Kolkata" }).toLowerCase()}` : ""}</span>
      </div>
      {data.people.length ? (
        <div className="divide-y divide-line/50 overflow-hidden rounded-[22px] bg-s1">
          {data.people.map((v) => (
            <Link key={v.id} href={`/admin/visitors/${v.id}`} className="a-fade group flex gap-4 px-5 py-4 transition hover:bg-s2">
              <span className="relative grid h-10 w-10 shrink-0 place-items-center rounded-full bg-s2 text-ink/75">
                <Icon name={deviceIcon(v)} className="h-[19px] w-[19px]" />
                <span className="absolute right-0 top-0 h-2.5 w-2.5 rounded-full bg-ok ring-2 ring-s1" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[15px] leading-snug">
                  <span>on <span className="font-semibold">{pageName(v.now)}</span></span><Reached steps={v.reached} />
                </span>
                <span className="mt-0.5 block text-[13px] text-quiet">
                  {where(v)} · {v.device} · {v.referrer ? `from ${v.referrer}` : "came direct"} · {v.nth && v.nth > 1 ? `visit ${v.nth}` : "first visit"} · here {span(Date.now() - Date.parse(v.startedAt))}
                </span>
                <span className="mt-2 block text-[13px]"><Trail trail={v.trail} max={8} /></span>
                {v.bag.length || v.last?.step ? (
                  <span className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-[13px]">
                    {v.bag.length ? <span><span className="text-quiet">in the bag </span>{v.bag.map((b) => `${shirtLabel(b.design)} ${b.size ?? ""}${b.n > 1 ? ` ×${b.n}` : ""}`).join(", ")}</span> : null}
                    {v.last?.step ? <span><span className="text-quiet">last </span>{STEP_WORD[v.last.step]}{v.last.detail ? ` ${shirtLabel(v.last.detail) || v.last.detail}` : ""}</span> : null}
                  </span>
                ) : null}
              </span>
              <Icon name="chevron" className="mt-2.5 h-[18px] w-[18px] shrink-0 text-quiet transition group-hover:translate-x-0.5 group-hover:text-ink" />
            </Link>
          ))}
        </div>
      ) : (
        <div className="grid place-items-center rounded-[22px] bg-s1 px-6 py-12 text-center">
          <span className="grid h-10 w-10 place-items-center rounded-full bg-s2 text-ink/75"><Icon name="live" className="h-[19px] w-[19px]" /></span>
          <p className="mt-4 text-[15px]">nobody on the site right now</p>
          <p className="mt-1 text-[13px] text-quiet">someone shows here the moment they open a page, and for a minute after their last move</p>
        </div>
      )}
    </>
  );
}
