"use client";

import { useState } from "react";

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "sent" | "error">("idle");
  if (state === "sent")
    return <p className="text-[14px]">if that&apos;s the admin&apos;s address, a link is on its way. it works once, for 10 minutes. open it in this browser or any other.</p>;
  return (
    <form className="grid gap-3" onSubmit={async (e) => {
      e.preventDefault();
      setState("busy");
      const r = await fetch("/api/admin/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) }).catch(() => null);
      setState(r?.ok ? "sent" : "error");
    }}>
      <label className="grid gap-1 text-[12px] text-quiet">email
        <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)}
          className="h-11 bg-transparent px-3 text-[15px] text-ink ring-1 ring-line focus:ring-ink focus:outline-none" />
      </label>
      <button disabled={state === "busy"} className="h-11 bg-ink text-[15px] font-semibold text-paper disabled:opacity-50">{state === "busy" ? "sending…" : "email me a link"}</button>
      {state === "error" ? <p className="text-[12px] text-[#f08a7a]">that didn&apos;t go through. try again in a minute.</p> : null}
    </form>
  );
}
