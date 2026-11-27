import { audit } from "@/lib/admin/auth";
import { adminWrite, failedAction, ok, str } from "@/lib/admin/guard";
import { forgetPerson } from "@/lib/visits/server";

export const dynamic = "force-dynamic";

/** { action: "forget", person }: one person's whole visit log wiped (they asked, or it's you testing) */
export async function POST(req: Request) {
  const g = await adminWrite(req);
  if ("fail" in g) return g.fail;
  const person = str(g.body.person, 12);
  if (str(g.body.action, 20) !== "forget" || !/^[a-f0-9]{12}$/.test(person)) return ok({ error: "unknown action" }, 400);
  try {
    const n = await forgetPerson(person);
    await audit(g.admin.email, "visitor.forget", `person:${person}`, { visits: n }, g.ip);
    return ok({ message: `forgot ${n} visit${n === 1 ? "" : "s"}` });
  } catch (e) {
    return failedAction(g.admin, "visitor.forget", `person:${person}`, e, g.ip);
  }
}
