"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, startTransition, useCallback, useContext, useEffect, useRef, useState, useTransition } from "react";
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
            <div key={t.id} className="a-pop pointer-events-auto flex items-start gap-3 rounded-[12px] bg-s3 px-4 py-3.5 text-[14px] shadow-[0_12px_40px_rgba(0,0,0,0.5)]">
              <span className={`mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-s2 ${t.ok ? "text-ok" : "text-bad"}`}><Icon name={t.ok ? "check" : "x"} className="h-3.5 w-3.5" /></span>
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

/** the admin's map: the overview, then five sections that open to show their pages */
type Item = [href: string, label: string, icon: IconName];
const HOME: Item = ["/admin", "overview", "home"];
const SECTIONS: { name: string; icon: IconName; items: Item[] }[] = [
  { name: "sales", icon: "orders", items: [["/admin/orders", "orders", "orders"], ["/admin/money", "money", "money"]] },
  { name: "customers", icon: "people", items: [["/admin/people", "people", "people"], ["/admin/accounts", "accounts", "user"]] },
  { name: "shop", icon: "shirt", items: [["/admin/products", "shirts", "shirt"], ["/admin/prices", "prices", "card"], ["/admin/words", "site words", "note"]] },
  { name: "visitors", icon: "visitors", items: [["/admin/live", "live now", "live"], ["/admin/visitors", "visits", "visitors"], ["/admin/insights", "insights", "chart"]] },
  { name: "system", icon: "settings", items: [["/admin/status", "health", "shield"], ["/admin/settings", "settings", "settings"], ["/admin/audit", "audit log", "list"]] },
];
/** on a phone, the four used most along the bottom, and everything else under "more" */
const BAR: Item[] = [HOME, ["/admin/orders", "orders", "orders"], ["/admin/people", "people", "people"], ["/admin/live", "live", "live"]];

const isOn = (path: string, href: string) => (href === "/admin" ? path === "/admin" : path === href || path.startsWith(href + "/"));

function LiveCount({ tiny }: { tiny?: boolean }) {
  const { data } = usePoll<{ now: number }>("/api/admin/live?count=1", 15_000, { now: -1 });
  if (data.now <= 0) return null;
  return tiny
    ? <span className="tnum absolute -right-1 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-ink px-1 text-[10px] font-bold text-paper">{data.now}</span>
    : <span className="tnum ml-auto inline-flex items-center gap-1.5 text-[13px] text-ink/80"><span className="h-1.5 w-1.5 rounded-full bg-ok" />{data.now}</span>;
}

const OPEN_KEY = "admin-nav-open";

