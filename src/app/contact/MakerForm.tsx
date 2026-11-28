"use client";

import { useState } from "react";
import { input, post } from "@/components/shop/AddressFields";

type Bad = { field?: string; error: string };

/** the note to the maker: name, email, the order if there is one, and what's happened */
export function MakerForm({ name: n0, email: e0 }: { name: string; email: string }) {
  const [name, setName] = useState(n0);
  const [email, setEmail] = useState(e0);
  const [order, setOrder] = useState("");
  const [body, setBody] = useState("");
  const [trap, setTrap] = useState("");
  const [busy, setBusy] = useState(false);
  const [bad, setBad] = useState<Bad | null>(null);
  const [sent, setSent] = useState(false);

  if (sent)
    return (
      <div role="status" className="border-t border-ink pt-4 text-[15px] leading-relaxed">
        <p className="font-semibold">it&apos;s with the maker.</p>
        <p className="mt-1 text-quiet">they read it themselves and write back to {email}. if you think of something else, reply to that email.</p>
      </div>
    );

  const go = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setBad(null);
    try {
      await post("/api/shop/maker", { name, email, order, body, website: trap });
      setSent(true);
    } catch (x) {
      setBad({ field: (x as { field?: string }).field, error: (x as Error).message });
    }
    setBusy(false);
  };
  const label = "block text-[13px] text-quiet";
  return (
    <form onSubmit={go} noValidate className="grid grid-cols-2 gap-x-3 gap-y-4">
      <label className={label}>your name
        <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" maxLength={80} className={input} aria-invalid={bad?.field === "name"} />
      </label>
      <label className={label}>your email
        <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" autoComplete="email" inputMode="email" maxLength={120} spellCheck={false} autoCapitalize="off" className={input} aria-invalid={bad?.field === "email"} />
      </label>
      <label className={`${label} col-span-2`}>order number <span className="text-quiet/80">(if it&apos;s about one)</span>
        <input value={order} onChange={(e) => setOrder(e.target.value.toUpperCase())} maxLength={14} placeholder="S261128…" spellCheck={false} autoCapitalize="characters" className={`${input} font-mono`} aria-invalid={bad?.field === "order"} />
      </label>
      <label className={`${label} col-span-2`}>what&apos;s happened
        <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={6} maxLength={5000} className={`${input} !h-auto py-3 leading-relaxed`} aria-invalid={bad?.field === "body"} />
      </label>
      <label aria-hidden className="absolute -left-[9999px] h-px w-px overflow-hidden">website
        <input tabIndex={-1} autoComplete="off" value={trap} onChange={(e) => setTrap(e.target.value)} />
      </label>
      {bad ? <p role="alert" className="col-span-2 text-[14px]">{bad.error}</p> : null}
      <button disabled={busy} className="col-span-2 flex h-12 w-full items-center justify-between bg-ink px-4 text-[15px] font-semibold text-paper hover:bg-ink/90 disabled:opacity-60">
        <span>{busy ? "one moment.." : "send it to the maker"}</span><span aria-hidden>→</span>
      </button>
    </form>
  );
}
