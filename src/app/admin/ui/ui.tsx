import Link from "next/link";
import type { Stage } from "@/lib/shop/orders";

/** The admin's pieces: sahn's paper, ink and blue, plain rules, numbers in even columns. */

export const inr = (n: number | null | undefined, paise = false) =>
  n == null || !Number.isFinite(n) ? "–" : "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: paise ? 2 : 0, maximumFractionDigits: paise ? 2 : 0 });

const IST = "Asia/Kolkata";
export const dt = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit", timeZone: IST }).toLowerCase() : "–";
export const dateOnly = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: IST }).toLowerCase() : "–";
export const ago = (iso?: string | null) => {
  if (!iso) return "–";
  const m = Math.round((Date.now() - Date.parse(iso)) / 60000);
  return m < 1 ? "just now" : m < 60 ? `${m} min ago` : m < 48 * 60 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} days ago`;
};

export function PageHead({ title, sub, children }: { title: string; sub?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b border-line pb-5">
      <div className="min-w-0">
        <h1 className="text-[clamp(28px,3.4vw,44px)] font-extrabold leading-none tracking-[-0.04em]">{title}</h1>
        {sub ? <p className="mt-2 text-[13px] text-quiet">{sub}</p> : null}
      </div>
      {children ? <div className="flex flex-wrap items-center gap-2">{children}</div> : null}
    </div>
  );
}

export function Section({ title, aside, children, className = "" }: { title: string; aside?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={`mb-10 ${className}`}>
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 className="text-[12px] font-semibold uppercase tracking-[0.12em] text-quiet">{title}</h2>
        {aside ? <div className="text-[12px] text-quiet">{aside}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function Stat({ label, value, sub, tone }: { label: string; value: React.ReactNode; sub?: React.ReactNode; tone?: "blue" | "warn" }) {
  return (
    <div className="border-t border-line pt-3">
      <div className="text-[12px] text-quiet">{label}</div>
      <div className={`tnum mt-1 text-[26px] font-bold leading-tight tracking-[-0.02em] ${tone === "blue" ? "text-blue" : tone === "warn" ? "text-[#f0a35b]" : ""}`}>{value}</div>
      {sub ? <div className="tnum mt-0.5 text-[12px] text-quiet">{sub}</div> : null}
    </div>
  );
}

/** a table that scrolls sideways on a phone instead of squashing */
export function Table({ head, children, empty }: { head: React.ReactNode[]; children: React.ReactNode; empty?: string }) {
  const none = Array.isArray(children) && children.length === 0;
  return (
    <div className="-mx-4 overflow-x-auto px-4 md:mx-0 md:px-0">
      <table className="w-full min-w-[640px] border-collapse text-left text-[13px]">
        <thead>
          <tr className="border-b border-line text-[11px] uppercase tracking-[0.1em] text-quiet">
            {head.map((h, i) => (
              <th key={i} className="whitespace-nowrap py-2 pr-4 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="[&_td]:py-2.5 [&_td]:pr-4 [&_td]:align-top [&_tr]:border-b [&_tr]:border-line/60">{children}</tbody>
      </table>
      {none ? <p className="py-6 text-[13px] text-quiet">{empty ?? "nothing yet"}</p> : null}
    </div>
  );
}

export function KV({ items }: { items: [string, React.ReactNode][] }) {
  return (
    <dl className="grid grid-cols-[minmax(7rem,auto)_1fr] gap-x-6 gap-y-1.5 text-[13px]">
      {items.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-quiet">{k}</dt>
          <dd className="min-w-0 break-words">{v ?? "–"}</dd>
        </div>
      ))}
    </dl>
  );
}

const STAGE: Record<Stage, [string, string]> = {
  paying: ["not paid", "text-quiet ring-line"],
  paid: ["paid · in the hour", "text-ink ring-ink/40"],
  printing: ["printing", "text-blue ring-blue/60"],
  shipped: ["shipped", "text-blue ring-blue/60"],
  out: ["out for delivery", "text-blue ring-blue/60"],
  delivered: ["delivered", "text-[#8fd19e] ring-[#8fd19e]/50"],
  attention: ["needs a look", "text-[#f0a35b] ring-[#f0a35b]/60"],
  cancelled: ["cancelled", "text-quiet ring-line line-through"],
};
export function StageBadge({ stage }: { stage: Stage }) {
  const [word, cls] = STAGE[stage] ?? [stage, "text-quiet ring-line"];
  return <span className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] ring-1 ${cls}`}>{word}</span>;
}
export const STAGE_ADMIN = Object.fromEntries(Object.entries(STAGE).map(([k, v]) => [k, v[0]])) as Record<Stage, string>;

export function Pill({ children, tone }: { children: React.ReactNode; tone?: "warn" | "ok" | "blue" }) {
  const c = tone === "warn" ? "text-[#f0a35b] ring-[#f0a35b]/60" : tone === "ok" ? "text-[#8fd19e] ring-[#8fd19e]/50" : tone === "blue" ? "text-blue ring-blue/60" : "text-quiet ring-line";
  return <span className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] ring-1 ${c}`}>{children}</span>;
}

export function A({ href, children, className = "" }: { href: string; children: React.ReactNode; className?: string }) {
  return (
    <Link href={href} className={`underline decoration-line underline-offset-4 transition hover:decoration-ink ${className}`}>
      {children}
    </Link>
  );
}

/** an honest blank: what isn't there yet and why, never a made-up number */
export function Missing({ children }: { children: React.ReactNode }) {
  return <p className="border border-dashed border-line px-4 py-3 text-[13px] text-quiet">{children}</p>;
}
