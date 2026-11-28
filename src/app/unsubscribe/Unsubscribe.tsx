"use client";

import Link from "next/link";
import { useState } from "react";

export function Unsubscribe({ e, t }: { e: string; t: string }) {
  const [state, setState] = useState<"ask" | "off" | "on" | "bad">("ask");
  const [busy, setBusy] = useState(false);
  const go = async (on: boolean) => {
    setBusy(true);
    const r = await fetch(`/api/shop/drops?e=${encodeURIComponent(e)}&t=${encodeURIComponent(t)}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ on }) }).catch(() => null);
    setState(r?.ok ? (on ? "on" : "off") : "bad");
    setBusy(false);
  };
  const button = "flex h-12 w-full items-center justify-between bg-ink px-4 text-[15px] font-semibold text-paper hover:bg-ink/90 disabled:opacity-60";
  if (state === "bad") return <p className="text-[15px]">that link isn&apos;t right. use the one at the bottom of your latest email, or turn it off in your <Link href="/profile#details" className="draw">profile</Link>.</p>;
  if (state === "off")
    return (
      <div className="menu-in">
        <p className="text-[22px] leading-tight font-semibold tracking-[-0.02em]">done. no more drop emails.</p>
        <p className="mt-2 text-[15px] text-quiet">{e} still gets emails about its own orders.</p>
        <button type="button" disabled={busy} onClick={() => go(true)} className="hit mt-4 text-[13px] text-quiet underline decoration-line underline-offset-4 hover:text-ink">that was a mistake, keep me on</button>
      </div>
    );
  if (state === "on") return <p className="menu-in text-[22px] leading-tight font-semibold tracking-[-0.02em]">you&apos;re back on. one email per drop.</p>;
  return (
    <div>
      <p className="border-t border-line pt-1.5 text-[13px] text-quiet">new drop emails</p>
      <p className="mt-4 text-[15px] text-ink/85">stop emails about new drops to <span className="text-ink">{e || "this address"}</span>? emails about your orders still come.</p>
      <button type="button" disabled={busy || !e || !t} onClick={() => go(false)} className={`mt-6 ${button}`}><span>{busy ? "one moment.." : "stop them"}</span><span aria-hidden>→</span></button>
    </div>
  );
}
