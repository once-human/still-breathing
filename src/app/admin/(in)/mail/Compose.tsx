"use client";

import { useRouter } from "next/navigation";
import { startTransition, useEffect, useState } from "react";
import { BTN, FIELD, Modal, useAdminPost, useToast } from "../../ui/client";

type Preset = { local: string; name: string; use: string };
export type GroupOpt = { key: string; label: string; hint: string; days: boolean; service: boolean };
type Count = { count: number; sample: string[]; leftOut: number; bad: string[] } | null;
const AREA = `${FIELD} !h-auto min-h-[180px] py-3 leading-relaxed`;
const MINE = "admin-mail-from";

/**
 * Write an email and send it. A letter goes from any name@ on the domain (the shop's boxes, or one of your own, which
 * the form remembers on this device) to up to 50 people; a drop goes from drops@ to everyone on the list. Both can be
 * tried on yourself first, and the real send asks once more.
 */
export function Compose({ kind, domain, presets, listSize, me, groups = [], days: DAYS = [] }: {
  kind: "letter" | "drop"; domain: string; presets: Preset[]; listSize: number; me: string | null; groups?: GroupOpt[]; days?: number[];
}) {
  const post = useAdminPost();
  const say = useToast();
  const router = useRouter();
  const [local, setLocal] = useState("hello");
  const [name, setName] = useState("sahn");
  const [mine, setMine] = useState<{ local: string; name: string } | null>(null);
  const [to, setTo] = useState("");
  const [group, setGroup] = useState("typed");
  const [days, setDays] = useState(30);
  const [count, setCount] = useState<Count>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [link, setLink] = useState("");
  const [signoff, setSignoff] = useState("");
  const [busy, setBusy] = useState<"" | "test" | "send">("");
  const [ask, setAsk] = useState(false);
  const [typed, setTyped] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    try {
      const m = JSON.parse(localStorage.getItem(MINE) ?? "null");
      if (m?.local) setMine(m);
    } catch { /* nothing kept */ }
  }, []);

  const people = [...new Set(to.toLowerCase().split(/[\s,;]+/).filter(Boolean))];
  const g = groups.find((x) => x.key === group);
  // how many it reaches, asked again a moment after the group, window or typed list changes
  useEffect(() => {
    if (kind !== "letter") return;
    let stop = false;
    const t = setTimeout(async () => {
      const r = await post("/api/admin/mail", { action: "count", group, days, to });
      if (!stop) setCount(r.ok ? (r.data as unknown as Count) : null);
    }, group === "typed" ? 500 : 150);
    return () => { stop = true; clearTimeout(t); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, group, days, to]);
  const reach = kind === "drop" ? listSize : count?.count ?? (group === "typed" ? people.length : 0);
  const isPreset = presets.some((p) => p.local === local && p.name === name);
  const pick = (v: string) => {
    if (v === "__mine" && mine) { setLocal(mine.local); setName(mine.name); return; }
    if (v === "__new") { setLocal(""); setName(""); return; }
    const p = presets.find((x) => x.local === v);
    if (p) { setLocal(p.local); setName(p.name); }
  };
  const chosen = isPreset ? local : mine && mine.local === local && mine.name === name ? "__mine" : "__new";

  const send = async (test: boolean) => {
    setErr("");
    setBusy(test ? "test" : "send");
    const r = await post("/api/admin/mail", kind === "drop" ? { action: "drop", subject, body, link, test } : { action: "letter", local, name, group, days, to, subject, body, link, signoff, test });
    setBusy("");
    if (!r.ok) { setErr(r.error); setAsk(false); return; }
    say(true, String(r.data.message ?? "sent"));
    if (kind === "letter" && !isPreset && local) {
      try { localStorage.setItem(MINE, JSON.stringify({ local, name })); } catch { /* fine */ }
      setMine({ local, name });
    }
    if (!test) {
      setAsk(false); setTyped(""); setSubject(""); setBody(""); setLink(""); setTo(""); setGroup("typed");
      startTransition(() => router.refresh());
    }
  };
  const ready = !!subject.trim() && !!body.trim() && (kind === "drop" ? listSize > 0 : !!local && reach > 0);
  const from = kind === "drop" ? `sahn drops <drops@${domain}>` : `${name || "sahn"} <${local || "…"}@${domain}>`;

  return (
    <form className="grid gap-4" onSubmit={(e) => { e.preventDefault(); if (ready) setAsk(true); }}>
      {kind === "letter" ? (
        <>
          <label className="grid gap-1.5 text-[13px] text-quiet">from
            <select value={chosen} onChange={(e) => pick(e.target.value)} className={FIELD}>
              {presets.map((p) => <option key={p.local} value={p.local}>{p.local}@{domain} · {p.use}</option>)}
              {mine && !presets.some((p) => p.local === mine.local) ? <option value="__mine">{mine.local}@{domain} · {mine.name}</option> : null}
              <option value="__new">another address…</option>
            </select>
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="grid gap-1.5 text-[13px] text-quiet">address
              <span className="flex items-center gap-2">
                <input value={local} onChange={(e) => setLocal(e.target.value.toLowerCase().replace(/[^a-z0-9._-]/g, ""))} placeholder="yourname" maxLength={40} className={FIELD} autoComplete="off" spellCheck={false} />
                <span className="shrink-0 text-[15px] text-ink/70">@{domain}</span>
              </span>
            </label>
            <label className="grid gap-1.5 text-[13px] text-quiet">name they see
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="sahn" maxLength={60} className={FIELD} />
            </label>
          </div>
          <div className="grid gap-2">
            <span className="text-[13px] text-quiet">who it goes to</span>
            <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="who it goes to">
              {groups.map((x) => (
                <button key={x.key} type="button" role="radio" aria-checked={group === x.key} onClick={() => setGroup(x.key)}
                  className={`h-9 rounded-full px-4 text-[14px] transition ${group === x.key ? "bg-ink font-semibold text-paper" : "bg-s2 text-ink/80 hover:bg-s3"}`}>{x.label}</button>
              ))}
            </div>
            {g ? <p className="text-[13px] text-quiet">{g.hint}{g.service ? "" : ". anyone who turned emails off is left out, and the email has a one-tap way off at the bottom"}.</p> : null}
            {g?.days ? (
              <div className="flex flex-wrap items-center gap-2 text-[13px] text-quiet">{group === "lapsed" ? "nothing in the last" : "in the last"}
                {DAYS.map((d) => (
                  <button key={d} type="button" onClick={() => setDays(d)} className={`h-8 rounded-full px-3 text-[13px] ${days === d ? "bg-ink/90 font-semibold text-paper" : "bg-s2 text-ink/80 hover:bg-s3"}`}>{d === 365 ? "year" : `${d} days`}</button>
                ))}
              </div>
            ) : null}
          </div>
          <label className="grid gap-1.5 text-[13px] text-quiet">{group === "typed" ? "people" : "and also (optional)"} <span className="text-quiet/80">(emails, by commas or new lines; each gets their own copy)</span>
            <textarea value={to} onChange={(e) => setTo(e.target.value)} rows={2} placeholder="someone@gmail.com" className={`${FIELD} !h-auto py-3`} spellCheck={false} />
          </label>
          <p className="rounded-[10px] bg-s2 px-4 py-3 text-[14px]" aria-live="polite">
            {count === null ? <span className="text-quiet">counting…</span> : <>
              reaches <b className="tnum">{count.count}</b> {count.count === 1 ? "person" : "people"}
              {count.sample.length ? <span className="text-quiet">: {count.sample.join(", ")}{count.count > count.sample.length ? ", …" : ""}</span> : null}
              {count.leftOut ? <span className="block text-[13px] text-quiet">{count.leftOut} left out: they turned emails off</span> : null}
              {count.bad.length ? <span className="block text-[13px] text-bad">not an email: {count.bad.join(", ")}</span> : null}
            </>}
          </p>
        </>
      ) : (
        <p className="text-[15px] text-ink/80">from <span className="text-ink">sahn drops &lt;drops@{domain}&gt;</span> to the <b className="tnum">{listSize}</b> {listSize === 1 ? "person" : "people"} who asked. each email has its own one-tap way off.</p>
      )}
      <label className="grid gap-1.5 text-[13px] text-quiet">subject
        <input value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={150} placeholder={kind === "drop" ? "02 is out" : ""} className={FIELD} />
      </label>
      <label className="grid gap-1.5 text-[13px] text-quiet">email <span className="text-quiet/80">(a blank line starts a new paragraph)</span>
        <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={8} className={AREA} />
      </label>
      <div className={`grid gap-4 ${kind === "letter" ? "sm:grid-cols-2" : ""}`}>
        <label className="grid gap-1.5 text-[13px] text-quiet">link for a button <span className="text-quiet/80">(optional)</span>
          <input value={link} onChange={(e) => setLink(e.target.value)} placeholder={`https://www.${domain}/…`} inputMode="url" className={FIELD} spellCheck={false} />
        </label>
        {kind === "letter" ? (
          <label className="grid gap-1.5 text-[13px] text-quiet">signed <span className="text-quiet/80">(optional, under the email)</span>
            <input value={signoff} onChange={(e) => setSignoff(e.target.value)} placeholder={name || "sahn"} maxLength={200} className={FIELD} />
          </label>
        ) : null}
      </div>
      {err ? <p className="a-pop rounded-[12px] bg-bad/10 px-4 py-3 text-[14px] text-bad">{err}</p> : null}
      <div className="mt-1 flex flex-wrap gap-2">
        <button type="button" disabled={!subject.trim() || !body.trim() || !!busy || !me} onClick={() => void send(true)} className={BTN.plain} title={me ? `to ${me}` : "add ADMIN_EMAIL in vercel"}>
          {busy === "test" ? "sending…" : "send a test to me"}
        </button>
        <button type="submit" disabled={!ready || !!busy} className={BTN.main}>
          {reach > 1 ? `send to ${reach}` : "send"}
        </button>
      </div>

      {ask ? (
        <Modal title={kind === "drop" ? `send to ${listSize}?` : "send it?"} onClose={() => !busy && setAsk(false)}>
          <div className="grid gap-4">
            <p className="text-[15px] leading-relaxed text-ink/80">
              “{subject}” from <span className="text-ink">{from}</span> to {kind === "drop" ? `everyone on the list (${listSize})` : reach === 1 && count?.sample[0] ? count.sample[0] : `${reach} people${g && g.key !== "typed" ? ` (${g.label.toLowerCase()}${g.days ? `, ${days === 365 ? "a year" : `${days} days`}` : ""})` : ""}, each on their own`}. an email can't be taken back.
            </p>
            {kind === "drop" || reach > 50 ? (
              <label className="grid gap-1.5 text-[13px] text-quiet">type <span className="font-mono text-ink">SEND</span> to go ahead
                <input value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" spellCheck={false} className={`${FIELD} font-mono`} />
              </label>
            ) : null}
            <div className="mt-2 grid grid-cols-2 gap-2">
              <button type="button" disabled={!!busy} onClick={() => setAsk(false)} className={BTN.plain}>cancel</button>
              <button type="button" disabled={!!busy || ((kind === "drop" || reach > 50) && typed.trim().toUpperCase() !== "SEND")} onClick={() => void send(false)} className={BTN.main}>{busy ? "sending…" : "send"}</button>
            </div>
          </div>
        </Modal>
      ) : null}
    </form>
  );
}
