/**
 * The shop's addresses on sahn.in, each one there for a reason: hello for anything, orders for order mail, drops for
 * the new-drop emails (kept apart from order mail, so a spam mark on one never hurts the other), security for sign-in
 * codes and anything about a profile's safety, privacy because the DPDP Act wants a named place for data requests,
 * and direct, straight to the top (the person who started sahn, however many people work on it), for what nobody
 * else has put right, and onkar, the owner's own address (quick replies from gmail go out from it). Mail to any of them comes in through Resend (sahn.in's MX), lands in the admin's email inbox and
 * is copied to the owner; it goes out through Resend from the domain it has verified.
 */
export const MAIL_DOMAIN = "sahn.in";

export const BOXES = {
  hello: { name: "sahn", use: "anything: a size, a question, press, stockists" },
  orders: { name: "sahn orders", use: "order emails, and help with an order" },
  drops: { name: "sahn drops", use: "new drop emails, for those who asked" },
  security: { name: "sahn security", use: "sign-in codes, a password or device changed, admin alerts" },
  privacy: { name: "sahn privacy", use: "your data: a copy, a fix, or erasing it" },
  direct: { name: "sahn", use: "straight to the top, for what nothing else has put right" },
  onkar: { name: "Onkar from sahn", use: "your own address: a reply from your gmail goes out from here" },
} as const;

/** the owner's own box: a reply written in gmail to an inbox copy goes to the customer from here */
export const OWNER_BOX: Box = "onkar";

export type Box = keyof typeof BOXES;

/** the address, e.g. orders@sahn.in */
export const box = (b: Box) => `${b}@${MAIL_DOMAIN}`;
