import { limited } from "@/lib/shop/guard";
import { kvKeys } from "@/lib/shop/config";
import { notOurPage } from "@/lib/visits/bots";
import { forget, mine, record } from "@/lib/visits/server";
import { ID, type TrackBatch } from "@/lib/visits/shared";

export const dynamic = "force-dynamic";

/**
 * The visitor log (see /policies/privacy).
 *
 *   POST   /api/track            a batch from the page: the visit, pages, links out, shop steps
 *   GET    /api/track  (x-visitor: <code>)  everything kept about this browser
 *   DELETE /api/track  (x-visitor: <code>)  forget it all
 *
 * <code> is the random code the browser made for itself; only that browser has it. No IP address is ever stored.
 */
const headers = { "Cache-Control": "no-store" };

export async function POST(req: Request) {
  if (!kvKeys()) return new Response(null, { status: 204 });
  // Sent with navigator.sendBeacon, so it may arrive as text.
  const text = await req.text();
  if (text.length > 64_000) return new Response(null, { status: 413 });
  let b: TrackBatch;
  try {
    b = JSON.parse(text) as TrackBatch;
  } catch {
    return new Response(null, { status: 400 });
  }
  if (!b || !ID.test(b.v ?? "") || !ID.test(b.s ?? "") || !Array.isArray(b.events)) return new Response(null, { status: 400 });
  // Posted from another site: not ours at all.
  if (notOurPage(req)?.startsWith("sent from")) return new Response(null, { status: 403 });
  // A busy visit sends a batch every few seconds at most, and one browser doesn't make hundreds of visits an hour.
  if ((await limited(`track:${b.s}`, 400, 3600_000)) || (await limited(`track-v:${b.v}`, 900, 3600_000))) return new Response(null, { status: 429 });
  const ok = await record(req, b).catch(() => false);
  return new Response(null, { status: ok ? 204 : 409, headers });
}

const code = (req: Request) => {
  // a header, not the address, so the code never sits in a request log
  const v = req.headers.get("x-visitor") ?? "";
  return ID.test(v) ? v : null;
};

export async function GET(req: Request) {
  const v = code(req);
  if (!v || !kvKeys()) return Response.json({ visits: [] }, { headers });
  if (await limited(`track-me:${v}`, 60, 3600_000)) return Response.json({ error: "too many" }, { status: 429, headers });
  return Response.json(await mine(v), { headers });
}

export async function DELETE(req: Request) {
  const v = code(req);
  if (!v || !kvKeys()) return Response.json({ deleted: 0 }, { headers });
  if (notOurPage(req)?.startsWith("sent from")) return new Response(null, { status: 403 });
  if (await limited(`track-forget:${v}`, 10, 3600_000)) return Response.json({ error: "too many" }, { status: 429, headers });
  return Response.json({ deleted: await forget(v) }, { headers });
}
