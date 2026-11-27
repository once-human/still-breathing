import Link from "next/link";
import type { Stage } from "@/lib/shop/orders";
import { Icon, type IconName } from "./icons";

/**
 * The admin's look: the shop's font, colours and lowercase, at its own calmer scale. One loud thing a screen (its
 * name, its number) in extrabold; a plain heading over each part; 15 px to read, 13 px at the smallest; blue the only
 * colour that isn't a signal. Under each heading the rows sit together on one solid card: an icon, what it is, a
 * quiet line, and its control on the right. Green, amber and red only ever mean live, needs you, broken. Things
 * move with a little spring (globals.css, the a-* classes).
 */

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

/* ---------- a page ---------- */

/** a page's name, big and lowercase as on the site, with a line under it and its own buttons on the right */
export function Page({ title, sub, back, actions }: { title: string; sub?: React.ReactNode; back?: [string, string]; actions?: React.ReactNode }) {
  return (
    <header className="mb-9 md:mb-12">
      {back ? (
        <Link href={back[0]} className="a-press mb-4 inline-flex items-center gap-1 text-[14px] text-quiet transition hover:text-ink">
          <Icon name="back" className="h-4 w-4" />{back[1]}
        </Link>
      ) : null}
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
        <h1 className="min-w-0 break-words text-[clamp(34px,4.4vw,54px)] font-extrabold leading-[0.95] tracking-[-0.045em]">{title}</h1>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
      {sub ? <p className="mt-3 text-[15px] text-quiet">{sub}</p> : null}
    </header>
  );
}
/** the old name: a page head */
export const PageHead = ({ title, sub, children }: { title: string; sub?: React.ReactNode; children?: React.ReactNode }) => <Page title={title} sub={sub} actions={children} />;

/** a part's heading: its name, and a quiet note or a link on the right */
export function Rule({ children, note, id }: { children: React.ReactNode; note?: React.ReactNode; id?: string }) {
  return (
    <div id={id} className="mb-3 flex scroll-mt-24 items-baseline justify-between gap-4 px-1">
      <h2 className="text-[17px] font-semibold tracking-[-0.01em]">{children}</h2>
      {note ? <div className="min-w-0 text-right text-[13px] text-quiet">{note}</div> : null}
    </div>
  );
}

/** a part of a page: its rule, then what's in it */
export function Section({ title, aside, children, className = "", id }: { title: string; aside?: React.ReactNode; children: React.ReactNode; className?: string; id?: string }) {
  return (
    <section className={`mb-10 md:mb-12 ${className}`}>
      <Rule note={aside} id={id}>{title}</Rule>
      {children}
    </section>
  );
}

/** one solid surface */
export function Card({ children, className = "", pad = true }: { children: React.ReactNode; className?: string; pad?: boolean }) {
  return <div className={`rounded-[14px] bg-s1 ${pad ? "p-5 md:p-6" : ""} ${className}`}>{children}</div>;
}

/** rows that belong together, on one card, a hairline between each */
export function Group({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`divide-y divide-line/50 overflow-hidden rounded-[14px] bg-s1 ${className}`}>{children}</div>;
}

export type Tone = "ok" | "warn" | "bad" | "blue" | "quiet";
/** icons and badges stay grey; a signal shows only as its colour on the icon or the dot */
const TINT: Record<Tone, string> = { ok: "bg-s2 text-ok", warn: "bg-s2 text-warn", bad: "bg-s2 text-bad", blue: "bg-s2 text-ink/80", quiet: "bg-s2 text-ink/75" };
const DOT: Record<Tone, string> = { ok: "bg-ok", warn: "bg-warn", bad: "bg-bad", blue: "bg-ink/60", quiet: "bg-quiet/60" };

