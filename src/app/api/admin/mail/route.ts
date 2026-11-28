import { randomBytes } from "node:crypto";
import { BOXES, box } from "@/content/mail";
import { adminEmail, audit } from "@/lib/admin/auth";
import { adminWrite, failedAction, ok, str } from "@/lib/admin/guard";
import { validEmail } from "@/lib/shop/account";
import { ownerEmail } from "@/lib/shop/config";
import { everyone, logSend, sendDrop, sendLetter } from "@/lib/shop/drops";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

/**
 * Email from the admin, by `action`:
 *   drop {subject, body, link?, test?}                       a new drop to everyone on the list (test: only to you), from drops@
 *   letter {local, name, to, subject, body, link?, signoff, test?}   an email of your own from name@, to up to 50 people
 * `to` is addresses split by commas, spaces or lines. Each person gets their own copy: nobody sees anyone else.
 */
export async function POST(req: Request) {
  const g = await adminWrite(req, 60_000);
  if ("fail" in g) return g.fail;
  const b = g.body;
  const subject = str(b.subject, 150), body = typeof b.body === "string" ? b.body.replace(/\r\n/g, "\n").trim().slice(0, 20_000) : "";
  const rawLink = str(b.link, 500);
  const link = rawLink ? (/^https:\/\/[^\s"<>]+$/.test(rawLink) ? rawLink : null) : null;
  if (!subject) return ok({ error: "a subject" }, 400);
  if (!body) return ok({ error: "something to say" }, 400);
  if (rawLink && !link) return ok({ error: "the link starts with https://" }, 400);
  const me = adminEmail() ?? ownerEmail();
  const test = b.test === true;
  if (test && !me) return ok({ error: "no ADMIN_EMAIL in vercel to send the test to" }, 400);
  const idem = `${b.action}-${randomBytes(8).toString("hex")}`;
  try {
    if (b.action === "drop") {
      const list = test ? [me!] : await everyone();
      if (!list.length) return ok({ error: "nobody is on the list yet" }, 400);
      const r = await sendDrop(list, test ? `[test] ${subject}` : subject, body, link, idem);
      if (!test) {
        await logSend("drop", `${BOXES.drops.name} <${box("drops")}>`, [], subject, body, link, r.sent, r.failed, g.admin.email);
        await audit(g.admin.email, "mail.drop", null, { subject, sent: r.sent, failed: r.failed }, g.ip);
      }
      if (!r.sent) return ok({ error: "resend didn't take it: see the logs in vercel" }, 502);
      return ok({ message: test ? `test sent to ${me}` : `sent to ${r.sent}${r.failed ? `, ${r.failed} failed` : ""}` });
    }
    if (b.action === "letter") {
      const local = str(b.local, 40).toLowerCase();
      if (!/^[a-z0-9](?:[a-z0-9._-]{0,38}[a-z0-9])?$/.test(local)) return ok({ error: "the part before @: letters, numbers, dots, dashes", field: "local" }, 400);
      const name = str(b.name, 60).replace(/["<>\r\n]/g, "") || "sahn";
      const signoff = (typeof b.signoff === "string" ? b.signoff.trim().slice(0, 200) : "") || name;
      const to = [...new Set(str(b.to, 6000).toLowerCase().split(/[\s,;]+/).filter(Boolean))];
      const bad = to.filter((e) => !validEmail(e));
      if (!test && !to.length) return ok({ error: "who it goes to", field: "to" }, 400);
      if (bad.length) return ok({ error: `not an email: ${bad.slice(0, 3).join(", ")}`, field: "to" }, 400);
      if (to.length > 50) return ok({ error: "50 people at most: for everyone, send a drop", field: "to" }, 400);
      const list = test ? [me!] : to;
      const r = await sendLetter(local, name, list, test ? `[test] ${subject}` : subject, body, link, signoff, idem);
      if (!test) {
        await logSend("letter", r.from, to, subject, body, link, r.sent, r.failed, g.admin.email);
        await audit(g.admin.email, "mail.letter", null, { from: r.from, to: to.length, subject, sent: r.sent, failed: r.failed }, g.ip);
      }
      if (!r.sent) return ok({ error: "resend didn't take it: see the logs in vercel" }, 502);
      return ok({ message: test ? `test sent to ${me}` : `sent to ${r.sent}${r.failed ? `, ${r.failed} failed` : ""}` });
    }
    return ok({ error: "unknown action" }, 400);
  } catch (e) {
    return failedAction(g.admin, `mail.${String(b.action)}`, null, e, g.ip);
  }
}
