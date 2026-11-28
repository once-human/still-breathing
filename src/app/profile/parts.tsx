"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { AddressFields, EMPTY, addressLine, input, post } from "@/components/shop/AddressFields";
import { SIZE_ORDER, type Design, type Size } from "@/content/tee";
import type { Address } from "@/lib/shop/account";
import { pickedSize, refreshMe } from "@/lib/shop/me";
import { DropsBox } from "@/components/shop/DropsBox";
import type { Details } from "@/lib/shop/india";

const button = "flex h-12 w-full items-center justify-between bg-ink px-4 text-[15px] font-semibold text-paper hover:bg-ink/90 disabled:opacity-60";
const quiet = "flex h-12 w-full items-center justify-center gap-3 border border-line px-4 text-[15px] text-ink hover:border-ink disabled:opacity-60";
type Bad = { field?: string; error: string } | null;
const asBad = (e: unknown): Bad => ({ field: (e as { field?: string }).field, error: (e as Error).message });
const RESEND_S = 30;
const H2 = "border-t border-line pt-1.5 text-[13px] text-quiet";

const ago = (iso: string) => {
  const s = (Date.now() - Date.parse(iso)) / 1000;
  if (s < 90) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" }).toLowerCase();
};

/** a password field with a show / hide switch */
function Secret({ value, onChange, label, auto, bad, focus }: { value: string; onChange: (v: string) => void; label: string; auto: string; bad?: boolean; focus?: boolean }) {
  const [show, setShow] = useState(false);
  return (
    <label className="mt-4 block text-[13px] text-quiet">{label}
      <span className="relative block">
        <input type={show ? "text" : "password"} value={value} onChange={(e) => onChange(e.target.value)} autoComplete={auto} autoFocus={focus} maxLength={128}
          spellCheck={false} autoCapitalize="off" className={`${input} !pr-16`} aria-invalid={bad} />
        <button type="button" onClick={() => setShow(!show)} className="absolute right-1 top-1/2 mt-0.5 h-10 -translate-y-1/2 px-3 text-[13px] text-quiet hover:text-ink">{show ? "hide" : "show"}</button>
      </span>
    </label>
  );
}

/* ---------- signing in (and making a profile, the same way) ---------- */

/**
 * Google, or an email: then a code to it (six boxes, filled by a paste or the phone itself, sent by the sixth
 * digit), or the password if they've set one. A new profile is asked its name once, which it can skip.
 */