/** a round tinted mark for a row */
export function Mark({ icon, tone = "quiet" }: { icon: IconName; tone?: Tone }) {
  return <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${TINT[tone]}`}><Icon name={icon} className="h-[19px] w-[19px]" /></span>;
}

/**
 * One row: icon, title, a quiet line, and on the right a value or a control. With `href` the whole row is the link
 * and ends in a chevron; `muted` greys it out for a value that's fixed elsewhere.
 */
export function Row({ icon, tone, title, sub, right, href, external, muted }: {
  icon?: IconName; tone?: Tone; title: React.ReactNode; sub?: React.ReactNode; right?: React.ReactNode; href?: string; external?: boolean; muted?: boolean;
}) {
  const body = (
    <>
      {icon ? <Mark icon={icon} tone={tone} /> : null}
      <div className="min-w-0 flex-1">
        <div className={`text-[15px] leading-snug ${muted ? "text-quiet" : ""}`}>{title}</div>
        {sub ? <div className="mt-0.5 text-[13px] leading-snug text-quiet">{sub}</div> : null}
      </div>
      {right != null ? <div className={`shrink-0 text-right text-[15px] ${muted ? "text-quiet" : ""}`}>{right}</div> : null}
      {href ? <Icon name={external ? "out" : "chevron"} className="h-[18px] w-[18px] text-quiet transition group-hover:translate-x-0.5 group-hover:text-ink" /> : null}
    </>
  );
  const cls = "flex min-h-[68px] items-center gap-4 px-5 py-3.5";
  if (!href) return <div className={cls}>{body}</div>;
  return external
    ? <a href={href} target="_blank" rel="noreferrer" className={`group ${cls} transition hover:bg-s2`}>{body}</a>
    : <Link href={href} className={`group ${cls} transition hover:bg-s2`}>{body}</Link>;
}

/** a big number with what it is and how it compares */
export function Tile({ label, value, sub, delta, href, tone, icon }: {
  label: string; value: React.ReactNode; sub?: React.ReactNode; delta?: { now: number; was: number; word?: string; money?: boolean }; href?: string; tone?: "blue" | "ok" | "warn"; icon?: IconName;
}) {
  const color = tone === "warn" ? "text-warn" : "";
  const inner = (
    <>
      <div className="flex items-center justify-between gap-2 text-[14px] text-quiet">
        <span>{label}</span>{icon ? <Icon name={icon} className="h-[18px] w-[18px]" /> : null}
      </div>
      <div className={`tnum mt-6 text-[clamp(34px,4.2vw,52px)] font-extrabold leading-none tracking-[-0.045em] ${color}`}>{value}</div>
      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-quiet">
        {delta ? <Delta {...delta} /> : null}{sub ? <span>{sub}</span> : null}
      </div>
    </>
  );
  const cls = "block rounded-[14px] bg-s1 p-5 md:p-6";
  return href ? <Link href={href} className={`${cls} transition hover:bg-s2`}>{inner}</Link> : <div className={cls}>{inner}</div>;
}

/** up or down on before, in words: "up 3 on yesterday" */
export function Delta({ now, was, word = "yesterday", money }: { now: number; was: number; word?: string; money?: boolean }) {
  const d = Math.round((now - was) * 100) / 100;
  const f = (n: number) => (money ? inr(Math.abs(n)) : String(Math.abs(n)));
  if (!d) return <span>same as {word}</span>;
  return (
    <span className="inline-flex items-center gap-1 text-ink/75">
      <Icon name={d > 0 ? "up" : "fall"} className="h-4 w-4" />{f(d)} {d > 0 ? "more" : "less"} than {word}
    </span>
  );
}

/** a small word in a tinted pill */
export function Badge({ children, tone = "quiet", dot }: { children: React.ReactNode; tone?: Tone; dot?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-[6px] bg-s2 px-2.5 py-1 text-[12.5px] font-medium leading-none text-ink/80">
      {dot ? <span className={`h-1.5 w-1.5 rounded-full ${DOT[tone]}`} /> : null}{children}
    </span>
  );
}
/** the old name */
export function Pill({ children, tone }: { children: React.ReactNode; tone?: "warn" | "ok" | "blue" }) {
  return <Badge tone={tone ?? "quiet"}>{children}</Badge>;
}

/** a status light: a dot and a word */
export function Light({ tone, children }: { tone: "ok" | "warn" | "bad" | "quiet"; children: React.ReactNode }) {
  const c = { ok: "bg-ok", warn: "bg-warn", bad: "bg-bad", quiet: "bg-quiet/50" }[tone];
  return <span className="inline-flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${c}`} />{children}</span>;
}

