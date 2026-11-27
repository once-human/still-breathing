"use client";

import { useState } from "react";
import { BTN, FIELD } from "../ui/client";

export function LoginForm() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "sent" | "error">("idle");
  if (state === "sent")
    return <p className="a-pop rounded-[14px] bg-s1 p-5 text-[15px] leading-snug">if that&apos;s the admin&apos;s address, a link is on its way. it works once, for 10 minutes. open it in this browser or any other.</p>;
  return (
    <form className="grid gap-4" onSubmit={async (e) => {
      e.preventDefault();
      setState("busy");
      const r = await fetch("/api/admin/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) }).catch(() => null);
      setState(r?.ok ? "sent" : "error");
    }}>
      <label className="grid gap-1.5 text-[13px] text-quiet">email
        <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)}
          className={FIELD} />
      </label>
      <button disabled={state === "busy"} className={`${BTN.main} h-12 w-full`}>{state === "busy" ? "sending…" : "email me a link"}</button>
      {state === "error" ? <p className="text-[13px] text-bad">that didn&apos;t go through. try again in a minute.</p> : null}
    </form>
  );
}
