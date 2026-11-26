import { createHmac, timingSafeEqual } from "node:crypto";

/**
 * Shopify signs every webhook: base64 HMAC-SHA256 of the raw body with the store's webhook signing key, in
 * X-Shopify-Hmac-Sha256. Checked over the bytes exactly as they came, compared in constant time.
 */
export function verifyShopify(raw: string, signature: string | null, secret: string) {
  if (!signature) return false;
  const want = createHmac("sha256", secret).update(raw, "utf8").digest();
  let got: Buffer;
  try {
    got = Buffer.from(signature, "base64");
  } catch {
    return false;
  }
  return got.length === want.length && timingSafeEqual(got, want);
}

/** Shopify delivers at least once and retries; each delivery has an id. Seen ids are remembered for a day per
 *  instance. What the webhook does (refreshing the catalog) is harmless to repeat, so a repeat that lands on another
 *  instance is still safe. */
const seen = new Map<string, number>();
export function firstTime(id: string | null) {
  if (!id) return true;
  const now = Date.now();
  if (seen.has(id)) return false;
  seen.set(id, now);
  if (seen.size > 2000) for (const [k, t] of seen) if (now - t > 86_400_000) seen.delete(k);
  return true;
}