/** pick one of a few views, as links (search params) */
export function Tabs({ items, active }: { items: { href: string; label: string; count?: number; key: string }[]; active: string }) {
  return (
    <nav className="-mx-4 mb-8 overflow-x-auto px-4 [scrollbar-width:none] md:mx-0 md:px-0">
      <div className="inline-flex gap-1 rounded-[12px] bg-s1 p-1">
        {items.map((t) => (
          <Link key={t.key} href={t.href} aria-current={t.key === active ? "page" : undefined}
            className={`a-press whitespace-nowrap rounded-[9px] px-4 py-2 text-[14px] transition ${t.key === active ? "bg-ink font-semibold text-paper" : "text-quiet hover:text-ink"}`}>
            {t.label}{t.count != null ? <span className={`tnum ml-1.5 ${t.key === active ? "text-paper/60" : "text-quiet/70"}`}>{t.count}</span> : null}
          </Link>
        ))}
      </div>
    </nav>
  );
}

/** nothing to show, said kindly */
export function Empty({ icon = "check", title, sub }: { icon?: IconName; title: string; sub?: React.ReactNode }) {
  return (
    <div className="grid place-items-center rounded-[14px] bg-s1 px-6 py-12 text-center">
      <Mark icon={icon} />
      <p className="mt-4 text-[15px]">{title}</p>
      {sub ? <p className="mt-1 max-w-sm text-[13px] text-quiet">{sub}</p> : null}
    </div>
  );
}
/** the old name: an honest blank */
export function Missing({ children }: { children: React.ReactNode }) {
  return <p className="rounded-[14px] bg-s1 px-5 py-4 text-[14px] text-quiet">{children}</p>;
}

/** label and value lines on a card */
export function KV({ items }: { items: [string, React.ReactNode][] }) {
  return (
    <dl className="divide-y divide-line/50 overflow-hidden rounded-[14px] bg-s1">
      {items.map(([k, v]) => (
        <div key={k} className="flex min-h-[52px] flex-wrap items-baseline justify-between gap-x-6 gap-y-1 px-5 py-3.5 text-[15px]">
          <dt className="text-quiet">{k}</dt>
          <dd className="min-w-0 break-words text-right">{v ?? "–"}</dd>
        </div>
      ))}
    </dl>
  );
}

/** a big number, plainly: what it is above, a quiet line below */
export function Stat({ label, value, sub, tone }: { label: string; value: React.ReactNode; sub?: React.ReactNode; tone?: "blue" | "warn" }) {
  return (
    <div className="rounded-[14px] bg-s1 p-5">
      <div className="text-[14px] text-quiet">{label}</div>
      <div className={`tnum mt-3 text-[34px] font-extrabold leading-none tracking-[-0.04em] ${tone === "warn" ? "text-warn" : ""}`}>{value}</div>
      {sub ? <div className="tnum mt-2 text-[13px] text-quiet">{sub}</div> : null}
    </div>
  );
}

/** ranked bars: what, a bar for how many, the number */
export function Bars({ rows, empty = "nothing yet" }: { rows: { key: string; label: React.ReactNode; n: number; sub?: React.ReactNode }[]; empty?: string }) {
  const max = Math.max(1, ...rows.map((r) => r.n));
  if (!rows.length) return <p className="rounded-[14px] bg-s1 px-5 py-6 text-[14px] text-quiet">{empty}</p>;
  return (
    <ul className="grid gap-3 rounded-[14px] bg-s1 p-5">
      {rows.map((r) => (
        <li key={r.key}>
          <div className="flex items-baseline justify-between gap-4 text-[15px]"><span className="min-w-0 truncate">{r.label}</span><span className="tnum shrink-0 text-quiet">{r.n}{r.sub ? <span className="ml-1.5 text-[13px]">{r.sub}</span> : null}</span></div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-s3"><div className="h-full rounded-full bg-ink/55" style={{ width: `${Math.max(2, (r.n / max) * 100)}%` }} /></div>
        </li>
      ))}
    </ul>
  );
}

