import { audit } from "@/lib/admin/auth";
import { adminWrite, failedAction, ok, str } from "@/lib/admin/guard";
import { archive, markRead, reply } from "@/lib/shop/inbox";

export const dynamic = "force-dynamic";

/** one conversation: { id, action: reply {body, from?} | read | unread | archive | unarchive } */
export async function POST(req: Request) {
  const g = await adminWrite(req, 60_000);
  if ("fail" in g) return g.fail;
  const id = str(g.body.id, 20);
  if (!/^\d{1,18}$/.test(id)) return ok({ error: "no such conversation" }, 400);
  const action = str(g.body.action, 20);
  try {
    switch (action) {
      case "reply": {
        const body = typeof g.body.body === "string" ? g.body.body.replace(/\r\n/g, "\n").trim().slice(0, 20_000) : "";
        if (!body) return ok({ error: "something to say" }, 400);
        const local = str(g.body.from, 40).toLowerCase();
        if (local && !/^[a-z0-9](?:[a-z0-9._-]{0,38}[a-z0-9])?$/.test(local)) return ok({ error: "the part before @: letters, numbers, dots, dashes" }, 400);
        const from = await reply(id, body, g.admin.email, local || undefined);
        await audit(g.admin.email, "inbox.reply", `thread:${id}`, { from, length: body.length }, g.ip);
        return ok({ message: `sent from ${from}` });
      }
      case "read": case "unread":
        await markRead(id, action === "read");
        return ok({ message: action === "read" ? "marked read" : "marked unread" });
      case "archive": case "unarchive":
        await archive(id, action === "archive");
        return ok({ message: action === "archive" ? "archived" : "back in the inbox" });
    }
    return ok({ error: "unknown action" }, 400);
  } catch (e) {
    return failedAction(g.admin, `inbox.${action}`, `thread:${id}`, e, g.ip);
  }
}
