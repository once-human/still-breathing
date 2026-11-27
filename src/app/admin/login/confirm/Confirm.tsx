"use client";

import { useEffect, useState } from "react";
import { BTN } from "../../ui/client";

export function Confirm() {
  const [token, setToken] = useState<string | null>(null);
  const [state, setState] = useState<"idle" | "busy" | "error">("idle");
  const [err, setErr] = useState("");
  useEffect(() => {
    const t = window.location.hash.slice(1);
    setToken(/^[\w-]{40,50}$/.test(t) ? t : "");
    history.replaceState(null, "", window.location.pathname); // the token leaves the address bar and history
  }, []);
  if (token === null) return null;
  if (!token) return <p className="rounded-[14px] bg-s1 p-5 text-[15px]">this link is incomplete. <a className="underline decoration-ink/25 underline-offset-4" href="/admin/login">ask for a new one</a>.</p>;
  return (
    <div className="grid gap-4">
      <p className="rounded-[14px] bg-s1 p-5 text-[15px] leading-snug">sign this browser in to the sahn admin? the session lasts 12 hours, or 2 hours without use.</p>
      <button disabled={state === "busy"} className={`${BTN.main} h-12 w-full`} onClick={async () => {
        setState("busy");
        const r = await fetch("/api/admin/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) }).catch(() => null);
        if (r?.ok) { window.location.href = "/admin"; return; }
        const j = (await r?.json().catch(() => ({}))) as { error?: string } | undefined;
        setErr(j?.error ?? "that didn't go through");
        setState("error");
      }}>{state === "busy" ? "signing in…" : "sign in"}</button>
      {state === "error" ? <p className="text-[13px] text-bad">{err}. <a className="underline underline-offset-4" href="/admin/login">ask for a new link</a>.</p> : null}
    </div>
  );
}
