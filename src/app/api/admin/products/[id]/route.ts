import { revalidateTag } from "next/cache";
import { audit } from "@/lib/admin/auth";
import { adminWrite, failedAction, ok } from "@/lib/admin/guard";
import { PRODUCTS_TAG, productById, saveProduct, type Product } from "@/lib/shop/products";

export const dynamic = "force-dynamic";

/** what the admin may change; qikink's cost and the SKUs are qikink's facts, set from its dashboard in code, never here */
const FIELDS = ["status", "margin", "fixedPrice", "name", "about", "sort"] as const;
/** the words are shown on every page, so they're checked here before the shop saves them */
const TEXT: Record<string, number> = { name: 60, about: 600 };

/** a shirt's changes, through the shop's saveProduct (which checks each field); from → to in the audit log */
export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const g = await adminWrite(req);
  if ("fail" in g) return g.fail;
  const { id } = await params;
  const before = await productById(id);
  if (!before) return ok({ error: "no such shirt" }, 404);
  const patch: Record<string, unknown> = {};
  for (const k of FIELDS) if (k in g.body) patch[k] = g.body[k];
  if (!Object.keys(patch).length) return ok({ error: "nothing to change" }, 400);
  for (const [k, max] of Object.entries(TEXT)) {
    if (!(k in patch)) continue;
    const v = typeof patch[k] === "string" ? (patch[k] as string).replace(/[\u0000-\u001f<>]/g, " ").replace(/\s+/g, " ").trim() : "";
    if (!v || v.length > max) return ok({ error: `${k}: 1 to ${max} characters` }, 400);
    patch[k] = v;
  }
  if ("sort" in patch && !(Number.isInteger(patch.sort) && (patch.sort as number) >= 0 && (patch.sort as number) <= 999)) return ok({ error: "order: a whole number, 0 to 999" }, 400);
  try {
    const after = await saveProduct(before.id, patch as Partial<Product>, g.admin.email);
    const changed = Object.fromEntries(Object.keys(patch).map((k) => [k, [before[k as keyof Product], after?.[k as keyof Product]]]));
    if (before.price !== after?.price) changed.price = [before.price, after?.price];
    await audit(g.admin.email, "product.save", `product:${before.id}`, changed, g.ip);
    revalidateTag(PRODUCTS_TAG, "max");
    return ok({ message: "saved", price: after?.price });
  } catch (e) {
    return failedAction(g.admin, "product.save", `product:${before.id}`, e, g.ip);
  }
}
