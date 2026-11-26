import { signOut } from "@/lib/admin/auth";
import { adminWrite, ok } from "@/lib/admin/guard";

export const dynamic = "force-dynamic";

/** { signOut: true, all?: true }: end this session, or every session */
export async function POST(req: Request) {
  const g = await adminWrite(req);
  if ("fail" in g) return g.fail;
  await signOut(g.body.all === true);
  return ok({ ok: true });
}
