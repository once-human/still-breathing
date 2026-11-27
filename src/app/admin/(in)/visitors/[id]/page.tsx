import { notFound } from "next/navigation";
import { requireAdmin } from "@/lib/admin/auth";
import { visitById } from "@/lib/visits/server";
import { span } from "@/lib/visits/shared";
import { Card, Group, KV, Page, Row, Section } from "../../../ui/ui";
import { Reached, Timeline, shirtLabel, time, where } from "../../../ui/visits";

export const metadata = { title: "visit" };
export const dynamic = "force-dynamic";

/** one visit: every step with its time, and what's known about it */
export default async function Visit({ params }: { params: Promise<{ id: string }> }) {
  await requireAdmin();
  const r = await visitById(decodeURIComponent((await params).id)).catch(() => null);
  if (!r) notFound();
  const { visit: v, events } = r;
  const live = Date.now() - Date.parse(v.lastAt) < 60_000;
  return (
    <>
      <Page title={v.kind === "bot" ? (v.device ?? "a program").toLowerCase() : where(v)} back={["/admin/visitors", "visits"]}
        sub={<>{live ? <span className="mr-2 inline-flex items-center gap-1.5 text-ink"><span className="h-2 w-2 rounded-full bg-ok" />on the site now</span> : null}{time(v.startedAt)} to {time(v.lastAt)}, {v.pages} page{v.pages === 1 ? "" : "s"}, {span(v.activeMs)} on screen</>} />
      <div className="grid gap-x-6 lg:grid-cols-[1.4fr_1fr]">
        <Section title="step by step">
          <Card>{events.length ? <Timeline events={events} /> : <p className="text-[15px] text-quiet">nothing kept</p>}</Card>
        </Section>
        <div>
          <Section title="the visit">
            <KV items={[
              ["who", v.kind === "bot" ? `a program: ${v.reason ?? ""}` : v.nth && v.nth > 1 ? `came back: visit ${v.nth}` : "first visit"],
              ["where", `${v.city ?? "–"}${v.region ? `, ${v.region}` : ""}${v.country ? ` (${v.country})` : ""}`],
              ["device", v.device],
              ["screen", v.screen],
              ["language", v.lang],
              ["came from", v.referrer ?? "direct: typed, a bookmark or an app"],
              ["shirts seen", v.shirts.map(shirtLabel).join(", ") || "–"],
              ["got to", v.reached.length ? <Reached key="r" steps={v.reached} /> : "browsing"],
            ]} />
          </Section>
          {v.person ? (
            <Section title="this person">
              <Group><Row icon="user" title="every visit of theirs" sub="the same browser, over the kept 90 days" href={`/admin/visitors/person/${v.person}`} /></Group>
            </Section>
          ) : null}
        </div>
      </div>
    </>
  );
}
