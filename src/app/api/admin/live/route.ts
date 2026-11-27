import { adminRead, ok } from "@/lib/admin/guard";
import { liveCount, liveNow } from "@/lib/visits/server";

export const dynamic = "force-dynamic";

/** who is on the site now (?count=1: only how many, for the menu) */
export async function GET(req: Request) {
  const g = await adminRead();
  if ("fail" in g) return g.fail;
  if (new URL(req.url).searchParams.get("count")) return ok(await liveCount());
  const [people, count] = await Promise.all([liveNow(), liveCount()]);
  return ok({ people, count });
}