export function SignIn({ next, google, said }: { next: string | null; google: boolean; said: string | null }) {
  const router = useRouter();
  const [step, setStep] = useState<"email" | "code" | "password" | "hello">("email");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [bad, setBad] = useState<Bad>(said ? { error: said } : null);
  const [wait, setWait] = useState(0);

  useEffect(() => {
    if (wait <= 0) return;
    const t = setTimeout(() => setWait(wait - 1), 1000);
    return () => clearTimeout(t);
  }, [wait]);

  const done = (fresh?: boolean) => {
    if (fresh) return setStep("hello");
    if (next) router.push(next);
    router.refresh();
  };

  async function send(e?: React.FormEvent) {
    e?.preventDefault();
    setBusy(true);
    setBad(null);
    try {
      await post("/api/shop/account", { action: "code", email });
      setStep("code");
      setWait(RESEND_S);
    } catch (err) {
      setBad(asBad(err));
    } finally {
      setBusy(false);
    }
  }

  async function verify(code: string) {
    setBusy(true);
    setBad(null);
    try {
      done((await post<{ ok: true; fresh?: boolean }>("/api/shop/account", { action: "verify", email, code })).fresh);
    } catch (err) {
      setBad(asBad(err));
    } finally {
      setBusy(false);
    }
  }

  async function withPassword(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setBad(null);
    try {
      done((await post<{ ok: true; fresh?: boolean }>("/api/shop/account", { action: "password", email, password: pw })).fresh);
    } catch (err) {
      setBad(asBad(err));
      setBusy(false);
    }
  }

  if (step === "hello") return <Hello next={next} />;

  if (step === "code")
    return (
      <div className="menu-in max-w-[420px]">
        <p className={H2}>check your email</p>
        <p className="mt-4 text-[22px] leading-tight font-semibold tracking-[-0.02em]">the code&apos;s on its way.</p>
        <p className="mt-2 text-[15px] text-ink/85">6 digits, to <span className="text-ink">{email}</span>. it works for 10 minutes.</p>
        <Code key={email} busy={busy} bad={!!bad} onCode={verify} />
        {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
        <div className="mt-5 flex flex-wrap gap-x-5 gap-y-1 text-[13px] text-quiet">
          <button type="button" disabled={wait > 0 || busy} onClick={() => send()} className="hit hover:text-ink disabled:hover:text-quiet">
            {wait > 0 ? <>new code in <span className="tnum">{wait}</span>s</> : "send a new code"}
          </button>
          <button type="button" onClick={() => { setStep("password"); setBad(null); }} className="hit hover:text-ink">use my password</button>
          <button type="button" onClick={() => { setStep("email"); setBad(null); }} className="hit hover:text-ink">another email</button>
        </div>
        <p className="mt-4 text-[12px] text-quiet">not there? look in spam or promotions; it comes from sahn.</p>
      </div>
    );

  if (step === "password")
    return (
      <form onSubmit={withPassword} className="menu-in max-w-[420px]">
        <p className={H2}>with your password</p>
        <input type="email" name="email" autoComplete="username" value={email} readOnly hidden />
        <p className="mt-4 text-[15px] text-ink/85">{email}</p>
        <Secret label="password" value={pw} onChange={(v) => { setPw(v); setBad(null); }} auto="current-password" bad={bad?.field === "password"} focus />
        {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
        <button disabled={busy || !pw} className={`mt-5 ${button}`}><span>{busy ? "one moment.." : "sign in"}</span><span aria-hidden>→</span></button>
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 text-[13px] text-quiet">
          <button type="button" onClick={() => send()} className="hit hover:text-ink">forgot it? email me a code</button>
          <button type="button" onClick={() => { setStep("email"); setBad(null); }} className="hit hover:text-ink">another email</button>
        </div>
      </form>
    );

  return (
    <div className="max-w-[420px]">
      {google ? (
        <>
          <a href={`/api/shop/auth/google${next ? `?next=${encodeURIComponent(next)}` : ""}`} className={quiet}>
            <GoogleMark /> continue with google
          </a>
          <p className="my-5 flex items-center gap-3 text-[12px] text-quiet"><span className="h-px flex-1 bg-line" />or with your email<span className="h-px flex-1 bg-line" /></p>
        </>
      ) : <p className={H2}>with your email</p>}
      <form onSubmit={send}>
        <label className="mt-4 block text-[13px] text-quiet">email
          <input value={email} onChange={(e) => { setEmail(e.target.value); setBad(null); }} type="email" inputMode="email" autoComplete="email" required maxLength={120}
            className={input} aria-invalid={bad?.field === "email"} />
        </label>
        {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
        <button disabled={busy} className={`mt-5 ${button}`}><span>{busy ? "sending.." : "email me a code"}</span><span aria-hidden>→</span></button>
      </form>
      <button type="button" disabled={!email.includes("@")} onClick={() => { setStep("password"); setBad(null); }} className={`mt-3 ${quiet}`}>use a password instead</button>
      <p className="mt-4 text-[12px] leading-snug text-quiet">new here? this makes your profile; set a password later if you like. orders you placed before with this email show up in it. we only email you about your orders.</p>
    </div>
  );
}

function GoogleMark() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden className="h-[18px] w-[18px]">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
      <path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </svg>
  );
}

/** six boxes for the code: each digit moves you on, backspace moves you back, a paste or the phone's autofill fills them all */
function Code({ busy, bad, onCode }: { busy: boolean; bad: boolean; onCode: (code: string) => void }) {
  const [d, setD] = useState<string[]>(Array(6).fill(""));
  const boxes = useRef<(HTMLInputElement | null)[]>([]);
  const sent = useRef("");

  useEffect(() => { boxes.current[0]?.focus(); }, []);
  useEffect(() => {
    if (!bad) return;
    setD(Array(6).fill(""));
    sent.current = "";
    boxes.current[0]?.focus();
  }, [bad]);

  const fill = (from: number, text: string) => {
    const digits = text.replace(/\D/g, "").slice(0, 6 - from).split("");
    if (!digits.length) return;
    const n = [...d];
    digits.forEach((x, i) => (n[from + i] = x));
    setD(n);
    boxes.current[Math.min(5, from + digits.length)]?.focus();
    const code = n.join("");
    if (code.length === 6 && code !== sent.current) {
      sent.current = code;
      onCode(code);
    }
  };

  return (
    <div className="mt-6 grid grid-cols-6 gap-2" role="group" aria-label="the 6-digit code">
      {d.map((x, i) => (
        <input key={i} ref={(el) => { boxes.current[i] = el; }} value={x} disabled={busy}
          inputMode="numeric" autoComplete={i === 0 ? "one-time-code" : "off"} aria-label={`digit ${i + 1}`} maxLength={i === 0 ? 6 : 1}
          onChange={(e) => {
            const v = e.target.value.replace(/\D/g, "");
            if (!v) { const n = [...d]; n[i] = ""; setD(n); return; }
            fill(i, v.length > 1 && i > 0 ? v.slice(-1) : v);
          }}
          onPaste={(e) => { e.preventDefault(); fill(0, e.clipboardData.getData("text")); }}
          onKeyDown={(e) => {
            if (e.key === "Backspace" && !d[i] && i > 0) { const n = [...d]; n[i - 1] = ""; setD(n); boxes.current[i - 1]?.focus(); }
            if (e.key === "ArrowLeft" && i > 0) boxes.current[i - 1]?.focus();
            if (e.key === "ArrowRight" && i < 5) boxes.current[i + 1]?.focus();
          }}
          className={`h-14 w-full border bg-transparent text-center text-[24px] font-semibold tnum text-ink outline-none transition-colors focus:border-ink disabled:opacity-60 ${bad ? "border-ink/70" : x ? "border-ink/50" : "border-line"}`} />
      ))}
    </div>
  );
}

/** a new profile's one question: what to call you, and a mobile for the courier (both can wait) */
export function Hello({ next }: { next: string | null }) {
  const router = useRouter();
  const [drops, setDrops] = useState(false);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [bad, setBad] = useState<Bad>(null);
  const done = () => { router.replace(next ?? "/profile"); router.refresh(); };
  return (
    <form className="menu-in max-w-[420px]" onSubmit={async (e) => {
      e.preventDefault();
      setBusy(true);
      setBad(null);
      try {
        await post("/api/shop/account", { action: "profile", name, phone });
        if (drops) await post("/api/shop/account", { action: "drops", on: true, from: "welcome" }).catch(() => {});
        done();
      } catch (err) {
        setBad(asBad(err));
        setBusy(false);
      }
    }}>
      <p className={H2}>you&apos;re in</p>
      <p className="mt-4 text-[22px] leading-tight font-semibold tracking-[-0.02em]">welcome to sahn. what should we call you?</p>
      <p className="mt-2 text-[15px] text-ink/85">your name shows at the top of the site, and checkout fills it in. change it any time.</p>
      <label className="mt-6 block text-[13px] text-quiet">your name
        <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" maxLength={80} autoFocus className={input} aria-invalid={bad?.field === "name"} />
      </label>
      <label className="mt-4 block text-[13px] text-quiet">mobile, for the courier (optional)
        <span className="relative block">
          <span className="pointer-events-none absolute left-3 top-1/2 mt-0.5 -translate-y-1/2 text-[16px] text-quiet">+91</span>
          <input value={phone} onChange={(e) => setPhone(e.target.value)} type="tel" inputMode="tel" autoComplete="tel-national" maxLength={14} className={`${input} !pl-12`} aria-invalid={bad?.field === "phone"} />
        </span>
      </label>
      <DropsBox on={drops} onChange={setDrops} />
      {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
      <button disabled={busy || !name.trim()} className={`mt-6 ${button}`}><span>{busy ? "saving.." : "done"}</span><span aria-hidden>→</span></button>
      <button type="button" onClick={done} className="hit mt-3 block text-[13px] text-quiet hover:text-ink">skip for now</button>
    </form>
  );
}

/* ---------- the tabs ---------- */

const TABS = ["orders", "saved", "addresses", "details", "sign-in", "privacy", "activity"] as const;
type Tab = (typeof TABS)[number];

/** one pane at a time, kept in the address (#sign-in) so back and a reload land on it; on a phone the tabs scroll sideways */
export function ProfileTabs({ panes, counts }: { panes: Record<Tab, React.ReactNode>; counts: Partial<Record<Tab, number>> }) {
  const [tab, setTab] = useState<Tab>("orders");
  useEffect(() => {
    const read = () => {
      const h = decodeURIComponent(window.location.hash.slice(1)) as Tab;
      setTab(TABS.includes(h) ? h : "orders");
    };
    read();
    window.addEventListener("hashchange", read);
    return () => window.removeEventListener("hashchange", read);
  }, []);
  const pick = (t: Tab) => {
    setTab(t);
    history.replaceState(null, "", t === "orders" ? window.location.pathname + window.location.search : `#${t}`);
  };
  return (
    <div>
      <div role="tablist" aria-label="your profile" className="-mx-4 mb-8 flex gap-6 overflow-x-auto border-b border-line px-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {TABS.map((t) => (
          <button key={t} role="tab" type="button" aria-selected={tab === t} aria-controls={`pane-${t}`} id={`tab-${t}`} onClick={() => pick(t)}
            className={`relative -mb-px flex h-12 shrink-0 items-center gap-1.5 border-b-2 text-[15px] transition-colors ${tab === t ? "border-ink text-ink" : "border-transparent text-quiet hover:text-ink"}`}>
            {t}{counts[t] != null ? <span className="tnum text-[12px] text-quiet">{counts[t]}</span> : null}
          </button>
        ))}
      </div>
      {TABS.map((t) => (
        <div key={t} role="tabpanel" id={`pane-${t}`} aria-labelledby={`tab-${t}`} hidden={tab !== t} className={tab === t ? "menu-in" : undefined}>
          {panes[t]}
        </div>
      ))}
    </div>
  );
}

