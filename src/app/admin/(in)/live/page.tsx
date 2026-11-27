import { requireAdmin } from "@/lib/admin/auth";
import { liveCount, liveNow } from "@/lib/visits/server";
import { PageHead } from "../../ui/ui";
import { Live } from "./Live";

export const metadata = { title: "live now" };
export const dynamic = "force-dynamic";

export default async function LivePage() {
  await requireAdmin();
  const [people, count] = await Promise.all([liveNow().catch(() => []), liveCount()]);
  return (
    <>
      <PageHead title="live now" sub="everyone on the site this minute: the page they're on, where they came from, what's in their bag" />
      <Live initial={{ people, count }} />
    </>
  );
}
