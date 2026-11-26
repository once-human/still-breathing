"use client";

import { useActionState } from "react";
import { findOrder, type FindState } from "./actions";

const field = "mt-1 h-12 w-full border border-line bg-transparent px-3 text-[16px] outline-none focus:border-ink";

export function Find() {
  const [state, act, busy] = useActionState<FindState, FormData>(findOrder, { error: null });
  return (
    <form action={act} className="max-w-[420px]">
      <label className="block text-[13px] text-quiet">order number
        <input name="number" required autoComplete="off" autoCapitalize="characters" placeholder="#S261126K7QX" maxLength={13} className={`${field} tnum text-ink`} />
      </label>
      <label className="mt-4 block text-[13px] text-quiet">the email you ordered with
        <input name="email" type="email" required autoComplete="email" maxLength={200} className={`${field} text-ink`} />
      </label>
      {state.error && <p role="alert" className="mt-3 text-[14px]">{state.error}</p>}
      <button disabled={busy} className="mt-5 flex h-12 w-full items-center justify-between bg-ink px-4 text-[15px] font-semibold text-paper hover:bg-ink/90 disabled:opacity-60">
        <span>{busy ? "looking.." : "find my order"}</span><span aria-hidden>→</span>
      </button>
    </form>
  );
}
