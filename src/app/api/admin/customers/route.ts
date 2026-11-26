import { audit } from "@/lib/admin/auth";
import { adminWrite, ok, str } from "@/lib/admin/guard";
import { addNote } from "@/lib/admin/log";
import { validEmail } from "@/lib/shop/account";

export const dynamic = "force-dynamic";

/** { email, text }: a note on a customer */
export async function POST(req: Request) {
  const g = await adminWrite(req);
  if ("fail" in g) return g.fail;
  const email = str(g.body.email, 120).toLowerCase(), text = str(g.body.text, 2000);
  if (!validEmail(email) || !text) return ok({ error: "email and text needed" }, 400);
  await addNote(`customer:${email}`, g.admin.email, text);
  await audit(g.admin.email, "customer.note", `customer:${email}`, { length: text.length }, g.ip);
  return ok({ message: "saved" });
}
