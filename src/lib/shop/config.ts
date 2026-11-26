/**
 * The shop's keys, read on the server only. None of these is NEXT_PUBLIC_, so Next never puts them in a browser bundle.
 * The shop is open only when the storefront keys are all there; until then every buy control reads "opening soon".
 */
const env = (k: string) => {
  const v = process.env[k]?.trim();
  return v ? v : undefined;
};

/** a *.myshopify.com host and nothing else, so a typo can't send our tokens anywhere */
const store = () => {
  const d = env("SHOPIFY_STORE_DOMAIN")?.replace(/^https?:\/\//, "").replace(/\/.*$/, "").toLowerCase();
  return d && /^[a-z0-9][a-z0-9-]*\.myshopify\.com$/.test(d) ? d : undefined;
};

export const API_VERSION = "2026-10";

export const storefrontKeys = () => {
  const domain = store(), token = env("SHOPIFY_STOREFRONT_PRIVATE_TOKEN");
  return domain && token ? { domain, token } : null;
};

export const adminKeys = () => {
  const domain = store(), id = env("SHOPIFY_ADMIN_CLIENT_ID"), secret = env("SHOPIFY_ADMIN_CLIENT_SECRET");
  return domain && id && secret ? { domain, id, secret } : null;
};

export const webhookSecret = () => env("SHOPIFY_WEBHOOK_SECRET") ?? null;

/** buying works: products, bag and checkout */
export const shopOpen = () => storefrontKeys() !== null;
/** order pages work */
export const ordersOpen = () => adminKeys() !== null;
