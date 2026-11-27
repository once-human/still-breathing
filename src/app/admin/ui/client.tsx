"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { Icon, type IconName } from "./icons";

/**
 * The admin's moving parts. Every change is saved in place (no page reloads): switches and pickers save the moment
 * they change and say so in a toast; forms show a "save changes" bar once something is changed; anything that can't
 * be undone, or moves money, asks first in a pop-up (and the worst ones want a word typed). Every write sends the
 * session's CSRF token.
 */
const Csrf = createContext("");
type Toast = { id: number; ok: boolean; text: string };
const Toasts = createContext<(ok: boolean, text: string) => void>(() => {});

export function CsrfProvider({ token, children }: { token: string; children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const say = useCallback((ok: boolean, text: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t.slice(-3), { id, ok, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), ok ? 3500 : 7000);
  }, []);
  return (
    <Csrf.Provider value={token}>
      <Toasts.Provider value={say}>
        {children}
        <div className="pointer-events-none fixed inset-x-4 bottom-24 z-[60] mx-auto grid w-auto max-w-[400px] gap-2 md:inset-x-auto md:bottom-6 md:right-6" role="status" aria-live="polite">
          {toasts.map((t) => (
            <div key={t.id} className="a-pop pointer-events-auto flex items-start gap-3 rounded-2xl bg-s3 px-4 py-3.5 text-[14px] shadow-[0_12px_40px_rgba(0,0,0,0.5)]">
              <span className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full ${t.ok ? "bg-ok/20 text-ok" : "bg-bad/20 text-bad"}`}><Icon name={t.ok ? "check" : "x"} className="h-3.5 w-3.5" /></span>
              <span className="min-w-0">{t.text}</span>
            </div>
          ))}
        </div>
      </Toasts.Provider>
    </Csrf.Provider>
  );
}
export const useToast = () => useContext(Toasts);

export function useAdminPost() {
  const csrf = useContext(Csrf);
  return async (url: string, body: unknown): Promise<{ ok: true; data: Record<string, unknown> } | { ok: false; error: string }> => {
    const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "x-csrf": csrf }, body: JSON.stringify(body), credentials: "same-origin" }).catch(() => null);
    if (!res) return { ok: false, error: "no answer: check the connection" };
    const j = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    if (res.status === 401) window.location.href = "/admin/login";
    return res.ok ? { ok: true, data: j } : { ok: false, error: String(j.error ?? `failed (${res.status})`) };
  };
}

/** a JSON read from an admin route, at once and again every `ms` while the tab is in front */
export function usePoll<T>(url: string, ms: number, initial: T) {
  const [data, setData] = useState<T>(initial);
  const [at, setAt] = useState<number>(0);
  useEffect(() => {
    let stop = false;
    const go = async () => {
      if (document.visibilityState !== "visible") return;
      const r = await fetch(url, { cache: "no-store", credentials: "same-origin" }).catch(() => null);
      if (r?.status === 401) window.location.href = "/admin/login";
      if (!r?.ok || stop) return;
      setData((await r.json()) as T);
      setAt(Date.now());
    };
    void go();
    const id = window.setInterval(go, ms);
    document.addEventListener("visibilitychange", go);
    return () => {
      stop = true;
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", go);
    };
  }, [url, ms]);
  return { data, at };
}

/* ---------- navigation ---------- */

const NAV: { group: string; items: [string, string][] }[] = [
  { group: "shop", items: [["/admin", "home"], ["/admin/orders", "orders"], ["/admin/customers", "customers"], ["/admin/products", "products"]] },
  { group: "people", items: [["/admin/live", "live now"], ["/admin/visitors", "visitors"], ["/admin/activity", "activity"]] },
  { group: "setup", items: [["/admin/status", "what's live"], ["/admin/settings", "settings"], ["/admin/audit", "audit log"]] },
];

function LiveDot() {
  const { data } = usePoll<{ now: number }>("/api/admin/live?count=1", 15_000, { now: -1 });
  if (data.now < 0) return null;
  return (
    <span className={`ml-auto inline-flex items-center gap-1.5 text-[11px] tnum ${data.now ? "text-[#8fd19e]" : "text-quiet"}`}>
      {data.now ? <span className="relative flex h-1.5 w-1.5"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#8fd19e] opacity-60" /><span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#8fd19e]" /></span> : null}
      {data.now}
    </span>
  );
}

export function Nav({ email }: { email: string }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const on = (href: string) => (href === "/admin" ? path === "/admin" : path === href || path.startsWith(href + "/"));
  const links = NAV.map((g) => (
    <div key={g.group} className="mb-5">
      <div className="mb-1.5 pl-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-quiet/70">{g.group}</div>
      {g.items.map(([href, label]) => (
        <Link key={href} href={href} onClick={() => setOpen(false)}
          className={`flex items-center rounded-md px-3 py-1.5 text-[14px] transition ${on(href) ? "bg-ink/[0.08] text-ink" : "text-quiet hover:bg-ink/[0.04] hover:text-ink"}`}>
          {label}{href === "/admin/live" ? <LiveDot /> : null}
        </Link>
      ))}
    </div>
  ));
  return (
    <>
      <div className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-paper/95 px-4 py-3 backdrop-blur md:hidden">
        <Link href="/admin" className="text-[18px] font-extrabold tracking-[-0.04em]">sahn <span className="font-normal text-quiet">admin</span></Link>
        <button type="button" onClick={() => setOpen((v) => !v)} className="hit text-[14px]" aria-expanded={open}>{open ? "close" : "menu"}</button>
      </div>
      {open ? <nav className="border-b border-line px-2 py-3 md:hidden">{links}<div className="mt-1 px-3"><SignOut /></div></nav> : null}
      <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col border-r border-line px-3 py-6 md:flex">
        <Link href="/admin" className="px-3 text-[22px] font-extrabold tracking-[-0.04em]">sahn <span className="font-normal text-quiet">admin</span></Link>
        <nav className="mt-8 overflow-y-auto">{links}</nav>
        <div className="mt-auto grid gap-2 px-3 text-[12px] text-quiet">
          <span className="truncate" title={email}>{email}</span>
          <Link href="/" target="_blank" className="hover:text-ink">open the site</Link>
          <SignOut />
        </div>
      </aside>
    </>
  );
}

function SignOut() {
  const post = useAdminPost();
  return (
    <button type="button" className="text-left text-[12px] text-quiet hover:text-ink" onClick={async () => {
      await post("/api/admin/session", { signOut: true });
      window.location.href = "/admin/login";
    }}>sign out</button>
  );
}

export function SignOutAll() {
  return <Act label="sign out everywhere" confirm="every admin session, on every device, ends now (this one too)." url="/api/admin/session" body={{ signOut: true, all: true }} goTo="/admin/login" />;
}

/* ---------- buttons, pop-ups ---------- */

const btn = "a-press inline-flex h-11 items-center justify-center gap-2 rounded-full px-5 text-[15px] font-medium disabled:cursor-not-allowed disabled:opacity-40";
export const BTN = {
  plain: `${btn} bg-s2 text-ink hover:bg-s3`,
  main: `${btn} bg-ink font-semibold text-paper hover:bg-ink/90`,
  danger: `${btn} bg-bad/12 text-bad hover:bg-bad/20`,
  dangerMain: `${btn} bg-bad font-semibold text-black hover:bg-bad/90`,
};
export const FIELD = "h-12 w-full rounded-2xl bg-s2 px-4 text-[15px] text-ink ring-1 ring-transparent transition placeholder:text-quiet/70 focus:bg-s3 focus:ring-ink/30 focus:outline-none disabled:opacity-60";

/** a pop-up: a sheet from the bottom on a phone, a card in the middle on a computer; Escape or outside closes it */
export function Modal({ title, children, onClose, danger }: { title: string; children: React.ReactNode; onClose: () => void; danger?: boolean }) {
  const box = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && close.current();
    window.addEventListener("keydown", k);
    box.current?.querySelector<HTMLElement>("input,select,textarea")?.focus();
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", k);
      document.body.style.overflow = prev;
    };
  }, []);
  return (
    <div className="a-fade fixed inset-0 z-[70] flex items-end justify-center bg-black/70 md:items-center md:p-6" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={box} role="dialog" aria-modal="true" aria-label={title}
        className="a-sheet max-h-[92dvh] w-full overflow-y-auto rounded-t-[28px] bg-s1 px-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-3 shadow-[0_-20px_60px_rgba(0,0,0,0.5)] md:max-w-[460px] md:rounded-[28px] md:pb-6 md:pt-6">
        <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-s3 md:hidden" />
        <h3 className={`text-[22px] font-bold leading-tight tracking-[-0.02em] ${danger ? "text-bad" : ""}`}>{title}</h3>
        <div className="mt-3">{children}</div>
      </div>
    </div>
  );
}

/**
 * One admin action: the button (or a whole row, with `row`), then a pop-up saying what will happen (with fields if
 * it needs any, and for the ones that can't be undone, a word to type), then a toast with the answer. Nothing
 * happens on the first press.
 */
type Field = { name: string; label: string; type?: "text" | "number"; placeholder?: string; initial?: string; optional?: boolean; options?: string[] };

export function Act({ label, confirm, url, body, danger, typeToConfirm, done, goTo, fields = [], small, row }: {
  label: string; confirm: string; url: string; body: Record<string, unknown>; danger?: boolean; typeToConfirm?: string;
  done?: (data: Record<string, unknown>) => void; /** where to go once it's done (a page that's gone after it) */ goTo?: string; fields?: Field[]; small?: boolean;
  /** draw it as a row in a group: an icon and a quiet line under the label */
  row?: { icon: IconName; sub?: string };
}) {
  const post = useAdminPost();
  const say = useToast();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [typed, setTyped] = useState("");
  const [values, setValues] = useState<Record<string, string>>(Object.fromEntries(fields.map((f) => [f.name, f.initial ?? ""])));
  const [err, setErr] = useState("");
  const go = async () => {
    setBusy(true);
    setErr("");
    const r = await post(url, { ...body, ...Object.fromEntries(fields.map((f) => [f.name, f.type === "number" ? Number(values[f.name]) : values[f.name]])) });
    setBusy(false);
    if (!r.ok) return setErr(r.error);
    setOpen(false);
    setTyped("");
    say(true, String(r.data.message ?? "done"));
    done?.(r.data);
    if (goTo) router.push(goTo);
    else router.refresh();
  };
  const blocked = (typeToConfirm && typed.trim().toUpperCase() !== typeToConfirm.toUpperCase()) || fields.some((f) => !f.optional && !values[f.name]?.trim());
  const start = () => { setErr(""); setOpen(true); };
  return (
    <>
      {row ? (
        <button type="button" onClick={start} className="group flex min-h-[68px] w-full items-center gap-4 px-5 py-3.5 text-left transition hover:bg-s2 active:bg-s3">
          <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${danger ? "bg-bad/12 text-bad" : "bg-s3 text-ink/80"}`}><Icon name={row.icon} className="h-[19px] w-[19px]" /></span>
          <span className="min-w-0 flex-1">
            <span className={`block text-[15px] leading-snug ${danger ? "text-bad" : ""}`}>{label}</span>
            {row.sub ? <span className="mt-0.5 block text-[13px] leading-snug text-quiet">{row.sub}</span> : null}
          </span>
          <Icon name="chevron" className="h-[18px] w-[18px] text-quiet transition group-hover:translate-x-0.5" />
        </button>
      ) : (
        <button type="button" className={`${danger ? BTN.danger : BTN.plain} ${small ? "!h-9 !px-4 !text-[14px]" : ""}`} onClick={start}>{label}</button>
      )}
      {open ? (
        <Modal title={label} danger={danger} onClose={() => !busy && setOpen(false)}>
          <form className="grid gap-4" onSubmit={(e) => { e.preventDefault(); if (!blocked && !busy) void go(); }}>
            <p className="text-[15px] leading-relaxed text-ink/80">{confirm}</p>
            {fields.map((f) => (
              <label key={f.name} className="grid gap-1.5 text-[13px] text-quiet">{f.label}
                {f.options ? (
                  <select value={values[f.name]} onChange={(e) => setValues({ ...values, [f.name]: e.target.value })} className={FIELD}>
                    {f.options.map((o) => <option key={o}>{o}</option>)}
                  </select>
                ) : (
                  <input type={f.type ?? "text"} value={values[f.name]} onChange={(e) => setValues({ ...values, [f.name]: e.target.value })} placeholder={f.placeholder} className={FIELD} />
                )}
              </label>
            ))}
            {typeToConfirm ? (
              <label className="grid gap-1.5 text-[13px] text-quiet">type <span className="font-mono text-ink">{typeToConfirm}</span> to go ahead
                <input value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" spellCheck={false} className={`${FIELD} font-mono`} />
              </label>
            ) : null}
            {err ? <p className="a-pop rounded-2xl bg-bad/10 px-4 py-3 text-[14px] text-bad">{err}</p> : null}
            <div className="mt-2 grid grid-cols-2 gap-2">
              <button type="button" disabled={busy} onClick={() => setOpen(false)} className={BTN.plain}>cancel</button>
              <button type="submit" disabled={!!blocked || busy} className={danger ? BTN.dangerMain : BTN.main}>{busy ? "working…" : label}</button>
            </div>
          </form>
        </Modal>
      ) : null}
    </>
  );
}

