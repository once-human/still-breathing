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

/** the order store: Postgres on Neon (DATABASE_URL, or POSTGRES_URL as Vercel's Neon integration names it) */
export const kvKeys = () => {
  const url = env("DATABASE_URL") ?? env("POSTGRES_URL");
  if (!url || !/^postgres(ql)?:\/\//.test(url)) return null;
  try {
    return { url, host: new URL(url).hostname };
  } catch {
    return null;
  }
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

/** accounts need only the store, email and the secret (no payment): sign in, profile, addresses, order history */
export const accountsOpen = () => !!(kvKeys() && mailKeys() && shopSecret());

export const shopOpen = () => !!(razorpayKeys() && partnerKeys() && kvKeys() && mailKeys() && shopSecret());

/** Google sign-in: an OAuth client from Google Cloud (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET); the button shows only with both */
export const googleKeys = () => {
  const id = env("GOOGLE_CLIENT_ID"), secret = env("GOOGLE_CLIENT_SECRET");
  return id && secret ? { id, secret } : null;
};
