/**
 * The shop's addresses on sahn.in, one for each kind of email, so a reader knows from the sender what an email is
 * before opening it, and a reply lands where it belongs. The ones people write to (hello, orders, drops) read like a
 * small label talking; the ones that guard things (signin, security, privacy) read like a shop that takes care of
 * them. Every address goes to the same inbox: sahn.in's mail is forwarded by Cloudflare Email Routing (a catch-all),
 * and sent through Resend from the domain it has verified.
 */
export const MAIL_DOMAIN = "sahn.in";

export const BOXES = {
  hello: { name: "sahn", use: "anything: a size, a question, a hello" },
  orders: { name: "sahn orders", use: "order emails, and help with an order" },
  drops: { name: "sahn drops", use: "new drop emails, for those who asked" },
  signin: { name: "sahn sign-in", use: "sign-in codes" },
  security: { name: "sahn security", use: "a sign-in, a password or a device changed; admin alerts" },
  privacy: { name: "sahn privacy", use: "your data: a copy, a fix, or erasing it" },
  collab: { name: "sahn collab", use: "press, stockists, working together" },
} as const;

export type Box = keyof typeof BOXES;

/** the address, e.g. orders@sahn.in */
export const box = (b: Box) => `${b}@${MAIL_DOMAIN}`;