/** a table for the few places a grid is the clearest (it scrolls sideways on a phone) */
export function Table({ head, children, empty }: { head: React.ReactNode[]; children: React.ReactNode; empty?: string }) {
  const none = Array.isArray(children) && children.length === 0;
  return (
    <div className="overflow-hidden rounded-[14px] bg-s1">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-left text-[14px]">
          <thead>
            <tr className="border-b border-line/60 text-[13px] text-quiet">
              {head.map((h, i) => <th key={i} className="whitespace-nowrap px-5 py-3 font-medium">{h}</th>)}
            </tr>
          </thead>
          <tbody className="[&_td]:px-5 [&_td]:py-3.5 [&_td]:align-middle [&_tr+tr]:border-t [&_tr+tr]:border-line/40 [&_tr]:transition [&_tr:hover]:bg-s2/60">{children}</tbody>
        </table>
      </div>
      {none ? <p className="px-5 py-8 text-[14px] text-quiet">{empty ?? "nothing yet"}</p> : null}
    </div>
  );
}

/* ---------- orders ---------- */

const STAGE: Record<Stage, [string, Tone]> = {
  paying: ["not paid", "quiet"],
  paid: ["paid", "blue"],
  printing: ["being made", "blue"],
  shipped: ["on its way", "blue"],
  out: ["out for delivery", "blue"],
  delivered: ["delivered", "ok"],
  attention: ["needs you", "warn"],
  cancelled: ["cancelled", "quiet"],
};
export function StageBadge({ stage }: { stage: Stage }) {
  const [word, tone] = STAGE[stage] ?? [stage, "quiet" as Tone];
  return <Badge tone={tone} dot>{word}</Badge>;
}
export const STAGE_ADMIN = Object.fromEntries(Object.entries(STAGE).map(([k, v]) => [k, v[0]])) as Record<Stage, string>;

/** a link: the text's own colour, a faint underline that firms up on hover */
export function A({ href, children, className = "" }: { href: string; children: React.ReactNode; className?: string }) {
  return <Link href={href} className={`text-ink/85 underline decoration-ink/25 underline-offset-4 transition hover:text-ink hover:decoration-ink ${className}`}>{children}</Link>;
}

/** the first letter of a name, in a circle */
export function Avatar({ name, tone = "quiet" }: { name: string; tone?: Tone }) {
  return <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full text-[15px] font-semibold uppercase ${TINT[tone]}`}>{(name.trim()[0] ?? "?").toUpperCase()}</span>;
}

/* ---------- forms ---------- */

/**
 * One setting in a group: what it is and a quiet line on the left, its control on the right; `stack` puts the
 * control under the words (a long text), and `count` shows how much of the limit is used.
 */
export function Field({ label, hint, children, stack, count }: { label: React.ReactNode; hint?: React.ReactNode; children: React.ReactNode; stack?: boolean; count?: [number, number] }) {
  const words = (
    <span className="min-w-0 flex-1">
      <span className="flex items-baseline justify-between gap-4 text-[15px] leading-snug">{label}{count ? <span className={`tnum text-[13px] ${count[0] > count[1] ? "text-bad" : "text-quiet"}`}>{count[0]}/{count[1]}</span> : null}</span>
      {hint ? <span className="mt-0.5 block text-[13px] leading-snug text-quiet">{hint}</span> : null}
    </span>
  );
  return stack
    ? <label className="grid gap-3 px-5 py-4">{words}{children}</label>
    : <label className="flex min-h-[68px] flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3.5">{words}<span className="shrink-0">{children}</span></label>;
}

/** a value that's set somewhere else (a partner's rate, the code): plain grey, nothing to press */
export function Fixed({ children }: { children: React.ReactNode }) {
  return <span className="tnum text-[15px] text-quiet">{children}</span>;
}
