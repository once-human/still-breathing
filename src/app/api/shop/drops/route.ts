import { subscribe, tokenOk, unsubscribe } from "@/lib/shop/drops";
import { validEmail } from "@/lib/shop/account";
import { json } from "@/lib/shop/guard";

export const dynamic = "force-dynamic";

/**
 * Off the new-drop list, by the link in a drop email: POST ?e=&t= (the one-tap button mail apps show, and the
 * button on /unsubscribe). {on: true} in the body puts them back, for "that was a mistake".
 */
export async function POST(req: Request) {
  const u = new URL(req.url);
  const e = (u.searchParams.get("e") ?? "").trim().toLowerCase(), t = u.searchParams.get("t") ?? "";
  if (!validEmail(e) || !t || !tokenOk(e, t)) return json({ error: "that link isn't right: use the one in your latest email" }, 400);
  const back = req.headers.get("content-type")?.startsWith("application/json") ? ((await req.json().catch(() => ({}))) as { on?: unknown }).on === true : false;
  if (back) await subscribe(e, "back on");
  else await unsubscribe(e);
  return json({ ok: true, on: back });
}
