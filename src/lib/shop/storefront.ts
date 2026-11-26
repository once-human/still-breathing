import { API_VERSION, storefrontKeys } from "./config";

export class ShopError extends Error {
  constructor(message: string, readonly status = 502) {
    super(message);
  }
}

type GqlOpts = {
  /** the buyer's IP, for calls made on a buyer's behalf (Shopify counts them as buyer traffic, not as a bot) */
  buyerIp?: string | null;
  /** cache the answer for this many seconds under these tags; buyer calls are never cached */
  cache?: { revalidate: number; tags: string[] };
};

/**
 * One Storefront API call from the server with the private token. The token, the cart's secret key and the raw
 * answer stay here; callers turn the answer into the plain views the browser gets.
 */
export async function storefront<T>(query: string, variables: Record<string, unknown> = {}, opts: GqlOpts = {}): Promise<T> {
  const keys = storefrontKeys();
  if (!keys) throw new ShopError("shop closed", 503);
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Shopify-Storefront-Private-Token": keys.token,
  };
  if (opts.buyerIp) headers["Shopify-Storefront-Buyer-IP"] = opts.buyerIp;
  let res: Response;
  try {
    res = await fetch(`https://${keys.domain}/api/${API_VERSION}/graphql.json`, {
      method: "POST",
      headers,
      body: JSON.stringify({ query, variables }),
      signal: AbortSignal.timeout(8000),
      ...(opts.cache ? { next: opts.cache } : { cache: "no-store" as const }),
    });
  } catch {
    throw new ShopError("shop unreachable");
  }
  if (!res.ok) throw new ShopError(`storefront ${res.status}`, res.status === 429 ? 429 : 502);
  const json = (await res.json()) as { data?: T; errors?: { message: string; extensions?: { code?: string } }[] };
  if (json.errors?.length) {
    const throttled = json.errors.some((e) => e.extensions?.code === "THROTTLED");
    throw new ShopError(throttled ? "busy" : `storefront: ${json.errors[0].message}`, throttled ? 429 : 502);
  }
  if (!json.data) throw new ShopError("storefront: empty answer");
  return json.data;
}

/** user errors from a cart mutation: Shopify's own reasons (sold out, quantity) */
export const userErrors = (errs: { message: string; code?: string | null }[] | undefined) => {
  if (errs?.length) throw new ShopError(errs[0].message.toLowerCase(), 409);
};
