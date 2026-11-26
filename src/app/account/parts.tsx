"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AddressFields, EMPTY, addressLine, input, post } from "@/components/shop/AddressFields";
import type { Address } from "@/lib/shop/account";
import type { Details } from "@/lib/shop/india";

const button = "flex h-12 w-full items-center justify-between bg-ink px-4 text-[15px] font-semibold text-paper hover:bg-ink/90 disabled:opacity-60";
type Bad = { field?: string; error: string } | null;
const asBad = (e: unknown): Bad => ({ field: (e as { field?: string }).field, error: (e as Error).message });

/** email → 6-digit code → signed in */
export function SignIn({ next }: { next: string | null }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [bad, setBad] = useState<Bad>(null);

  async function go(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setBad(null);
    try {
      if (!sent) {
        await post("/api/shop/account", { action: "code", email });
        setSent(true);
      } else {
        await post("/api/shop/account", { action: "verify", email, code });
        if (next) router.push(next);
        router.refresh();
      }
    } catch (err) {
      setBad(asBad(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={go} className="max-w-[420px]">
      <label className="block text-[13px] text-quiet">your email
        <input value={email} onChange={(e) => { setEmail(e.target.value); setSent(false); setCode(""); }} type="email" inputMode="email" autoComplete="email" required maxLength={120} className={input} aria-invalid={bad?.field === "email"} />
      </label>
      {sent && (
        <label className="mt-4 block text-[13px] text-quiet">the 6-digit code we just emailed to {email}
          <input value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" autoComplete="one-time-code" required autoFocus
            className={`${input} tnum tracking-[0.3em]`} aria-invalid={bad?.field === "code"} />
        </label>
      )}
      {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
      <button disabled={busy || (sent && code.length !== 6)} className={`mt-5 ${button}`}>
        <span>{busy ? "one moment.." : sent ? "sign in" : "email me a code"}</span><span aria-hidden>→</span>
      </button>
      {sent && <p className="mt-2 text-[12px] text-quiet">it works for 10 minutes. not there? check spam, or <button type="button" className="draw hover:text-ink" onClick={() => { setSent(false); setCode(""); }}>send another</button>.</p>}
    </form>
  );
}

export function Profile({ name: n0, phone: p0 }: { name: string; phone: string }) {
  const router = useRouter();
  const [name, setName] = useState(n0);
  const [phone, setPhone] = useState(p0);
  const [state, setState] = useState<Bad | "saved">(null);
  const [busy, setBusy] = useState(false);
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
      <label className="mt-3 block text-[13px] text-quiet">name
        <input value={name} onChange={(e) => { setName(e.target.value); setState(null); }} autoComplete="name" maxLength={80} className={input} aria-invalid={bad?.field === "name"} />
      </label>
      <label className="mt-3 block text-[13px] text-quiet">mobile
        <input value={phone} onChange={(e) => { setPhone(e.target.value); setState(null); }} type="tel" inputMode="tel" autoComplete="tel-national" maxLength={20} className={input} aria-invalid={bad?.field === "phone"} />
      </label>
      {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
      <button disabled={busy} className="hit mt-3 text-[14px] font-semibold hover:text-ink/80">{busy ? "saving.." : state === "saved" ? "saved ✓" : "save"}</button>
    </form>
  );
}

export function Addresses({ list }: { list: Address[] }) {
  const router = useRouter();
  const [adding, setAdding] = useState(false);
  const [d, setD] = useState<Details>(EMPTY);
  const [bad, setBad] = useState<Bad>(null);
  const [busy, setBusy] = useState(false);
  async function act(body: object) {
    setBusy(true);
    setBad(null);
    try {
      await post("/api/shop/account", body);
      setAdding(false);
      setD(EMPTY);
      router.refresh();
    } catch (err) {
      setBad(asBad(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div>
      <h2 className="border-t border-line pt-1.5 text-[13px] text-quiet">addresses · {list.length} of 5</h2>
      {list.length === 0 && !adding && <p className="mt-3 text-[14px] text-quiet">the places you send shirts to are kept here, so checkout fills itself in.</p>}
      <ul className="mt-2 text-[14px]">
        {list.map((a) => (
          <li key={a.id} className="flex items-start justify-between gap-3 border-b border-line py-2">
            <span><span className="text-ink">{a.name}</span><span className="text-quiet"> · {addressLine(a)} · {a.phone}</span></span>
            <button type="button" disabled={busy} onClick={() => act({ action: "remove-address", id: a.id })} className="hit shrink-0 text-[13px] text-quiet hover:text-ink" aria-label={`Remove the address ${addressLine(a)}`}>remove</button>
          </li>
        ))}
      </ul>
      {adding ? (
        <form onSubmit={(e) => { e.preventDefault(); act({ action: "add-address", details: d }); }} className="mt-4">
          <AddressFields d={d} onChange={setD} bad={bad?.field as keyof Details | undefined} email={false} />
          {bad && <p role="alert" className="mt-3 text-[14px]">{bad.error}</p>}
          <div className="mt-4 flex gap-4 text-[14px]">
            <button disabled={busy} className="hit font-semibold">{busy ? "saving.." : "save address"}</button>
            <button type="button" onClick={() => { setAdding(false); setBad(null); }} className="hit text-quiet hover:text-ink">cancel</button>
          </div>
        </form>
      ) : list.length < 5 ? (
        <button type="button" onClick={() => setAdding(true)} className="hit mt-3 text-[14px] font-semibold">add an address</button>
      ) : null}
    </div>
  );
}

export function SignOut() {
  const router = useRouter();
  return <button type="button" className="hit hover:text-ink" onClick={async () => { await post("/api/shop/account", { action: "signout" }).catch(() => {}); router.refresh(); }}>sign out</button>;
}