/* ---------- details ---------- */

export function Profile({ name: n0, phone: p0, email }: { name: string; phone: string; email: string }) {
  const router = useRouter();
  const [name, setName] = useState(n0);
  const [phone, setPhone] = useState(p0);
  const [state, setState] = useState<Bad | "saved">(null);
  const [busy, setBusy] = useState(false);
  const changed = name !== n0 || phone !== p0;
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await post("/api/shop/account", { action: "profile", name, phone });
      setState("saved");
      router.refresh();
    } catch (err) {
      setState(asBad(err));
    } finally {
      setBusy(false);
    }
  }
  const bad = state && state !== "saved" ? state : null;
  const saved = state === "saved" && !changed;
  return (
    <form onSubmit={save}>
      <h2 className={H2}>you</h2>
      <label className="mt-4 block text-[13px] text-quiet">name
        <input value={name} onChange={(e) => { setName(e.target.value); setState(null); }} autoComplete="name" maxLength={80} className={input} aria-invalid={bad?.field === "name"} />
      </label>
      <label className="mt-4 block text-[13px] text-quiet">mobile
        <span className="relative block">
          <span className="pointer-events-none absolute left-3 top-1/2 mt-0.5 -translate-y-1/2 text-[16px] text-quiet">+91</span>
          <input value={phone} onChange={(e) => { setPhone(e.target.value); setState(null); }} type="tel" inputMode="tel" autoComplete="tel-national" maxLength={14} className={`${input} !pl-12`} aria-invalid={bad?.field === "phone"} />
        </span>
      </label>
      <div className="mt-4 text-[13px] text-quiet">email
        <p className="mt-1 flex h-12 items-center border border-line/60 px-3 text-[16px] text-quiet">{email}</p>
        <p className="mt-1.5 text-[12px]">your email is your profile: every order placed with it shows here, signed in or not.</p>
      </div>
      {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
      <button disabled={busy || (!changed && !saved)} className={`mt-5 ${button}`}>
        <span>{busy ? "saving.." : saved ? "saved" : "save"}</span><span aria-hidden>{saved ? "✓" : "→"}</span>
      </button>
    </form>
  );
}

