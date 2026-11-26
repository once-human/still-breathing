import { record } from "@/lib/admin/activity";
import { ipOf } from "@/lib/shop/guard";
import { kvKeys } from "@/lib/shop/config";

export const dynamic = "force-dynamic";

/**
 * The site's visit log (src/components/Beacon.tsx sends here): { k: view | bag | checkout, p: path, r: referrer,
 * u: utm_source, d: shirt, s: size }. Only from our own pages; always answers 204, so it tells a caller nothing.
 */
export async function POST(req: Request) {
  const site = req.headers.get("sec-fetch-site");
  if (kvKeys() && (!site || site === "same-origin")) {
    const text = await req.text().catch(() => "");
    if (text.length <= 1000) {
      try {
        await record(req, JSON.parse(text), ipOf(req));
      } catch {
        /* a bad body or a database hiccup: a visit not counted, nothing more */
      }
    }
  }
  return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
}
