import { adminRead } from "@/lib/admin/guard";
import { attachmentLink } from "@/lib/shop/inbox";

export const dynamic = "force-dynamic";

/** ?e=<resend email id>&a=<attachment id> → a fresh download link (Resend's last an hour) */
export async function GET(req: Request) {
  const g = await adminRead();
  if ("fail" in g) return g.fail;
  const u = new URL(req.url);
  const e = u.searchParams.get("e") ?? "", a = u.searchParams.get("a") ?? "";
  if (!/^[0-9a-f-]{20,64}$/i.test(e) || !/^[0-9a-f-]{20,64}$/i.test(a)) return new Response("no such file", { status: 400 });
  const link = await attachmentLink(e, a);
  return link ? Response.redirect(link, 302) : new Response("that file isn't there any more", { status: 404 });
}