/** their size: every shirt opens on it */
export function SizePick({ size }: { size: Size | null }) {
  const router = useRouter();
  const [z, setZ] = useState<Size | null>(size);
  const pick = async (x: Size | null) => {
    setZ(x);
    if (x) pickedSize(x);
    await post("/api/shop/account", { action: "size", size: x }).catch(() => setZ(size));
    refreshMe();
    router.refresh();
  };
  return (
    <section>
      <h2 className={H2}>your size</h2>
      <p className="mt-3 text-[14px] text-quiet">every shirt opens on it. not sure? the <a href="/size-guide" className="draw text-ink">size guide</a> has each one in cm.</p>
      <div className="mt-4 grid grid-cols-6 gap-1.5" role="radiogroup" aria-label="your size">
        {SIZE_ORDER.map((x) => (
          <button key={x} type="button" role="radio" aria-checked={x === z} onClick={() => pick(x === z ? null : x)}
            className={`h-11 border text-[14px] transition-colors duration-200 ${x === z ? "border-ink bg-ink text-paper" : "border-line hover:border-quiet"}`}>{x}</button>
        ))}
      </div>
    </section>
  );
}

/** emails about new drops: off until they turn it on */
export function Drops({ on }: { on: boolean }) {
  const router = useRouter();
  const [v, setV] = useState(on);
  const [busy, setBusy] = useState(false);
  return (
    <section>
      <h2 className={H2}>emails</h2>
      <ul className="mt-2 text-[14px]">
        <li className="flex items-start justify-between gap-4 border-b border-line py-3">
          <span><span className="text-ink">your orders</span><span className="block text-quiet">confirmed, sent to print, on its way, delivered. always on: they&apos;re about something you bought.</span></span>
          <span className="shrink-0 text-[13px] text-quiet">on</span>
        </li>
        <li className="flex items-start justify-between gap-4 border-b border-line py-3">
          <span><span className="text-ink">new drops</span><span className="block text-quiet">one email when a new lineup or shirt comes out. nothing else, and off whenever you like.</span></span>
          <button type="button" role="switch" aria-checked={v} aria-label="emails about new drops" disabled={busy}
            onClick={async () => { setBusy(true); setV(!v); await post("/api/shop/account", { action: "drops", on: !v }).catch(() => setV(v)); router.refresh(); setBusy(false); }}
            className={`relative h-7 w-12 shrink-0 rounded-full transition-colors disabled:opacity-60 ${v ? "bg-ink" : "bg-line"}`}>
            <span className={`absolute top-1 h-5 w-5 rounded-full transition-[left] duration-150 ${v ? "left-6 bg-paper" : "left-1 bg-quiet"}`} />
          </button>
        </li>
      </ul>
    </section>
  );
}

