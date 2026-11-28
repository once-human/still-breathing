import { createHmac, timingSafeEqual } from "node:crypto";
import { receive } from "@/lib/shop/inbox";

export const dynamic = "force-dynamic";

/**
 * Resend's webhook for mail to any @sahn.in address ("email.received"). The body only carries the email's id: we
 * fetch the email itself with our own key, so a forged call can at most point at an email Resend really has. With
 * RESEND_WEBHOOK_SECRET set in Vercel (the webhook's signing secret), every call is also checked for Resend's
 * signature. Answering non-2xx makes Resend try again later, so only a passing hiccup does.
 */
function signed(req: Request, body: string) {
  const secret = process.env.RESEND_WEBHOOK_SECRET?.trim();
  if (!secret) return true;
  const id = req.headers.get("svix-id"), ts = req.headers.get("svix-timestamp"), sig = req.headers.get("svix-signature");
  if (!id || !ts || !sig || Math.abs(Date.now() / 1000 - Number(ts)) > 600) return false;
  const want = Buffer.from(createHmac("sha256", Buffer.from(secret.replace(/^whsec_/, ""), "base64")).update(`${id}.${ts}.${body}`).digest("base64"));
  return sig.split(" ").some((s) => {
    const got = Buffer.from(s.split(",")[1] ?? "");
    return got.length === want.length && timingSafeEqual(got, want);
  });
}

export async function POST(req: Request) {
  const body = await req.text();
  if (body.length > 200_000) return new Response("too big", { status: 413 });
  if (!signed(req, body)) return new Response("bad signature", { status: 401 });
  let e: { type?: string; data?: { email_id?: string } };
  try { e = JSON.parse(body); } catch { return new Response("bad json", { status: 400 }); }
  if (e.type !== "email.received" || typeof e.data?.email_id !== "string") return new Response("ignored");
  try {
    await receive(e.data.email_id);
    return new Response("ok");
  } catch (x) {
    console.error("inbox:", x instanceof Error ? x.message : x);
    return new Response("try again", { status: 503 });
  }
}
