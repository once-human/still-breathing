"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { BTN, FIELD } from "../ui/client";
import { Icon } from "../ui/icons";

/** one field: the site key. A hidden name beside it lets a password manager save and fill it. */
export function LoginForm() {
  const router = useRouter();
  const [key, setKey] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [bad, setBad] = useState("");
  return (
    <form className="grid gap-4" onSubmit={async (e) => {
      e.preventDefault();
      setBusy(true);
      setBad("");
      const r = await fetch("/api/admin/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key }) }).catch(() => null);
      if (r?.ok) {
        router.replace("/admin");
        router.refresh();
        return;
      }
      setBad(((await r?.json().catch(() => null)) as { error?: string } | null)?.error ?? "that didn't go through: try again");
      setBusy(false);
    }}>
      <input type="text" name="username" autoComplete="username" value="sahn admin" readOnly hidden />
      <label className="grid gap-1.5 text-[13px] text-quiet">key
        <span className="relative block">
          <input type={show ? "text" : "password"} name="password" required autoFocus autoComplete="current-password" spellCheck={false} autoCapitalize="off"
            value={key} onChange={(e) => { setKey(e.target.value); setBad(""); }} aria-invalid={!!bad} className={`${FIELD} !pr-12 font-mono`} />
          <button type="button" onClick={() => setShow(!show)} aria-label={show ? "hide the key" : "show the key"}
            className="absolute right-1.5 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-full text-quiet hover:bg-s3 hover:text-ink">
            <Icon name={show ? "eyeOff" : "eye"} className="h-[18px] w-[18px]" />
          </button>
        </span>
      </label>
      <button disabled={busy || !key} className={`${BTN.main} h-12 w-full`}>{busy ? "opening…" : "open the admin"}</button>
      {bad ? <p role="alert" className="a-pop text-[13px] text-bad">{bad}</p> : null}
    </form>
  );
}
