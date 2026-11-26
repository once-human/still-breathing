import { changeBag, readBag } from "@/lib/shop/bag";
import { failed, guardWrite, ipOf, json, limited } from "@/lib/shop/guard";
import { DESIGNS, SIZE_ORDER, type Design, type Size } from "@/content/tee";

export const dynamic = "force-dynamic";

/** this visitor's bag, from their cookie */
export async function GET(req: Request) {
  if (limited(`bag-read:${ipOf(req)}`, 60, 60_000)) return json({ error: "too many tries, wait a minute" }, 429);
  try {
    return json(await readBag());
  } catch (e) {
    return failed(e);
  }
}

/**
 * { op: "add" | "set", design, size, quantity }: the only thing the browser can say. No IDs, no prices: the server
 * looks the shirt up in Shopify and Shopify prices the bag.
 */
export async function POST(req: Request) {
  const g = await guardWrite(req, "bag", 30);
  if ("fail" in g) return g.fail;
  const b = g.body as Record<string, unknown>;
  const op = b?.op, design = b?.design, size = b?.size, quantity = b?.quantity;
  if ((op !== "add" && op !== "set") || typeof design !== "string" || !Object.hasOwn(DESIGNS, design) || typeof size !== "string" || !(SIZE_ORDER as readonly string[]).includes(size)
    || typeof quantity !== "number" || !Number.isInteger(quantity) || quantity < (op === "add" ? 1 : 0) || quantity > 10) {
    return json({ error: "bad request" }, 400);
  }
  try {
    return json(await changeBag(op, design as Design, size as Size, quantity));
  } catch (e) {
    return failed(e);
  }
}
