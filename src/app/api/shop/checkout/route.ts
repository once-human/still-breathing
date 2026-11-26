import { checkoutUrl } from "@/lib/shop/bag";
import { failed, guardWrite, json } from "@/lib/shop/guard";

export const dynamic = "force-dynamic";

/** Where to pay: Shopify's checkout for this visitor's bag, asked for at the moment they go. Payment happens there. */
export async function POST(req: Request) {
  const g = await guardWrite(req, "checkout", 10);
  if ("fail" in g) return g.fail;
  try {
    return json({ url: await checkoutUrl() });
  } catch (e) {
    return failed(e);
  }
}
