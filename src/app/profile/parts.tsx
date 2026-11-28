"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { AddressFields, EMPTY, addressLine, input, post } from "@/components/shop/AddressFields";
import type { Address } from "@/lib/shop/account";
import type { Details } from "@/lib/shop/india";

const button = "flex h-12 w-full items-center justify-between bg-ink px-4 text-[15px] font-semibold text-paper hover:bg-ink/90 disabled:opacity-60";
const quietButton = "flex h-12 w-full items-center justify-center border border-line px-4 text-[15px] text-ink hover:border-ink disabled:opacity-60";
type Bad = { field?: string; error: string } | null;
const asBad = (e: unknown): Bad => ({ field: (e as { field?: string }).field, error: (e as Error).message });
const RESEND_S = 30;

/* ---------- sign in (and make an account, the same way) ---------- */

/**
 * email → the 6-digit code in six boxes (typed, pasted or filled from the message by the phone; it goes as soon as
 * the sixth digit is in) → signed in. A new account is asked its name and mobile once, which it can skip.
 */
export function SignIn({ next }: { next: string | null }) {
  const router = useRouter();
  const [step, setStep] = useState<"email" | "code" | "hello">("email");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [bad, setBad] = useState<Bad>(null);
  const [wait, setWait] = useState(0);

  useEffect(() => {
    if (wait <= 0) return;
    const t = setTimeout(() => setWait(wait - 1), 1000);
    return () => clearTimeout(t);
  }, [wait]);

  const done = () => {
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
      const r = await post<{ ok: true; fresh?: boolean }>("/api/shop/account", { action: "verify", email, code });
      if (r.fresh) setStep("hello");
      else done();
    } catch (err) {
      setBad(asBad(err));
    } finally {
      setBusy(false);
    }
  }

  if (step === "hello") return <Hello onDone={done} />;

  if (step === "code")
    return (
      <div className="menu-in max-w-[420px]">
        <p className="border-t border-line pt-1.5 text-[13px] text-quiet">step 2 of 2</p>
        <p className="mt-4 text-[22px] leading-tight font-semibold tracking-[-0.02em]">check your email.</p>
        <p className="mt-2 text-[15px] text-ink/85">we sent a 6-digit code to <span className="text-ink">{email}</span>. it works for 10 minutes.</p>
        <Code key={email} busy={busy} bad={!!bad} onCode={verify} />
        {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
        <div className="mt-5 flex flex-wrap gap-x-5 gap-y-1 text-[13px] text-quiet">
          <button type="button" disabled={wait > 0 || busy} onClick={() => send()} className="hit hover:text-ink disabled:hover:text-quiet">
            {wait > 0 ? <>send a new code in <span className="tnum">{wait}</span>s</> : "send a new code"}
          </button>
          <button type="button" onClick={() => { setStep("email"); setBad(null); }} className="hit hover:text-ink">use another email</button>
        </div>
        <p className="mt-4 text-[12px] text-quiet">not there? look in spam or promotions; it comes from sahn.</p>
      </div>
    );

  return (
    <form onSubmit={send} className="max-w-[420px]">
      <p className="border-t border-line pt-1.5 text-[13px] text-quiet">step 1 of 2</p>
      <label className="mt-4 block text-[13px] text-quiet">your email
        <input value={email} onChange={(e) => { setEmail(e.target.value); setBad(null); }} type="email" inputMode="email" autoComplete="email" required maxLength={120} autoFocus
          className={input} aria-invalid={bad?.field === "email"} />
      </label>
      {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
      <button disabled={busy} className={`mt-5 ${button}`}>
        <span>{busy ? "sending.." : "continue"}</span><span aria-hidden>→</span>
      </button>
      <p className="mt-3 text-[12px] leading-snug text-quiet">new here? this makes your account. we only email you about your orders.</p>
    </form>
  );
}

/** six boxes for the code: each digit moves you on, backspace moves you back, a paste or the phone's autofill fills them all */
function Code({ busy, bad, onCode }: { busy: boolean; bad: boolean; onCode: (code: string) => void }) {
  const [d, setD] = useState<string[]>(Array(6).fill(""));
  const boxes = useRef<(HTMLInputElement | null)[]>([]);
  const sent = useRef("");

  useEffect(() => { boxes.current[0]?.focus(); }, []);
  // a wrong code clears the boxes for another go
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

/** a new account's one question: what to call you, and a mobile for the courier (both can wait) */
function Hello({ onDone }: { onDone: () => void }) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [bad, setBad] = useState<Bad>(null);
  return (
    <form className="menu-in max-w-[420px]" onSubmit={async (e) => {
      e.preventDefault();
      setBusy(true);
      setBad(null);
      try {
        await post("/api/shop/account", { action: "profile", name, phone });
        onDone();
      } catch (err) {
        setBad(asBad(err));
        setBusy(false);
      }
    }}>
      <p className="border-t border-line pt-1.5 text-[13px] text-quiet">you&apos;re in</p>
      <p className="mt-4 text-[22px] leading-tight font-semibold tracking-[-0.02em]">welcome to sahn.</p>
      <p className="mt-2 text-[15px] text-ink/85">two things so checkout fills itself in. you can change them any time.</p>
      <label className="mt-6 block text-[13px] text-quiet">your name
        <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" maxLength={80} autoFocus className={input} aria-invalid={bad?.field === "name"} />
      </label>
      <label className="mt-4 block text-[13px] text-quiet">mobile, for the courier
        <span className="relative block">
          <span className="pointer-events-none absolute left-3 top-1/2 mt-0.5 -translate-y-1/2 text-[16px] text-quiet">+91</span>
          <input value={phone} onChange={(e) => setPhone(e.target.value)} type="tel" inputMode="tel" autoComplete="tel-national" maxLength={14} className={`${input} !pl-12`} aria-invalid={bad?.field === "phone"} />
        </span>
      </label>
      {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
      <button disabled={busy} className={`mt-6 ${button}`}><span>{busy ? "saving.." : "done"}</span><span aria-hidden>→</span></button>
      <button type="button" onClick={onDone} className="hit mt-3 block text-[13px] text-quiet hover:text-ink">skip for now</button>
    </form>
  );
}

/* ---------- the signed-in account: tabs ---------- */

const TABS = ["orders", "addresses", "details"] as const;
type Tab = (typeof TABS)[number];

/** orders, addresses, details: one shown at a time, kept in the address (#addresses) so back and a reload land on it */
export function AccountTabs({ orders, addresses, details, counts }: { orders: React.ReactNode; addresses: React.ReactNode; details: React.ReactNode; counts: { orders: number; addresses: number } }) {
  const [tab, setTab] = useState<Tab>("orders");
  useEffect(() => {
    const read = () => {
      const h = window.location.hash.slice(1) as Tab;
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
  const panes = { orders, addresses, details };
  return (
    <div>
      <div role="tablist" aria-label="your account" className="mb-8 flex gap-6 border-b border-line">
        {TABS.map((t) => (
          <button key={t} role="tab" type="button" aria-selected={tab === t} aria-controls={`pane-${t}`} id={`tab-${t}`} onClick={() => pick(t)}
            className={`relative -mb-px flex h-12 items-center gap-1.5 border-b-2 text-[15px] transition-colors ${tab === t ? "border-ink text-ink" : "border-transparent text-quiet hover:text-ink"}`}>
            {t}{t !== "details" ? <span className="tnum text-[12px] text-quiet">{counts[t]}</span> : null}
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
  return (
    <form onSubmit={save}>
      <h2 className="border-t border-line pt-1.5 text-[13px] text-quiet">you</h2>
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
        <p className="mt-1.5 text-[12px]">your email is your account: every order placed with it shows here.</p>
      </div>
      {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
      <button disabled={busy || (!changed && state !== "saved")} className={`mt-5 ${button}`}>
        <span>{busy ? "saving.." : state === "saved" && !changed ? "saved" : "save"}</span><span aria-hidden>{state === "saved" && !changed ? "✓" : "→"}</span>
      </button>
    </form>
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
          <h2 className="mb-4 border-t border-line pt-1.5 text-[13px] text-quiet">a new address</h2>
          <AddressFields d={d} onChange={setD} bad={bad?.field as keyof Details | undefined} email={false} />
          {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
          <div className="mt-5 grid grid-cols-2 gap-3">
            <button type="button" onClick={() => { setAdding(false); setBad(null); }} className={quietButton}>cancel</button>
            <button disabled={!!busy} className={button}><span>{busy ? "saving.." : "save"}</span><span aria-hidden>→</span></button>
          </div>
        </form>
      ) : list.length < 5 ? (
        <button type="button" onClick={() => setAdding(true)} className={`mt-6 max-w-[280px] ${quietButton}`}>add an address</button>
      ) : <p className="mt-6 text-[13px] text-quiet">five is the most: remove one to add another.</p>}
    </div>
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
      router.replace("/account");
      router.refresh();
    } catch (err) {
      setBad((err as Error).message);
      setBusy(null);
    }
  }
  return (
    <div>
      <h2 className="border-t border-line pt-1.5 text-[13px] text-quiet">signing out</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <button type="button" disabled={!!busy} onClick={() => go("signout")} className={quietButton}>{busy === "signout" ? "one moment.." : "sign out"}</button>
        <button type="button" disabled={!!busy} onClick={() => go("signout-all")} className={quietButton}>{busy === "signout-all" ? "one moment.." : "sign out everywhere"}</button>
      </div>
      <p className="mt-2 text-[12px] text-quiet">this device stays signed in while you keep coming back; 90 days away signs it out.</p>

      <div className="mt-12">
        {sure ? (
          <div className="menu-in border border-line p-4">
            <p className="text-[15px] font-semibold">delete the account for {email}?</p>
            <p className="mt-2 text-[14px] text-quiet">your name, mobile and saved addresses go, and you&apos;re signed out everywhere. orders you&apos;ve placed still arrive, and their pages and receipts still open from their emails. it can&apos;t be undone, but you can always sign in again with the same email and start fresh.</p>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <button type="button" onClick={() => setSure(false)} className={quietButton}>keep it</button>
              <button type="button" disabled={!!busy} onClick={() => go("delete")} className={button}><span>{busy === "delete" ? "deleting.." : "delete"}</span><span aria-hidden>→</span></button>
            </div>
          </div>
        ) : (
          <button type="button" onClick={() => setSure(true)} className="hit text-[13px] text-quiet underline decoration-line underline-offset-4 hover:text-ink">delete my account</button>
        )}
        {bad && <p role="alert" className="mt-3 text-[14px]">{bad}</p>}
      </div>
    </div>
  );
}
