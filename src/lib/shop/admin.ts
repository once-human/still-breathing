import { adminKeys, API_VERSION } from "./config";
import { ShopError } from "./storefront";

/**
 * The Admin API, for reading orders (the order page) and nothing else: the Dev Dashboard app's scopes are
 * read_orders, read_fulfillments, read_products. Its client ID and secret are swapped for a token (client credentials
 * grant, good for about 24 h) that lives only in this server's memory and is renewed before it runs out.
 */
let token: { value: string; until: number } | null = null;
let pending: Promise<string> | null = null;

async function accessToken(): Promise<string> {
  const keys = adminKeys();
  if (!keys) throw new ShopError("orders closed", 503);
  if (token && Date.now() < token.until) return token.value;
  pending ??= (async () => {
    try {
      const res = await fetch(`https://${keys.domain}/admin/oauth/access_token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ grant_type: "client_credentials", client_id: keys.id, client_secret: keys.secret }),
        cache: "no-store",
        signal: AbortSignal.timeout(8000),
      });
      if (!res.ok) throw new ShopError(`admin token ${res.status}`);
      const j = (await res.json()) as { access_token?: string; expires_in?: number };
      if (!j.access_token) throw new ShopError("admin token missing");
      // renew ten minutes early; if Shopify gives no lifetime, assume the shortest it gives (24 h)
      token = { value: j.access_token, until: Date.now() + Math.max(60, (j.expires_in ?? 86_400) - 600) * 1000 };
      return token.value;
    } finally {
      pending = null;
    }
  })();
  return pending;
}

export async function admin<T>(query: string, variables: Record<string, unknown> = {}): Promise<T> {
  const keys = adminKeys();
  if (!keys) throw new ShopError("orders closed", 503);
  const go = async () =>
    fetch(`https://${keys.domain}/admin/api/${API_VERSION}/graphql.json`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Shopify-Access-Token": await accessToken() },
      body: JSON.stringify({ query, variables }),
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });
  let res = await go().catch(() => null);
  if (res?.status === 401) {
    token = null; // revoked or rotated: get a new one once
    res = await go().catch(() => null);
  }
  if (!res) throw new ShopError("admin unreachable");
  if (!res.ok) throw new ShopError(`admin ${res.status}`, res.status === 429 ? 429 : 502);
  const json = (await res.json()) as { data?: T; errors?: { message: string }[] };
  if (json.errors?.length) throw new ShopError(`admin: ${json.errors[0].message}`);
  if (!json.data) throw new ShopError("admin: empty answer");
  return json.data;
}