/** the sections, each opening to its pages; the one you're in is always open, the rest stay as you left them */
function Links({ path, onGo }: { path: string; onGo?: () => void }) {
  const here = SECTIONS.find((sec) => sec.items.some(([href]) => isOn(path, href)))?.name;
  const [open, setOpen] = useState<string[]>(here ? [here] : []);
  useEffect(() => {
    try {
      const kept = JSON.parse(localStorage.getItem(OPEN_KEY) ?? "[]") as string[];
      if (Array.isArray(kept)) setOpen((o) => [...new Set([...o, ...kept])]);
    } catch {}
  }, []);
  useEffect(() => {
    if (here) setOpen((o) => (o.includes(here) ? o : [...o, here]));
  }, [here]);
  const flip = (name: string) => setOpen((o) => {
    const next = o.includes(name) ? o.filter((x) => x !== name) : [...o, name];
    try { localStorage.setItem(OPEN_KEY, JSON.stringify(next)); } catch {}
    return next;
  });
  const link = ([href, label, icon]: Item, sub?: boolean) => {
    const on = isOn(path, href);
    return (
      <Link key={href} href={href} onClick={onGo} aria-current={on ? "page" : undefined}
        className={`a-press flex h-10 items-center gap-3 rounded-[10px] px-3 text-[15px] ${sub ? "pl-[46px]" : ""} ${on ? "bg-s2 font-medium text-ink" : "text-ink/65 hover:bg-s1 hover:text-ink"}`}>
        {sub ? null : <Icon name={icon} className="h-[19px] w-[19px]" />}{label}{href === "/admin/live" ? <LiveCount /> : null}
      </Link>
    );
  };
  return (
    <div className="grid gap-1">
      {link(HOME)}
      {SECTIONS.map((sec) => {
        const isOpen = open.includes(sec.name);
        const has = sec.name === here;
        return (
          <div key={sec.name}>
            <button type="button" onClick={() => flip(sec.name)} aria-expanded={isOpen}
              className={`a-press flex h-10 w-full items-center gap-3 rounded-[10px] px-3 text-left text-[15px] hover:bg-s1 hover:text-ink ${has ? "text-ink" : "text-ink/65"}`}>
              <Icon name={sec.icon} className="h-[19px] w-[19px]" />{sec.name}
              <span className="ml-auto flex items-center gap-2">
                {!isOpen && sec.name === "visitors" ? <LiveCount /> : null}
                <Icon name="down" className={`h-4 w-4 text-quiet transition-transform duration-150 ${isOpen ? "rotate-180" : ""}`} />
              </span>
            </button>
            <div className={`grid transition-[grid-template-rows] duration-150 ease-out ${isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}>
              <div className="grid min-h-0 gap-0.5 overflow-hidden" inert={!isOpen}>
                <div className="h-0.5" />
                {sec.items.map((it) => link(it, true))}
                <div className="h-1" />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function Nav({ email }: { email: string }) {
  const path = usePathname();
  const [more, setMore] = useState(false);
  useEffect(() => setMore(false), [path]);
  const inBar = BAR.some(([href]) => isOn(path, href));
  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col overflow-y-auto border-r border-line/40 bg-paper px-3 pb-5 pt-6 md:flex">
        <Link href="/admin" className="mb-8 px-3 text-[24px] font-extrabold tracking-[-0.05em]">sahn<span className="ml-1.5 text-[14px] font-medium tracking-normal text-quiet">admin</span></Link>
        <Links path={path} />
        <div className="mt-auto grid gap-0.5 pt-8 text-[14px] text-ink/65">
          <span className="truncate px-3 pb-2 text-[13px] text-quiet" title={email}>{email}</span>
          <a href="/" target="_blank" rel="noreferrer" className="a-press flex h-10 items-center gap-3 rounded-[10px] px-3 hover:bg-s1 hover:text-ink"><Icon name="out" className="h-[18px] w-[18px]" />open the shop</a>
          <SignOut />
        </div>
      </aside>

      <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-line/40 bg-paper pb-[env(safe-area-inset-bottom)] md:hidden">
        {BAR.map(([href, label, icon]) => {
          const on = isOn(path, href);
          return (
            <Link key={href} href={href} aria-current={on ? "page" : undefined} className="a-press flex flex-col items-center gap-1 pb-2 pt-2.5 text-[11px]">
              <span className={`relative grid h-8 w-14 place-items-center rounded-full ${on ? "bg-s2 text-ink" : "text-quiet"}`}><Icon name={icon} className="h-[21px] w-[21px]" />{href === "/admin/live" ? <LiveCount tiny /> : null}</span>
              <span className={on ? "font-medium text-ink" : "text-quiet"}>{label}</span>
            </Link>
          );
        })}
        <button type="button" onClick={() => setMore(true)} className="a-press flex flex-col items-center gap-1 pb-2 pt-2.5 text-[11px]">
          <span className={`grid h-8 w-14 place-items-center rounded-full ${!inBar ? "bg-s2 text-ink" : "text-quiet"}`}><Icon name="list" className="h-[21px] w-[21px]" /></span>
          <span className={!inBar ? "font-medium text-ink" : "text-quiet"}>more</span>
        </button>
      </nav>
      {more ? (
        <Modal title="everything" onClose={() => setMore(false)}>
          <div className="-mx-3 mt-2"><Links path={path} onGo={() => setMore(false)} /></div>
          <div className="-mx-3 mt-6 grid gap-0.5 border-t border-line/40 pt-4 text-[15px] text-ink/65">
            <a href="/" target="_blank" rel="noreferrer" className="flex h-10 items-center gap-3 rounded-[10px] px-3"><Icon name="out" className="h-[18px] w-[18px]" />open the shop</a>
            <SignOut />
          </div>
        </Modal>
      ) : null}
    </>
  );
}

/**
 * The shop's on/off, always at the top right: one tap, a pop-up to be sure, and it's done. Closed, people can
 * still look and fill their bag, and checkout shows the closed message.
 */
export function ShopSwitch({ open, connected }: { open: boolean; connected: boolean }) {
  const post = useAdminPost();
  const say = useToast();
  const router = useRouter();
  const [on, setOn] = useState(open);
  const [ask, setAsk] = useState(false);
  useEffect(() => setOn(open), [open]);
  const live = on && connected;
  // flips at once; the save runs behind it and flips back if it fails
  const save = async (next: boolean) => {
    setAsk(false);
    setOn(next);
    const r = await post("/api/admin/settings", { open: next });
    if (!r.ok) {
      setOn(!next);
      return say(false, r.error);
    }
    say(true, next ? "the shop is live" : "the shop is closed: checkout is off");
    startTransition(() => router.refresh());
  };
  return (
    <>
      <button type="button" onClick={() => (!connected ? undefined : on ? setAsk(true) : void save(true))} disabled={!connected} title={connected ? undefined : "payments aren't connected"}
        className="a-press inline-flex h-10 items-center gap-2.5 rounded-[12px] bg-s1 pl-4 pr-1.5 text-[14px] font-medium hover:bg-s2">
        <span className={`h-2 w-2 rounded-full ${live ? "bg-ok" : "bg-warn"}`} />
        {!connected ? "not connected" : live ? "shop live" : "shop closed"}
        <span className={`relative h-7 w-12 rounded-full transition-colors duration-100 ${live ? "bg-ink" : "bg-s3"}`}><span className={`a-spring absolute top-1 h-5 w-5 rounded-full shadow transition-[left,background-color] ${live ? "left-6 bg-paper" : "left-1 bg-quiet"}`} /></span>
      </button>
      {ask ? (
        <Modal title="close the shop?" danger onClose={() => setAsk(false)}>
          <p className="text-[15px] leading-relaxed text-ink/80">checkout closes on the whole site at once. people can still look and fill their bag; anyone paying right now can finish.</p>
          <div className="mt-6 grid grid-cols-2 gap-2">
            <button type="button" onClick={() => setAsk(false)} className={BTN.plain}>cancel</button>
            <button type="button" onClick={() => void save(false)} className={BTN.dangerMain}>close it</button>
          </div>
        </Modal>
      ) : null}
    </>
  );
}

function SignOut() {
  const post = useAdminPost();
  return (
    <button type="button" className="a-press flex h-10 items-center gap-3 rounded-[10px] px-3 text-left hover:bg-s1 hover:text-ink" onClick={async () => {
      await post("/api/admin/session", { signOut: true });
      window.location.href = "/admin/login";
    }}><Icon name="signout" className="h-[18px] w-[18px]" />sign out</button>
  );
}

export function SignOutAll() {
  return <Act row={{ icon: "signout", sub: "every admin session on every device ends now, this one too" }} danger label="sign out everywhere" confirm="every admin session, on every device, ends now (this one too)." url="/api/admin/session" body={{ signOut: true, all: true }} goTo="/admin/login" />;
}

/* ---------- buttons, pop-ups ---------- */

const btn = "a-press inline-flex h-11 items-center justify-center gap-2 rounded-[10px] px-5 text-[15px] font-medium disabled:cursor-not-allowed disabled:opacity-40";
export const BTN = {
  plain: `${btn} bg-s2 text-ink hover:bg-s3`,
  main: `${btn} bg-ink font-semibold text-paper hover:bg-ink/90`,
  danger: `${btn} bg-bad/12 text-bad hover:bg-bad/20`,
  dangerMain: `${btn} bg-bad font-semibold text-black hover:bg-bad/90`,
};
export const FIELD = "h-12 w-full rounded-[10px] bg-s2 px-4 text-[15px] text-ink ring-1 ring-transparent transition placeholder:text-quiet/70 focus:bg-s3 focus:ring-ink/30 focus:outline-none disabled:opacity-60";

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
        className="a-sheet max-h-[92dvh] w-full overflow-y-auto rounded-t-[18px] bg-s1 px-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-3 shadow-[0_-20px_60px_rgba(0,0,0,0.5)] md:max-w-[460px] md:rounded-[18px] md:pb-6 md:pt-6">
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
    else startTransition(() => router.refresh());
  };
  const blocked = (typeToConfirm && typed.trim().toUpperCase() !== typeToConfirm.toUpperCase()) || fields.some((f) => !f.optional && !values[f.name]?.trim());
  const start = () => { setErr(""); setOpen(true); };
  return (
    <>
      {row ? (
        <button type="button" onClick={start} className="group flex min-h-[68px] w-full items-center gap-4 px-5 py-3.5 text-left transition hover:bg-s2 active:bg-s3">
          <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full bg-s2 ${danger ? "text-bad" : "text-ink/75"}`}><Icon name={row.icon} className="h-[19px] w-[19px]" /></span>
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
            {err ? <p className="a-pop rounded-[12px] bg-bad/10 px-4 py-3 text-[14px] text-bad">{err}</p> : null}
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
    <button type="button" role="switch" aria-checked={on} aria-label={label} aria-busy={busy} onClick={onClick}
      className={`a-press relative h-8 w-[52px] shrink-0 rounded-full transition-colors duration-100 ${on ? "bg-ink" : "bg-s3"}`}>
      <span className={`a-spring absolute top-1 h-6 w-6 rounded-full shadow-[0_1px_4px_rgba(0,0,0,0.35)] transition-[left,background-color] ${on ? "left-[24px] bg-paper" : "left-1 bg-quiet"}`} />
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
    startTransition(() => router.refresh());
  };
  const flip = () => {
    const next = !on;
    if (next ? confirmOn : confirmOff) setAsk(next);
    else void save(next);
  };
  return (
    <div className="flex min-h-[68px] items-center gap-4 px-5 py-3.5">
      {icon ? <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-s2 text-ink/75"><Icon name={icon} className="h-[19px] w-[19px]" /></span> : null}
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
    startTransition(() => router.refresh());
  };
  const tone = { ok: "bg-ink text-paper", warn: "bg-ink text-paper", off: "bg-ink text-paper" };
  return (
    <div role="radiogroup" aria-label={label} aria-busy={busy} className="inline-flex rounded-[12px] bg-s2 p-1">
      {options.map((o) => (
        <button key={o.value} type="button" role="radio" aria-checked={v === o.value} onClick={() => void pick(o.value)}
          className={`a-press whitespace-nowrap rounded-[9px] ${compact ? "px-3 py-1.5 text-[13px]" : "px-4 py-2 text-[14px]"} ${v === o.value ? `${tone[o.tone ?? "off"]} font-semibold shadow-sm` : "text-quiet hover:text-ink"}`}>
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
      <div aria-hidden={!dirty} className={`a-spring fixed inset-x-3 bottom-[88px] z-40 mx-auto max-w-[640px] transition-all md:bottom-6 md:left-[16rem] ${dirty ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-[140%] opacity-0"}`}>
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-[14px] bg-s3 py-2.5 pl-5 pr-2.5 shadow-[0_16px_50px_rgba(0,0,0,0.55)]">
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
      if (r.ok) { setText(""); say(true, "note saved"); startTransition(() => router.refresh()); } else say(false, r.error);
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

/* ---------- going somewhere on the same page ---------- */

/**
 * A tab or a period changes only the page's search params, so Next shows no loading page for it. This keeps the
 * page's own frame and, the moment one is tapped, dims what's showing and runs a line along the top until the new
 * numbers are in; the tab itself turns on at once.
 */
const Going = createContext<{ pending: boolean; go: (href: string) => void }>({ pending: false, go: () => {} });

export function Pending({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  const go = useCallback((href: string) => start(() => router.push(href, { scroll: false })), [router]);
  return (
    <Going.Provider value={{ pending, go }}>
      {pending ? <div aria-hidden className="a-loading-now fixed inset-x-0 top-0 z-50 h-[2px] overflow-hidden md:left-60"><span className="block h-full w-2/5 bg-ink/70" /></div> : null}
      <div aria-busy={pending || undefined} className={`transition-opacity duration-100 ${pending ? "pointer-events-none opacity-45" : ""}`}>{children}</div>
    </Going.Provider>
  );
}

/** pick one of a few views, as links (search params): it turns on at once, and the page follows */
export function Tabs({ items, active }: { items: { href: string; label: string; count?: number; key: string }[]; active: string }) {
  const { go } = useContext(Going);
  const [want, setWant] = useState<string | null>(null);
  useEffect(() => setWant(null), [active]);
  const on = want ?? active;
  return (
    <nav className="-mx-4 mb-8 overflow-x-auto px-4 [scrollbar-width:none] md:mx-0 md:px-0">
      <div className="inline-flex gap-1 rounded-[12px] bg-s1 p-1">
        {items.map((t) => (
          <Link key={t.key} href={t.href} aria-current={t.key === on ? "page" : undefined}
            onClick={(e) => {
              if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
              e.preventDefault();
              if (t.key === on) return;
              setWant(t.key);
              go(t.href);
            }}
            className={`a-press whitespace-nowrap rounded-[9px] px-4 py-2 text-[14px] ${t.key === on ? "bg-ink font-semibold text-paper" : "text-quiet hover:text-ink"}`}>
            {t.label}{t.count != null ? <span className={`tnum ml-1.5 ${t.key === on ? "text-paper/60" : "text-quiet/70"}`}>{t.count}</span> : null}
          </Link>
        ))}
      </div>
    </nav>
  );
}
