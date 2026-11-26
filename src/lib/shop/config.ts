/**
 * The shop's keys, read on the server only. None is NEXT_PUBLIC_, so none can end up in a browser bundle (the
 * payment page's public key ID is handed to the page by the server, at checkout, and it is public by design).
 * The shop is open only when every service an order passes through is set up: payment, the order store, the print
 * partner, email and the link secret. Until then no buy control is drawn at all.
 */
const env = (k: string) => {
  const v = process.env[k]?.trim();
  return v ? v : undefined;
};

export const razorpayKeys = () => {
  const id = env("RAZORPAY_KEY_ID"), secret = env("RAZORPAY_KEY_SECRET"), webhook = env("RAZORPAY_WEBHOOK_SECRET");
  return id && secret && webhook && /^rzp_(test|live)_[A-Za-z0-9]+$/.test(id) ? { id, secret, webhook, test: id.startsWith("rzp_test_") } : null;
};

/** the print partner's custom-store API; QIKINK_SANDBOX=1 sends orders to its sandbox */
export const partnerKeys = () => {
  const id = env("QIKINK_CLIENT_ID"), secret = env("QIKINK_CLIENT_SECRET");
  const sandbox = env("QIKINK_SANDBOX") === "1";
  return id && secret ? { id, secret, sandbox, base: sandbox ? "https://sandbox.qikink.com" : "https://api.qikink.com" } : null;
};

/** Upstash Redis over REST (the Vercel Marketplace integration sets the KV_ names; Upstash's own names work too) */
export const kvKeys = () => {
  const url = env("KV_REST_API_URL") ?? env("UPSTASH_REDIS_REST_URL"), token = env("KV_REST_API_TOKEN") ?? env("UPSTASH_REDIS_REST_TOKEN");
  return url && token && url.startsWith("https://") ? { url, token } : null;
};

export const mailKeys = () => {
  const key = env("RESEND_API_KEY"), from = env("SHOP_EMAIL_FROM");
  return key && from ? { key, from } : null;
};

/** signs order links and authorises the sync job; at least 32 characters */
export const shopSecret = () => {
  const s = env("SHOP_SECRET");
  return s && s.length >= 32 ? s : null;
};

/** where Onkar hears about anything the shop couldn't do by itself (an order the partner refused, say) */
export const ownerEmail = () => env("SHOP_OWNER_EMAIL") ?? null;

export const shopOpen = () => !!(razorpayKeys() && partnerKeys() && kvKeys() && mailKeys() && shopSecret());
