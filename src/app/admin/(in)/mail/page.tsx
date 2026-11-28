import { BOXES, MAIL_DOMAIN } from "@/content/mail";
import { adminEmail, requireAdmin } from "@/lib/admin/auth";
import { mailKeys, ownerEmail } from "@/lib/shop/config";
import { DAYS, GROUPS } from "@/lib/shop/audience";
import { listStats } from "@/lib/shop/drops";
import { makerNotes } from "@/lib/shop/maker";
import { Badge, Card, Empty, Group, Missing, Page, Row, Section, Tabs, ago, dt } from "../../ui/ui";
import { Compose } from "./Compose";

export const metadata = { title: "email" };
export const dynamic = "force-dynamic";

const SOURCE: Record<string, string> = { checkout: "at checkout", welcome: "making a profile", profile: "in their profile" };

/** email: write one from any sahn.in address, send a new drop to the list, and see what went out */
export default async function Mail({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  await requireAdmin();
  const sp = await searchParams;
  const tab = sp.k === "drop" ? "drop" : "letter";
  const keys = mailKeys();
  const domain = keys?.domain ?? MAIL_DOMAIN;
  const [s, notes] = await Promise.all([listStats().catch(() => ({ on: 0, off: 0, recent: [], sends: [] })), makerNotes(30)]);
  const presets = Object.entries(BOXES).map(([local, b]) => ({ local, name: b.name, use: b.use }));

  return (
    <>
      <Page title="email" sub={`write from any address @${domain} to anyone, a group of customers, or the ${s.on} on the drop list. replies to every address come to your inbox.`} />
      {!keys ? <Missing>email isn&apos;t set up: add RESEND_API_KEY and SHOP_EMAIL_FROM in vercel.</Missing> : null}
      <Tabs active={tab} items={[{ key: "letter", label: "write", href: "?k=letter" }, { key: "drop", label: "new drop", href: "?k=drop", count: s.on }]} />

      <Section title={tab === "drop" ? "a new drop" : "write an email"}>
        <Card><Compose kind={tab} domain={domain} presets={presets} listSize={s.on} me={adminEmail() ?? ownerEmail()}
          groups={Object.entries(GROUPS).map(([key, x]) => ({ key, ...x }))} days={[...DAYS]} /></Card>
      </Section>

      <Section title="for the maker" aside="notes from the contact page, also emailed to you">
        {notes.length ? (
          <Group>
            {notes.map((n) => (
              <Row key={n.id} icon="note" tone={n.mailed ? "quiet" : "warn"} href={`/admin/people/${encodeURIComponent(n.email)}`}
                title={<span>{n.name}{n.order ? <span className="text-quiet"> · #{n.order}</span> : null}</span>}
                sub={<span className="line-clamp-3 whitespace-pre-line">{n.body}</span>}
                right={<span className="grid justify-items-end gap-1 text-[13px] text-quiet">
                  <span>{n.email}</span>
                  <span title={dt(n.at)}>{ago(n.at)}{n.mailed ? "" : " · email didn't go"}</span>
                </span>} />
            ))}
          </Group>
        ) : <Empty icon="note" title="no notes to the maker" sub="the form at /contact sends them here and to your inbox, under “for the maker: …”." />}
      </Section>

      <Section title="sent" aside={s.sends.length ? `the last ${s.sends.length}` : undefined}>
        {s.sends.length ? (
          <Group>
            {s.sends.map((x) => (
              <Row key={x.id} icon={x.kind === "drop" ? "shirt" : "mail"} tone={x.failed ? "warn" : "quiet"}
                title={x.subject}
                sub={<>{x.from}{x.kind === "letter" ? ` → ${x.to}${x.count > 3 ? ` +${x.count - 3}` : ""}` : " → the drop list"}</>}
                right={<span className="grid justify-items-end gap-1 text-[13px] text-quiet">
                  <span className="tnum text-[15px] text-ink">{x.sent} sent{x.failed ? <span className="text-bad">, {x.failed} failed</span> : null}</span>
                  <span title={dt(x.at)}>{ago(x.at)}</span>
                </span>} />
            ))}
          </Group>
        ) : <Empty icon="mail" title="nothing sent from here yet" />}
      </Section>

      <Section title="the drop list" aside={`${s.on} on it${s.off ? `, ${s.off} left` : ""}`}>
        {s.recent.length ? (
          <Group>
            {s.recent.map((r) => (
              <Row key={r.email} href={`/admin/people/${encodeURIComponent(r.email)}`} title={r.email} sub={`joined ${SOURCE[r.source] ?? r.source}`} right={<span className="text-[13px] text-quiet" title={dt(r.at)}>{ago(r.at)}</span>} />
            ))}
          </Group>
        ) : <Empty icon="people" title="nobody yet" sub="people join with the box at checkout, when they make a profile, or in their profile. the box starts ticked; anyone can untick it, or leave with one tap from any email." />}
      </Section>

      <Section title="the addresses" aside="every one forwards to your inbox">
        <Group>
          {Object.entries(BOXES).map(([local, b]) => (
            <Row key={local} title={<span>{local}@{domain} <Badge>{b.name}</Badge></span>} sub={b.use} />
          ))}
        </Group>
      </Section>
    </>
  );
}
