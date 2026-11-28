import { BOXES, MAIL_DOMAIN } from "@/content/mail";
import { adminEmail, requireAdmin } from "@/lib/admin/auth";
import { mailKeys, ownerEmail } from "@/lib/shop/config";
import { listStats } from "@/lib/shop/drops";
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
  const s = await listStats().catch(() => ({ on: 0, off: 0, recent: [], sends: [] }));
  const presets = Object.entries(BOXES).filter(([k]) => k !== "signin").map(([local, b]) => ({ local, name: b.name, use: b.use }));

  return (
    <>
      <Page title="email" sub={`write from any address @${domain}, or tell the ${s.on} on the drop list about something new. replies to every address come to your inbox.`} />
      {!keys ? <Missing>email isn&apos;t set up: add RESEND_API_KEY and SHOP_EMAIL_FROM in vercel.</Missing> : null}
      <Tabs active={tab} items={[{ key: "letter", label: "write", href: "?k=letter" }, { key: "drop", label: "new drop", href: "?k=drop", count: s.on }]} />

      <Section title={tab === "drop" ? "a new drop" : "write an email"}>
        <Card><Compose kind={tab} domain={domain} presets={presets} listSize={s.on} me={adminEmail() ?? ownerEmail()} /></Card>
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
        ) : <Empty icon="people" title="nobody yet" sub="people join with the box at checkout, when they make a profile, or in their profile. it's off until they tick it." />}
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