/* ---------- saved the moment they change ---------- */

/** the switch itself, with a little spring in the knob */
export function Switch({ on, busy, onClick, label }: { on: boolean; busy?: boolean; onClick: () => void; label: string }) {
  return (
    <button type="button" role="switch" aria-checked={on} aria-label={label} disabled={busy} onClick={onClick}
      className={`relative h-8 w-[52px] shrink-0 rounded-full transition-colors duration-300 disabled:opacity-60 ${on ? "bg-ok" : "bg-s3"}`}>
      <span className={`a-spring absolute top-1 h-6 w-6 rounded-full shadow-[0_2px_6px_rgba(0,0,0,0.35)] transition-all ${on ? "left-[24px] bg-paper" : "left-1 bg-quiet"}`} />
    </button>
  );
}

/** an on/off row that saves at once; `confirmOff` / `confirmOn` ask first in a pop-up */
export function Toggle({ label, hint, value, url, body, field, confirmOff, confirmOn, icon }: {
  label: string; hint?: string; value: boolean; url: string; body?: Record<string, unknown>; field: string; confirmOff?: string; confirmOn?: string; icon?: IconName;
}) {
  const post = useAdminPost();
  const say = useToast();
  const router = useRouter();
  const [on, setOn] = useState(value);
  const [busy, setBusy] = useState(false);
  const [ask, setAsk] = useState<boolean | null>(null);
  useEffect(() => setOn(value), [value]);
  const save = async (next: boolean) => {
    setAsk(null);
    setOn(next);
    setBusy(true);
    const r = await post(url, { ...body, [field]: next });
    setBusy(false);
    if (!r.ok) {
      setOn(!next);
      return say(false, r.error);
    }
    say(true, `${label}: ${next ? "on" : "off"}`);
    router.refresh();
  };
  const flip = () => {
    const next = !on;
    if (next ? confirmOn : confirmOff) setAsk(next);
    else void save(next);
  };
  return (
    <div className="flex min-h-[68px] items-center gap-4 px-5 py-3.5">
      {icon ? <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full transition-colors ${on ? "bg-ok/12 text-ok" : "bg-s3 text-ink/80"}`}><Icon name={icon} className="h-[19px] w-[19px]" /></span> : null}
      <div className="min-w-0 flex-1">
        <div className="text-[15px] leading-snug">{label}</div>
        {hint ? <div className="mt-0.5 text-[13px] leading-snug text-quiet">{hint}</div> : null}
      </div>
      <Switch on={on} busy={busy} onClick={flip} label={label} />
      {ask !== null ? (
        <Modal title={ask ? `turn ${label} on?` : `turn ${label} off?`} danger={!ask} onClose={() => setAsk(null)}>
          <p className="text-[15px] leading-relaxed text-ink/80">{ask ? confirmOn : confirmOff}</p>
          <div className="mt-6 grid grid-cols-2 gap-2">
            <button type="button" onClick={() => setAsk(null)} className={BTN.plain}>cancel</button>
            <button type="button" onClick={() => void save(ask)} className={ask ? BTN.main : BTN.dangerMain}>turn {ask ? "on" : "off"}</button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}

/** a choice of a few, saved at once (a shirt's status, say) */
export function Segmented<T extends string>({ value, options, url, body, field, label, compact }: {
  value: T; options: { value: T; label: string; tone?: "ok" | "warn" | "off" }[]; url: string; body?: Record<string, unknown>; field: string; label: string; compact?: boolean;
}) {
  const post = useAdminPost();
  const say = useToast();
  const router = useRouter();
  const [v, setV] = useState(value);
  const [busy, setBusy] = useState(false);
  useEffect(() => setV(value), [value]);
  const pick = async (next: T) => {
    if (next === v || busy) return;
    const was = v;
    setV(next);
    setBusy(true);
    const r = await post(url, { ...body, [field]: next });
    setBusy(false);
    if (!r.ok) {
      setV(was);
      return say(false, r.error);
    }
    say(true, `${label}: ${options.find((o) => o.value === next)?.label}`);
    router.refresh();
  };
  const tone = { ok: "bg-ok text-black", warn: "bg-warn text-black", off: "bg-ink text-paper" };
  return (
    <div role="radiogroup" aria-label={label} className={`inline-flex rounded-full bg-s2 p-1 ${busy ? "opacity-70" : ""}`}>
      {options.map((o) => (
        <button key={o.value} type="button" role="radio" aria-checked={v === o.value} onClick={() => void pick(o.value)}
          className={`a-press whitespace-nowrap rounded-full ${compact ? "px-3 py-1.5 text-[13px]" : "px-4 py-2 text-[14px]"} ${v === o.value ? `${tone[o.tone ?? "off"]} font-semibold shadow-sm` : "text-quiet hover:text-ink"}`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

/**
 * A form's "save changes" bar: it springs up once anything differs from what's saved, with discard and save; a
 * change that moves prices or closes the shop asks first. Leaving the page with changes unsaved asks too.
 */
export function SaveBar({ dirty, busy, onSave, onDiscard, summary, warn }: {
  dirty: boolean; busy: boolean; onSave: () => void; onDiscard: () => void; summary: string; warn?: string | null;
}) {
  const [ask, setAsk] = useState(false);
  useEffect(() => {
    if (!dirty) return;
    const leave = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", leave);
    return () => window.removeEventListener("beforeunload", leave);
  }, [dirty]);
  return (
    <>
      <div aria-hidden={!dirty} className={`a-spring fixed inset-x-3 bottom-[88px] z-40 mx-auto max-w-[640px] transition-all md:bottom-6 md:left-[17rem] ${dirty ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-[140%] opacity-0"}`}>
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-[28px] bg-s3 py-2.5 pl-5 pr-2.5 shadow-[0_16px_50px_rgba(0,0,0,0.55)]">
          <span className="min-w-0 text-[14px]"><span className="mr-2 inline-block h-2 w-2 rounded-full bg-warn" />{summary} changed</span>
          <div className="flex gap-2">
            <button type="button" disabled={busy} onClick={onDiscard} className={`${BTN.plain} !h-10 !bg-s2`}>discard</button>
            <button type="button" disabled={busy} onClick={() => (warn ? setAsk(true) : onSave())} className={`${BTN.main} !h-10`}>{busy ? "saving…" : "save"}</button>
          </div>
        </div>
      </div>
      {ask ? (
        <Modal title="save these changes?" onClose={() => setAsk(false)}>
          <p className="text-[15px] leading-relaxed text-ink/80">{warn}</p>
          <div className="mt-6 grid grid-cols-2 gap-2">
            <button type="button" onClick={() => setAsk(false)} className={BTN.plain}>cancel</button>
            <button type="button" onClick={() => { setAsk(false); onSave(); }} className={BTN.main}>save</button>
          </div>
        </Modal>
      ) : null}
    </>
  );
}

/** a short text note on an order or customer, saved with who wrote it */
export function NoteForm({ url, body }: { url: string; body: Record<string, unknown> }) {
  const post = useAdminPost();
  const say = useToast();
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <form className="grid gap-2" onSubmit={async (e) => {
      e.preventDefault();
      if (!text.trim()) return;
      setBusy(true);
      const r = await post(url, { ...body, text });
      setBusy(false);
      if (r.ok) { setText(""); say(true, "note saved"); router.refresh(); } else say(false, r.error);
    }}>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2} maxLength={2000} placeholder="a note for yourself (the buyer never sees it)"
        className={`${FIELD} !h-auto resize-y py-3 leading-relaxed`} />
      {text.trim() ? <div className="a-pop"><button disabled={busy} className={`${BTN.main} !h-10`}>{busy ? "saving…" : "add note"}</button></div> : null}
    </form>
  );
}

/** "3 min ago", kept fresh */
export function Ago({ iso }: { iso: string }) {
  const [, tick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => tick((n) => n + 1), 15_000);
    return () => window.clearInterval(id);
  }, []);
  const s = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 1000));
  return <span title={new Date(iso).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}>{s < 45 ? "just now" : s < 3600 ? `${Math.round(s / 60)} min ago` : s < 86400 ? `${Math.round(s / 3600)} h ago` : `${Math.round(s / 86400)} d ago`}</span>;
}
