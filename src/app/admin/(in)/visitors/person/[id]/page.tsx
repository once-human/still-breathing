import { notFound } from "next/navigation";
import { requireAdmin } from "@/lib/admin/auth";
import { linkedPeople } from "@/lib/shop/account";
import { listVisits } from "@/lib/visits/server";
import { span } from "@/lib/visits/shared";
import { Act } from "../../../../ui/client";
import { Group, Page, Section, Tile } from "../../../../ui/ui";
import { VisitTable, time } from "../../../../ui/visits";

export const metadata = { title: "visitor" };
export const dynamic = "force-dynamic";

/** one browser over the kept 180 days: its visits, and a way to forget it */
export default async function Person({ params }: { params: Promise<{ id: string }> }) {
  await requireAdmin();
  const id = (await params).id;
  if (!/^[a-f0-9]{12}$/.test(id)) notFound();
  const [visits, names] = await Promise.all([listVisits({ from: 0, to: Date.now() }, { kind: "person", person: id }, 200).catch(() => []), linkedPeople().catch(() => new Map<string, { email: string; name: string }>())]);
  const who = names.get(id);
  if (!visits.length) notFound();
  const first = visits[visits.length - 1], last = visits[0];
  const ms = visits.reduce((t, v) => t + v.activeMs, 0), pages = visits.reduce((t, v) => t + v.pages, 0);
  const devices = [...new Set(visits.map((v) => v.device))];
  return (
    <>
      <Page title={who ? (who.name || who.email).toLowerCase() : `visitor ${id.slice(0, 6)}`} back={["/admin/visitors?tab=people", "people"]}
        sub={who ? `${who.email}: first seen ${time(first.startedAt)}, last ${time(last.lastAt)}. their browser, linked while they were signed in` : `first seen ${time(first.startedAt)}, last ${time(last.lastAt)}. one browser's own random code: no name, no address`}
        actions={who ? <a href={`/admin/people/${encodeURIComponent(who.email)}`} className="text-[15px] text-quiet hover:text-ink">their profile →</a> : undefined} />
      <div className="mb-10 grid grid-cols-2 gap-3 md:mb-12 lg:grid-cols-4">
        <Tile label="visits" icon="return" value={visits.length} />
        <Tile label="pages" icon="list" value={pages} />
        <Tile label="on screen" icon="clock" value={span(ms)} />
        <Tile label="devices" icon="phone" value={devices.length} sub={devices.join(", ")} />
      </div>
      <Section title="every visit"><VisitTable visits={visits} /></Section>
      <Section title="manage">
        <Group>
          <Act danger label="forget this visitor" row={{ icon: "trash", sub: "every visit and every step deleted for good" }} typeToConfirm="FORGET" url="/api/admin/visitors" body={{ action: "forget", person: id }} goTo="/admin/visitors?tab=people"
            confirm="every visit of theirs, and every step in it, deleted for good (for when they ask, or it's you testing)." />
        </Group>
      </Section>
    </>
  );
}
