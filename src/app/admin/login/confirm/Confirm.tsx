"use client";

import { useEffect, useState } from "react";

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
  if (!token) return <p className="text-[14px]">this link is incomplete. <a className="underline" href="/admin/login">ask for a new one</a>.</p>;
  return (
    <div className="grid gap-3">
      <p className="text-[14px]">sign this browser in to the sahn admin? the session lasts 12 hours, or 2 hours without use.</p>
      <button disabled={state === "busy"} className="h-11 bg-ink text-[15px] font-semibold text-paper disabled:opacity-50" onClick={async () => {
        setState("busy");
        const r = await fetch("/api/admin/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token }) }).catch(() => null);
        if (r?.ok) { window.location.href = "/admin"; return; }
        const j = (await r?.json().catch(() => ({}))) as { error?: string } | undefined;
        setErr(j?.error ?? "that didn't go through");
        setState("error");
      }}>{state === "busy" ? "signing in…" : "sign in"}</button>
      {state === "error" ? <p className="text-[12px] text-[#f08a7a]">{err}. <a className="underline" href="/admin/login">ask for a new link</a>.</p> : null}
    </div>
  );
}
