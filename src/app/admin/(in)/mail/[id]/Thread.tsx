"use client";

import { useRouter } from "next/navigation";
import { startTransition, useState } from "react";
import { BTN, FIELD, Picker, useAdminPost, useToast } from "../../../ui/client";

/** one email: its words, or the email as it was sent (in a sandbox: no scripts, no forms) */
export function Body({ text, html }: { text: string; html: string | null }) {
  const [asSent, setAsSent] = useState(false);
  return (
    <div>
      {asSent && html ? (
        <iframe sandbox="" srcDoc={html} title="the email as sent" className="h-[70vh] w-full rounded-[10px] bg-white" referrerPolicy="no-referrer" />
      ) : (
        <div className="whitespace-pre-wrap break-words text-[15px] leading-relaxed">{text || <span className="text-quiet">(no words, only the email as sent)</span>}</div>
      )}
      {html ? <button type="button" onClick={() => setAsSent(!asSent)} className="mt-3 text-[13px] text-quiet underline underline-offset-4 hover:text-ink">{asSent ? "show just the words" : "show the email as sent"}</button> : null}
    </div>
  );
}

/** reply, from the address they wrote to (or another of ours), and the thread's own switches */
export function Reply({ id, to, box, domain, boxes, archived, unread }: { id: string; to: string; box: string; domain: string; boxes: string[]; archived: boolean; unread: boolean }) {
  const post = useAdminPost();
  const say = useToast();
  const router = useRouter();
  const [from, setFrom] = useState(box);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const act = async (action: string, extra: Record<string, unknown> = {}) => {
    setBusy(action);
    setErr("");
    const r = await post("/api/admin/inbox", { id, action, ...extra });
    setBusy("");
    if (!r.ok) return setErr(r.error);
    say(true, String(r.data.message ?? "done"));
    if (action === "reply") setBody("");
    if (action === "archive") return router.push("/admin/mail");
    startTransition(() => router.refresh());
  };
  const list = boxes.includes(box) ? boxes : [box, ...boxes];
  return (
    <div className="grid gap-4">
      <form className="grid gap-3" onSubmit={(e) => { e.preventDefault(); if (body.trim() && !busy) void act("reply", { body, from }); }}>
        <div className="flex flex-wrap items-center gap-2 text-[13px] text-quiet">
          reply to <span className="text-ink">{to}</span> from
          <Picker small value={from} onChange={setFrom} label="reply from" className="w-[220px]" options={list.map((b) => ({ value: b, label: `${b}@${domain}` }))} />
        </div>
        <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={7} placeholder="write your reply. a blank line starts a new paragraph; their email is quoted under it."
          className={`${FIELD} !h-auto min-h-[160px] py-3 leading-relaxed`} onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && body.trim()) void act("reply", { body, from }); }} />
        {err ? <p className="a-pop rounded-[12px] bg-bad/10 px-4 py-3 text-[14px] text-bad">{err}</p> : null}
        <div className="flex flex-wrap gap-2">
          <button type="submit" disabled={!body.trim() || !!busy} className={BTN.main}>{busy === "reply" ? "sending…" : "send reply"}</button>
          <button type="button" disabled={!!busy} onClick={() => void act(archived ? "unarchive" : "archive")} className={BTN.plain}>{archived ? "back to the inbox" : "archive"}</button>
          <button type="button" disabled={!!busy} onClick={() => void act(unread ? "read" : "unread")} className={BTN.plain}>{unread ? "mark read" : "mark unread"}</button>
        </div>
      </form>
    </div>
  );
}
