import Link from "next/link";
import { notFound } from "next/navigation";
import { requireAdmin } from "@/lib/admin/auth";
import { visitById } from "@/lib/visits/server";
import { span } from "@/lib/visits/shared";
import { KV, PageHead, Section } from "../../../ui/ui";
import { Reached, Timeline, shirtLabel, time, where } from "../../../ui/visits";

export const metadata = { title: "visit" };
export const dynamic = "force-dynamic";

export default async function Visit({ params }: { params: Promise<{ id: string }> }) {
  await requireAdmin();
  const r = await visitById(decodeURIComponent((await params).id)).catch(() => null);
  if (!r) notFound();
  const { visit: v, events } = r;
  const live = Date.now() - Date.parse(v.lastAt) < 60_000;
  return (
    <>
      <PageHead title={v.kind === "bot" ? (v.device ?? "a program") : `${where(v)}, ${v.device ?? ""}`} sub={<>
        {live ? <span className="text-[#8fd19e]">● on the site now · </span> : null}{time(v.startedAt)} → {time(v.lastAt)} · {v.pages} page{v.pages === 1 ? "" : "s"} · {span(v.activeMs)} on screen
      </>}>
        {v.person ? <Link href={`/admin/visitors/person/${v.person}`} className="text-[13px] text-quiet underline decoration-line underline-offset-4 hover:text-ink">all of this person&apos;s visits →</Link> : null}
      </PageHead>
      <div className="grid gap-x-12 lg:grid-cols-[1.5fr_1fr]">
        <Section title="step by step">
          {events.length ? <Timeline events={events} /> : <p className="text-[13px] text-quiet">nothing kept</p>}
        </Section>
        <Section title="the visit">
          <KV items={[
            ["who", v.kind === "bot" ? `a program: ${v.reason ?? ""}` : v.nth && v.nth > 1 ? `returning: visit ${v.nth}` : "first visit"],
            ["where", `${v.city ?? "–"}${v.region ? `, ${v.region}` : ""}${v.country ? ` (${v.country})` : ""}`],
            ["device", v.device],
            ["screen", v.screen],
            ["language", v.lang],
            ["came from", v.referrer ?? "direct (typed, a bookmark or an app)"],
            ["shirts seen", v.shirts.map(shirtLabel).join(", ") || "–"],
            ["got to", v.reached.length ? <Reached key="r" steps={v.reached} /> : "browsing"],
          ]} />
        </Section>
      </div>
    </>
  );
}