/** take a shirt off the saved list */
export function Unsave({ design }: { design: Design }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  return (
    <button type="button" disabled={busy} onClick={async () => { setBusy(true); await post("/api/shop/account", { action: "save", design, on: false }).catch(() => {}); refreshMe(); router.refresh(); }}
      className="hit mt-2 text-[13px] text-quiet hover:text-ink">{busy ? "one moment.." : "remove"}</button>
  );
}

/* ---------- addresses ---------- */

export function Addresses({ list }: { list: Address[] }) {
  const router = useRouter();
  const [adding, setAdding] = useState(false);
  const [d, setD] = useState<Details>(EMPTY);
  const [bad, setBad] = useState<Bad>(null);
  const [busy, setBusy] = useState<string | null>(null);
  async function act(body: { action: string; id?: string; details?: Details }) {
    setBusy(body.id ?? body.action);
    setBad(null);
    try {
      await post("/api/shop/account", body);
      if (body.action === "add-address") { setAdding(false); setD(EMPTY); }
      router.refresh();
    } catch (err) {
      setBad(asBad(err));
    } finally {
      setBusy(null);
    }
  }
  return (
    <div>
      {list.length === 0 && !adding ? (
        <div className="border-t border-line pt-6">
          <p className="text-[22px] leading-tight font-semibold tracking-[-0.02em]">no addresses yet.</p>
          <p className="mt-2 max-w-[40ch] text-[15px] text-quiet">the places you send shirts to are kept here, so checkout fills itself in. each order adds its own.</p>
        </div>
      ) : (
        <ul className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {list.map((a, i) => (
            <li key={a.id} className="flex flex-col bg-s1 p-4 text-[14px]">
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-semibold text-ink">{a.name}</span>
                {i === 0 ? <span className="text-[12px] text-quiet">used first</span> : null}
              </div>
              <p className="mt-1 text-quiet">{addressLine(a)}</p>
              <p className="text-quiet">+91 {a.phone}</p>
              <div className="mt-auto flex gap-5 pt-4 text-[13px] text-quiet">
                {i > 0 ? <button type="button" disabled={!!busy} onClick={() => act({ action: "default-address", id: a.id })} className="hit hover:text-ink">use this first</button> : null}
                <button type="button" disabled={!!busy} onClick={() => act({ action: "remove-address", id: a.id })} className="hit hover:text-ink" aria-label={`remove the address ${addressLine(a)}`}>
                  {busy === a.id ? "one moment.." : "remove"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {bad && !adding && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
      {adding ? (
        <form onSubmit={(e) => { e.preventDefault(); act({ action: "add-address", details: d }); }} className="menu-in mt-10 max-w-[560px]">
          <h2 className={`mb-4 ${H2}`}>a new address</h2>
          <AddressFields d={d} onChange={setD} bad={bad?.field as keyof Details | undefined} email={false} />
          {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
          <div className="mt-5 grid grid-cols-2 gap-3">
            <button type="button" onClick={() => { setAdding(false); setBad(null); }} className={quiet}>cancel</button>
            <button disabled={!!busy} className={button}><span>{busy ? "saving.." : "save"}</span><span aria-hidden>→</span></button>
          </div>
        </form>
      ) : list.length < 5 ? (
        <button type="button" onClick={() => setAdding(true)} className={`mt-6 max-w-[280px] ${quiet}`}>add an address</button>
      ) : <p className="mt-6 text-[13px] text-quiet">five is the most: remove one to add another.</p>}
    </div>
  );
}

/* ---------- sign-in ---------- */

/** google sign-in on or off for this profile */
export function GoogleSwitch({ on }: { on: boolean }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  return (
    <button type="button" role="switch" aria-checked={on} aria-label="google sign-in" disabled={busy}
      onClick={async () => { setBusy(true); await post("/api/shop/account", { action: "google", on: !on }).catch(() => {}); router.refresh(); setBusy(false); }}
      className={`relative h-7 w-12 shrink-0 rounded-full transition-colors disabled:opacity-60 ${on ? "bg-ink" : "bg-line"}`}>
      <span className={`absolute top-1 h-5 w-5 rounded-full transition-[left] duration-150 ${on ? "left-6 bg-paper" : "left-1 bg-quiet"}`} />
    </button>
  );
}

/** set, change or remove a password; a sign-in from the last 15 minutes counts in place of the old one */
export function Password({ has, email }: { has: boolean; email: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [pw, setPw] = useState("");
  const [current, setCurrent] = useState("");
  const [busy, setBusy] = useState(false);
  const [bad, setBad] = useState<Bad>(null);
  const [said, setSaid] = useState("");
  async function go(action: "set-password" | "remove-password") {
    setBusy(true);
    setBad(null);
    try {
      await post("/api/shop/account", { action, password: pw, current });
      setSaid(action === "remove-password" ? "password removed. sign in with a code or google." : has ? "changed. every other device was signed out." : "password set.");
      setOpen(false); setPw(""); setCurrent("");
      router.refresh();
    } catch (err) {
      setBad(asBad(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <h2 className={H2}>password</h2>
      {open ? (
        <form className="menu-in max-w-[420px]" onSubmit={(e) => { e.preventDefault(); go("set-password"); }}>
          <input type="email" name="email" autoComplete="username" value={email} readOnly hidden />
          {has ? <Secret label="current password (not needed if you signed in the last 15 minutes)" value={current} onChange={setCurrent} auto="current-password" bad={bad?.field === "current"} /> : null}
          <Secret label={has ? "new password" : "a password"} value={pw} onChange={(v) => { setPw(v); setBad(null); }} auto="new-password" bad={bad?.field === "password"} focus={!has} />
          <p className="mt-1.5 text-[12px] text-quiet">8 characters or more. a few words together is strong and easy to remember.</p>
          {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
          <div className="mt-5 grid grid-cols-2 gap-3">
            <button type="button" onClick={() => { setOpen(false); setBad(null); }} className={quiet}>cancel</button>
            <button disabled={busy || pw.length < 8} className={button}><span>{busy ? "saving.." : "save"}</span><span aria-hidden>→</span></button>
          </div>
          {has ? <button type="button" disabled={busy} onClick={() => go("remove-password")} className="hit mt-4 text-[13px] text-quiet underline decoration-line underline-offset-4 hover:text-ink">remove my password instead</button> : null}
        </form>
      ) : (
        <>
          <p className="mt-3 max-w-[52ch] text-[14px] text-quiet">{has ? "you can sign in with it, or with a code, whichever is handier. changing it signs out every other device." : "no password needed: a code by email always works. set one if you'd rather type it."}</p>
          <button type="button" onClick={() => { setOpen(true); setSaid(""); }} className={`mt-4 max-w-[280px] ${quiet}`}>{has ? "change or remove" : "set a password"}</button>
        </>
      )}
      {said ? <p role="status" className="mt-3 text-[14px]">{said}</p> : null}
    </section>
  );
}

/** every device signed in, this one first; any can be signed out, or all of them */
export function Devices({ list }: { list: { id: string; device: string; how: string; at: string; seen: string; current: boolean }[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  async function end(id: string) {
    setBusy(id);
    const r = await post<{ ok: true; out?: boolean }>("/api/shop/account", { action: "end-device", id }).catch(() => null);
    if (r?.out) router.replace("/profile");
    router.refresh();
    setBusy(null);
  }
  return (
    <section>
      <h2 className={H2}>signed in on · {list.length}</h2>
      <ul className="mt-2 text-[14px]">
        {list.map((d) => (
          <li key={d.id} className="flex items-start justify-between gap-4 border-b border-line py-3">
            <span className="min-w-0">
              <span className="text-ink">{d.device.split(", near")[0]}</span>{d.current ? <span className="text-quiet"> · this device</span> : null}
              <span className="block text-quiet">{d.device.includes(", near") ? `near ${d.device.split(", near ")[1]} · ` : ""}{d.how} · {d.at ? ago(d.at) : ""}{!d.current && d.seen ? `, last here ${ago(d.seen)}` : ""}</span>
            </span>
            <button type="button" disabled={!!busy} onClick={() => end(d.id)} className="hit shrink-0 text-[13px] text-quiet hover:text-ink">{busy === d.id ? "one moment.." : "sign out"}</button>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-[12px] text-quiet">a device stays signed in while you keep coming back; 90 days away signs it out.</p>
    </section>
  );
}

/* ---------- signing out, and leaving ---------- */

export function Leave({ email }: { email: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [sure, setSure] = useState(false);
  const [bad, setBad] = useState("");
  async function go(action: "signout" | "signout-all" | "delete") {
    setBusy(action);
    setBad("");
    try {
      await post("/api/shop/account", { action });
      router.replace("/profile");
      router.refresh();
    } catch (err) {
      setBad((err as Error).message);
      setBusy(null);
    }
  }
  return (
    <section>
      <h2 className={H2}>sign out, or leave</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <button type="button" disabled={!!busy} onClick={() => go("signout")} className={quiet}>{busy === "signout" ? "one moment.." : "sign out"}</button>
        <button type="button" disabled={!!busy} onClick={() => go("signout-all")} className={quiet}>{busy === "signout-all" ? "one moment.." : "sign out everywhere"}</button>
      </div>
      <div className="mt-10">
        {sure ? (
          <div className="menu-in border border-line p-4">
            <p className="text-[15px] font-semibold">delete the profile for {email}?</p>
            <p className="mt-2 text-[14px] text-quiet">your name, mobile, addresses, password, devices and activity go, and you&apos;re signed out everywhere. orders you&apos;ve placed still arrive, and their pages and receipts still open from their emails. it can&apos;t be undone, but you can sign in again with the same email and start fresh.</p>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <button type="button" onClick={() => setSure(false)} className={quiet}>keep it</button>
              <button type="button" disabled={!!busy} onClick={() => go("delete")} className={button}><span>{busy === "delete" ? "deleting.." : "delete"}</span><span aria-hidden>→</span></button>
            </div>
          </div>
        ) : (
          <button type="button" onClick={() => setSure(true)} className="hit text-[13px] text-quiet underline decoration-line underline-offset-4 hover:text-ink">delete my profile</button>
        )}
        {bad && <p role="alert" className="mt-3 text-[14px]">{bad}</p>}
      </div>
    </section>
  );
}
