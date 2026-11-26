"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useState } from "react";

/** The admin's few moving parts: the CSRF token every write sends, the nav, and actions with a confirm step. */
const Csrf = createContext("");
export const CsrfProvider = ({ token, children }: { token: string; children: React.ReactNode }) => <Csrf.Provider value={token}>{children}</Csrf.Provider>;

export function useAdminPost() {
  const csrf = useContext(Csrf);
  return async (url: string, body: unknown): Promise<{ ok: true; data: Record<string, unknown> } | { ok: false; error: string }> => {
    const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "x-csrf": csrf }, body: JSON.stringify(body), credentials: "same-origin" }).catch(() => null);
    if (!res) return { ok: false, error: "no answer: check the connection" };
    const j = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    if (res.status === 401) window.location.href = "/admin/login";
    return res.ok ? { ok: true, data: j } : { ok: false, error: String(j.error ?? `failed (${res.status})`) };
  };
}

const NAV = [
  ["/admin", "overview"],
  ["/admin/orders", "orders"],
  ["/admin/customers", "customers"],
  ["/admin/products", "products"],
  ["/admin/activity", "activity"],
  ["/admin/settings", "settings"],
  ["/admin/audit", "audit log"],
] as const;

export function Nav({ email }: { email: string }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const on = (href: string) => (href === "/admin" ? path === "/admin" : path === href || path.startsWith(href + "/"));
  const links = NAV.map(([href, label]) => (
    <Link key={href} href={href} onClick={() => setOpen(false)}
      className={`block border-l-2 py-1.5 pl-3 text-[14px] transition ${on(href) ? "border-blue text-ink" : "border-transparent text-quiet hover:text-ink"}`}>
      {label}
    </Link>
  ));
  return (
    <>
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-paper/95 px-4 py-3 backdrop-blur md:hidden">
        <Link href="/admin" className="text-[18px] font-extrabold tracking-[-0.04em]">sahn <span className="font-normal text-quiet">admin</span></Link>
        <button type="button" onClick={() => setOpen((v) => !v)} className="hit text-[14px]" aria-expanded={open}>{open ? "close" : "menu"}</button>
      </div>
      {open ? <nav className="border-b border-line px-4 py-3 md:hidden">{links}<div className="mt-3"><SignOut /></div></nav> : null}
      <aside className="sticky top-0 hidden h-dvh w-56 shrink-0 flex-col border-r border-line px-5 py-6 md:flex">
        <Link href="/admin" className="text-[22px] font-extrabold tracking-[-0.04em]">sahn <span className="font-normal text-quiet">admin</span></Link>
        <nav className="mt-8 grid gap-0.5">{links}</nav>
        <div className="mt-auto grid gap-2 text-[12px] text-quiet">
          <span className="truncate" title={email}>{email}</span>
          <Link href="/" className="hover:text-ink">the site ↗</Link>
          <SignOut />
        </div>
      </aside>
    </>
  );
}

function SignOut() {
  const post = useAdminPost();
  return (
    <button type="button" className="text-left text-[12px] text-quiet hover:text-ink" onClick={async () => {
      await post("/api/admin/session", { signOut: true });
      window.location.href = "/admin/login";
    }}>sign out</button>
  );
}

export function SignOutAll() {
  return <Act label="sign out everywhere" confirm="every admin session, on every device, ends now (this one too)." url="/api/admin/session" body={{ signOut: true, all: true }} done={() => (window.location.href = "/admin/login")} />;
}

const btn = "inline-flex h-9 items-center gap-2 px-3 text-[13px] ring-1 transition disabled:opacity-40";
export const BTN = { plain: `${btn} ring-line hover:ring-ink`, main: `${btn} bg-ink font-semibold text-paper ring-ink hover:bg-ink/90`, danger: `${btn} text-[#f08a7a] ring-[#f08a7a]/60 hover:ring-[#f08a7a]` };

/**
 * One admin action: the button, then a confirm with what will happen (and for the ones that move money, the order
 * number typed in), then the answer. Nothing happens on the first press.
 */
type Field = { name: string; label: string; type?: "text" | "number"; placeholder?: string; initial?: string; optional?: boolean; options?: string[] };

