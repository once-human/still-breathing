import { revalidateTag } from "next/cache";
import { audit } from "@/lib/admin/auth";
import { adminWrite, failedAction, ok } from "@/lib/admin/guard";
import { saveSettings } from "@/lib/admin/settings";

export const dynamic = "force-dynamic";

/** { key: value, ... }: each checked against its rules; the change, from → to, goes in the audit log */
export async function POST(req: Request) {
  const g = await adminWrite(req);
  if ("fail" in g) return g.fail;
  try {
    const changed = await saveSettings(g.body, g.admin.email);
    if (Object.keys(changed).length) {
      await audit(g.admin.email, "settings.save", "settings", changed, g.ip);
      // prices follow the margin everywhere they're shown
      if ("margin" in changed) revalidateTag("products", "max");
    }
    return ok({ message: "saved", changed });
  } catch (e) {
    return failedAction(g.admin, "settings.save", "settings", e, g.ip);
  }
}
