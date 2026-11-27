import Link from "next/link";
import { Icon, type IconName } from "./icons";
import { DESIGNS, type Design } from "@/content/tee";
import { STEP_WORD, span, type EventRow, type Step, type VisitRow } from "@/lib/visits/shared";

/** The visitor log's pieces, for the server pages and the live page alike (no hooks here). */

export const shirtLabel = (d: string | null | undefined) => {
  const x = d ? DESIGNS[d as Design] : null;
  return x ? `${x.no} ${x.name}${x.city ? ` ${x.city}` : ""}` : (d ?? "");
};

/** a path as a person reads it: "home", "crowd", "checkout" */
export function pageName(p: string | null | undefined) {
  if (!p) return "–";
  if (p === "/") return "home";
  const shirt = Object.values(DESIGNS).find((x) => p.endsWith(`/${x.slug}`));
  if (shirt) return `${shirt.no} ${shirt.name}${shirt.city ? ` ${shirt.city}` : ""}`;
  return p.replace(/^\//, "").replace(/\//g, " / ");
}

const regions = typeof Intl !== "undefined" && "DisplayNames" in Intl ? new Intl.DisplayNames(["en"], { type: "region" }) : null;
const country = (cc: string | null) => {
  if (!cc || !/^[A-Z]{2}$/.test(cc)) return null;
  try {
    return (regions?.of(cc) ?? cc).toLowerCase();
  } catch {
    return cc;
  }
};
/** "pune, india", or the country alone, or "somewhere" */
export const where = (v: Pick<VisitRow, "city" | "country">) => [v.city?.toLowerCase(), country(v.country)].filter(Boolean).join(", ") || "somewhere";

/** how far a visit got, as small marks */
const REACH: [Step, string][] = [["bag", "bag"], ["checkout", "checkout"], ["pay", "paying"], ["paid", "paid"]];
export function Reached({ steps }: { steps: Step[] }) {
  const got = REACH.filter(([s]) => steps.includes(s));
  if (!got.length) return null;
  return (
    <span className="inline-flex flex-wrap gap-1">
      {got.map(([s, w]) => <span key={s} className="inline-flex items-center gap-1 rounded-[6px] bg-s2 px-2 py-0.5 text-[12px] text-ink/80">{s === "paid" ? <span className="h-1.5 w-1.5 rounded-full bg-ok" /> : null}{w}</span>)}
    </span>
  );
}

export function Trail({ trail, max = 6 }: { trail: string[]; max?: number }) {
  const t = trail.length > max ? [...trail.slice(0, max - 1), `… ${trail.length - max + 1} more`] : trail;
  return <span className="text-quiet">{t.map((p, i) => <span key={i}>{i ? <span className="px-1 text-quiet/50">→</span> : null}<span className={i === t.length - 1 ? "text-ink/80" : ""}>{p.startsWith("…") ? p : pageName(p)}</span></span>)}</span>;
}

/** a device's mark: a phone, a computer or a program */
export const deviceIcon = (v: Pick<VisitRow, "kind" | "device">): IconName =>
  v.kind === "bot" ? "bot" : /iphone|android|phone|mobile|ipad|tablet/i.test(v.device ?? "") ? "phone" : "desktop";

/** visits as rows on one card: where and on what, the pages they went through, when, and how far they got */
export function VisitTable({ visits, empty }: { visits: VisitRow[]; empty?: string }) {
  if (!visits.length) return <p className="rounded-[14px] bg-s1 px-5 py-10 text-center text-[15px] text-quiet">{empty ?? "nobody yet"}</p>;
  return (
    <div className="divide-y divide-line/50 overflow-hidden rounded-[14px] bg-s1">
      {visits.map((v) => (
        <Link key={v.id} href={`/admin/visitors/${encodeURIComponent(v.id)}`} className="group flex items-center gap-4 px-5 py-3.5 transition hover:bg-s2">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-s2 text-ink/75"><Icon name={deviceIcon(v)} className="h-[19px] w-[19px]" /></span>
          <span className="min-w-0 flex-1">
            <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[15px] leading-snug">
              {v.kind === "bot" ? <span>{v.device}<span className="text-quiet"> · {v.reason}</span></span> : <span>{where(v)}<span className="text-quiet"> · {v.nth && v.nth > 1 ? `visit ${v.nth}` : "first visit"}{v.referrer ? ` · from ${v.referrer}` : ""}</span></span>}
              <Reached steps={v.reached} />
            </span>
            <span className="mt-0.5 block truncate text-[13px]"><Trail trail={v.trail} /></span>
          </span>
          <span className="shrink-0 text-right text-[13px] text-quiet">
            <span className="block">{time(v.lastAt)}</span>
            <span className="tnum block">{v.pages} page{v.pages === 1 ? "" : "s"}{v.activeMs ? ` · ${span(v.activeMs)}` : ""}</span>
          </span>
          <Icon name="chevron" className="hidden h-[18px] w-[18px] text-quiet transition group-hover:translate-x-0.5 group-hover:text-ink sm:block" />
        </Link>
      ))}
    </div>
  );
}

export const time = (iso: string) => new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" }).toLowerCase();
const clock = (iso: string) => new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", second: "2-digit", timeZone: "Asia/Kolkata" }).toLowerCase();

/** one visit, step by step */
export function Timeline({ events }: { events: EventRow[] }) {
  return (
    <ol className="relative grid gap-0 border-l border-line pl-5">
      {events.map((e) => {
        const step = e.step as Step | null;
        const money = step === "paid" ? "bg-ok" : step === "payfail" ? "bg-bad" : e.type === "page" ? "bg-ink" : "bg-quiet";
        return (
          <li key={e.seq} className="relative py-2">
            <span className={`absolute -left-[25px] top-[13px] h-2 w-2 rounded-full ${money}`} />
            <div className="flex flex-wrap items-baseline gap-x-3 text-[13px]">
              <span className="tnum w-24 shrink-0 text-[12px] text-quiet">{clock(e.at)}</span>
              {e.type === "page" ? (
                <span><span className="text-quiet">opened </span><span className="font-medium">{pageName(e.path)}</span>
                  <span className="text-[12px] text-quiet">{e.ms ? ` · ${span(e.ms)} on screen` : ""}{e.scroll != null ? ` · ${e.scroll}% down` : ""}</span></span>
              ) : e.type === "click" ? (
                <span><span className="text-quiet">went out to </span><span className="font-medium">{e.detail}</span></span>
              ) : (
                <span><span className="text-quiet">{step ? STEP_WORD[step] : "did"} </span>
                  <span className="font-medium">{[e.design ? shirtLabel(e.design) : null, e.size, step === "look" ? e.detail : null].filter(Boolean).join(" · ")}</span></span>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
