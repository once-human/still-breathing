import { notFound } from "next/navigation";
import { requireAdmin } from "@/lib/admin/auth";
import { listVisits } from "@/lib/visits/server";
import { span } from "@/lib/visits/shared";
import { Act } from "../../../../ui/client";
import { PageHead, Section, Stat } from "../../../../ui/ui";
import { VisitTable, time } from "../../../../ui/visits";

export const metadata = { title: "person" };
export const dynamic = "force-dynamic";

export default async function Person({ params }: { params: Promise<{ id: string }> }) {
  await requireAdmin();
  const id = (await params).id;
  if (!/^[a-f0-9]{12}$/.test(id)) notFound();
  const visits = await listVisits(24 * 90, { kind: "person", person: id }, 200).catch(() => []);
  if (!visits.length) notFound();
  const first = visits[visits.length - 1], last = visits[0];
  const ms = visits.reduce((t, v) => t + v.activeMs, 0), pages = visits.reduce((t, v) => t + v.pages, 0);
  return (
    <>
      <PageHead title={`person ${id.slice(0, 6)}`} sub={`first seen ${time(first.startedAt)}, last ${time(last.lastAt)} · one browser's own random code: no name, no address`}>
        <Act danger small label="forget this person" typeToConfirm="FORGET" url="/api/admin/visitors" body={{ action: "forget", person: id }} goTo="/admin/visitors?tab=people"
          confirm="every visit of theirs, and every step in it, deleted for good (for when they ask, or it's you testing)." />
      </PageHead>
      <Section title="in the kept 90 days">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat label="visits" value={visits.length} />
          <Stat label="pages" value={pages} />
          <Stat label="time on screen" value={span(ms)} />
          <Stat label="devices" value={new Set(visits.map((v) => v.device)).size} sub={[...new Set(visits.map((v) => v.device))].join(", ")} />
        </div>
      </Section>
      <Section title="every visit"><VisitTable visits={visits} /></Section>
    </>
  );
}
