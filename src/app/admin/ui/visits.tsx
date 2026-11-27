import Link from "next/link";
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
const REACH: [Step, string, string][] = [
  ["bag", "bag", "text-ink/80 ring-line"],
  ["checkout", "checkout", "text-ink/80 ring-line"],
  ["pay", "paying", "text-ink/80 ring-line"],
  ["paid", "paid", "text-ok ring-ok/40"],
];
export function Reached({ steps }: { steps: Step[] }) {
  const got = REACH.filter(([s]) => steps.includes(s));
  if (!got.length) return null;
  return (
    <span className="inline-flex flex-wrap gap-1">
      {got.map(([s, w, c]) => <span key={s} className={`rounded-full px-1.5 py-px text-[10px] ring-1 ${c}`}>{w}</span>)}
    </span>
  );
}

export function Trail({ trail, max = 6 }: { trail: string[]; max?: number }) {
  const t = trail.length > max ? [...trail.slice(0, max - 1), `… ${trail.length - max + 1} more`] : trail;
  return <span className="text-quiet">{t.map((p, i) => <span key={i}>{i ? <span className="px-1 text-line">→</span> : null}<span className={i === t.length - 1 ? "text-ink/80" : ""}>{p.startsWith("…") ? p : pageName(p)}</span></span>)}</span>;
}

export function VisitTable({ visits, empty }: { visits: VisitRow[]; empty?: string }) {
  if (!visits.length) return <p className="py-6 text-[13px] text-quiet">{empty ?? "nobody yet"}</p>;
  return (
    <div className="-mx-4 overflow-x-auto px-4 md:mx-0 md:px-0">
      <table className="w-full min-w-[760px] border-collapse text-left text-[13px]">
        <thead>
          <tr className="border-b border-line text-[11px] uppercase tracking-[0.1em] text-quiet">
            {["when", "who", "from", "pages", "time", "got to", "path"].map((h) => <th key={h} className="whitespace-nowrap py-2 pr-4 font-medium">{h}</th>)}
          </tr>
        </thead>
        <tbody className="[&_td]:py-2.5 [&_td]:pr-4 [&_td]:align-top [&_tr]:border-b [&_tr]:border-line/60">
          {visits.map((v) => (
            <tr key={v.id} className="transition hover:bg-ink/[0.03]">
              <td className="whitespace-nowrap"><Link href={`/admin/visitors/${encodeURIComponent(v.id)}`} className="underline decoration-line underline-offset-4 hover:decoration-ink">{time(v.lastAt)}</Link></td>
              <td className="whitespace-nowrap">
                {v.kind === "bot" ? <span>{v.device}<span className="block text-[11px] text-quiet">{v.reason}</span></span> : <>
                  {where(v)}
                  <span className="block text-[11px] text-quiet">{v.device}{v.person ? <> · <Link href={`/admin/visitors/person/${v.person}`} className="hover:text-ink">{v.nth && v.nth > 1 ? `visit ${v.nth}` : "first visit"}</Link></> : null}</span>
                </>}
              </td>
              <td className="whitespace-nowrap text-quiet">{v.referrer ?? "direct"}</td>
              <td className="tnum">{v.pages}</td>
              <td className="tnum whitespace-nowrap text-quiet">{v.activeMs ? span(v.activeMs) : "–"}</td>
              <td><Reached steps={v.reached} /></td>
              <td className="max-w-[28rem]"><Trail trail={v.trail} /></td>
            </tr>
          ))}
        </tbody>
      </table>
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