export function Act({ label, confirm, url, body, danger, typeToConfirm, done, fields = [] }: {
  label: string; confirm: string; url: string; body: Record<string, unknown>; danger?: boolean; typeToConfirm?: string;
  done?: (data: Record<string, unknown>) => void; fields?: Field[];
}) {
  const post = useAdminPost();
  const router = useRouter();
  const [step, setStep] = useState<"idle" | "confirm" | "busy">("idle");
  const [typed, setTyped] = useState("");
  const [values, setValues] = useState<Record<string, string>>(Object.fromEntries(fields.map((f) => [f.name, f.initial ?? ""])));
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const go = async () => {
    setStep("busy");
    const r = await post(url, { ...body, ...Object.fromEntries(fields.map((f) => [f.name, f.type === "number" ? Number(values[f.name]) : values[f.name]])) });
    setStep("idle");
    setTyped("");
    setMsg(r.ok ? { ok: true, text: String(r.data.message ?? "done") } : { ok: false, text: r.error });
    if (r.ok) {
      done?.(r.data);
      router.refresh();
    }
  };
  const blocked = (typeToConfirm && typed.trim().toUpperCase() !== typeToConfirm.toUpperCase()) || fields.some((f) => !f.optional && !values[f.name]?.trim());
  return (
    <div className="grid gap-2">
      {step === "idle" ? (
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" className={danger ? BTN.danger : BTN.plain} onClick={() => { setMsg(null); setStep("confirm"); }}>{label}</button>
          {msg ? <span className={`text-[12px] ${msg.ok ? "text-[#8fd19e]" : "text-[#f08a7a]"}`}>{msg.text}</span> : null}
        </div>
      ) : (
        <div className={`grid max-w-md gap-3 p-3 ring-1 ${danger ? "ring-[#f08a7a]/60" : "ring-line"}`}>
          <p className="text-[13px]">{confirm}</p>
          {fields.map((f) => (
            <label key={f.name} className="grid gap-1 text-[12px] text-quiet">{f.label}
              {f.options ? (
                <select value={values[f.name]} onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}
                  className="h-9 bg-paper px-2 text-[14px] text-ink ring-1 ring-line focus:ring-ink focus:outline-none">
                  {f.options.map((o) => <option key={o}>{o}</option>)}
                </select>
              ) : (
                <input type={f.type ?? "text"} value={values[f.name]} onChange={(e) => setValues({ ...values, [f.name]: e.target.value })} placeholder={f.placeholder}
                  className="h-9 bg-transparent px-2 text-[14px] text-ink ring-1 ring-line focus:ring-ink focus:outline-none" />
              )}
            </label>
          ))}
          {typeToConfirm ? (
            <label className="grid gap-1 text-[12px] text-quiet">type {typeToConfirm} to go ahead
              <input value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" spellCheck={false}
                className="h-9 bg-transparent px-2 font-mono text-[14px] text-ink ring-1 ring-line focus:ring-ink focus:outline-none" />
            </label>
          ) : null}
          <div className="flex gap-2">
            <button type="button" disabled={!!blocked || step === "busy"} onClick={go} className={danger ? BTN.danger : BTN.main}>{step === "busy" ? "working…" : `yes, ${label}`}</button>
            <button type="button" disabled={step === "busy"} onClick={() => setStep("idle")} className={BTN.plain}>no</button>
          </div>
        </div>
      )}
    </div>
  );
}

/** a short text note on an order or customer, saved with who wrote it */
export function NoteForm({ url, body }: { url: string; body: Record<string, unknown> }) {
  const post = useAdminPost();
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  return (
    <form className="grid gap-2" onSubmit={async (e) => {
      e.preventDefault();
      if (!text.trim()) return;
      setBusy(true);
      const r = await post(url, { ...body, text });
      setBusy(false);
      if (r.ok) { setText(""); setErr(""); router.refresh(); } else setErr(r.error);
    }}>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2} maxLength={2000} placeholder="a note for yourself (the buyer never sees it)"
        className="w-full resize-y bg-transparent p-2 text-[13px] ring-1 ring-line focus:ring-ink focus:outline-none" />
      <div className="flex items-center gap-3">
        <button disabled={busy || !text.trim()} className={BTN.plain}>{busy ? "saving…" : "add note"}</button>
        {err ? <span className="text-[12px] text-[#f08a7a]">{err}</span> : null}
      </div>
    </form>
  );
}
