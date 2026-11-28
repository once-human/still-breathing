import { notFound } from "next/navigation";
import { BOXES, MAIL_DOMAIN } from "@/content/mail";
import { requireAdmin } from "@/lib/admin/auth";
import { mailKeys } from "@/lib/shop/config";
import { markRead, thread, threads } from "@/lib/shop/inbox";
import { A, Avatar, Badge, Card, Page, Row, Group, Section, dt } from "../../../ui/ui";
import { Body, Reply } from "./Thread";

export const metadata = { title: "conversation" };
export const dynamic = "force-dynamic";

const size = (n: number | null) => (n == null ? "" : n > 1_000_000 ? `${(n / 1_000_000).toFixed(1)} mb` : `${Math.max(1, Math.round(n / 1000))} kb`);

/** one conversation, oldest first, with the reply box under it; opening it marks it read */
export default async function Conversation({ params }: { params: Promise<{ id: string }> }) {
  await requireAdmin();
  const { id } = await params;
  const t = await thread(id).catch(() => null);
  if (!t) notFound();
  const wasUnread = t.thread.unread > 0;
  if (wasUnread) await markRead(id).catch(() => {});
  const domain = mailKeys()?.domain ?? MAIL_DOMAIN;
  const others = (await threads({ email: t.thread.email, view: "all", limit: 6 })).filter((x) => x.id !== id);
  const who = t.thread.name || t.thread.email;

  return (
    <>
      <Page title={t.thread.subject || "(no subject)"} back={["/admin/mail", "email"]}
        sub={<span className="flex flex-wrap items-center gap-2"><Avatar name={who} /> <span>{who}{t.thread.name ? <span className="text-quiet"> · {t.thread.email}</span> : null}</span>
          <Badge>{t.thread.box}@</Badge>{t.thread.order ? <A href={`/admin/orders/${t.thread.order}`}>order #{t.thread.order}</A> : null}
          <A href={`/admin/people/${encodeURIComponent(t.thread.email)}`}>who they are →</A></span>} />

      <div className="mb-10 grid gap-3">
        {t.messages.map((m) => (
          <Card key={m.id} className={m.dir === "out" ? "ml-0 md:ml-16 !bg-s2" : ""}>
            <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2 text-[13px] text-quiet">
              <span><span className="text-[15px] text-ink">{m.dir === "out" ? `you, as ${m.from}` : m.fromName || m.from}</span>{m.dir === "in" && m.fromName ? ` · ${m.from}` : ""}
                {m.to.length && m.dir === "in" ? ` → ${m.to.join(", ")}` : ""}{m.cc.length ? ` · cc ${m.cc.join(", ")}` : ""}</span>
              <span title={m.at}>{dt(m.at)}{m.auth && m.dir === "in" && (m.auth.spf === "fail" || m.auth.dmarc === "fail") ? <span className="text-bad"> · may not really be from them</span> : null}</span>
            </div>
            <Body text={m.text} html={m.dir === "in" ? m.html : null} />
            {m.attachments.filter((a) => !a.inline).length && m.resendId ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {m.attachments.filter((a) => !a.inline).map((a) => (
                  <a key={a.id} href={`/api/admin/inbox/attachment?e=${m.resendId}&a=${a.id}`} target="_blank" rel="noreferrer" className="rounded-full bg-s2 px-4 py-1.5 text-[13px] hover:bg-s3">
                    {a.filename} <span className="text-quiet">{size(a.size)}</span>
                  </a>
                ))}
              </div>
            ) : null}
          </Card>
        ))}
      </div>

      <Section title="reply">
        <Card><Reply id={id} to={t.thread.email} box={t.thread.box} domain={domain} boxes={Object.keys(BOXES)} archived={t.thread.archived} unread={false} /></Card>
      </Section>

      {others.length ? (
        <Section title={`more from ${t.thread.name || "them"}`}>
          <Group>{others.map((o) => <Row key={o.id} href={`/admin/mail/${o.id}`} title={o.subject || "(no subject)"} sub={o.snippet} right={<span className="text-[13px] text-quiet">{dt(o.at)}</span>} />)}</Group>
        </Section>
      ) : null}
    </>
  );
}
