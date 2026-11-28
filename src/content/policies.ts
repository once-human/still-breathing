import { SHOP } from "@/content/shop";

/**
 * The shop's policies: shipping, returns and refunds, terms, privacy, contact. The facts follow how the shirts are
 * really made and sent (made to order, printed in 1–5 days, dispatched in 2–3, 2–7 days on the road; faults
 * reported within 7 days with an unboxing video) and the payment gateway's activation checks (it reads these pages).
 * The site-pages session draws them at /policies/<slug>; this file only holds the words.
 *
 * How to reach the shop is Onkar's to give. The pages go up once there's a real email to write to. The person behind
 * sahn and their city stay off the site for now (Onkar, 2026-11-26: sahn is to be a brand, not his name): with no
 * legalName or place the pages speak as sahn, an independent label from india. Never put a place he doesn't run it from.
 */
export const OPERATOR = {
  /** the legal name the shop runs under: a person's full name, or a firm */
  legalName: null as string | null,
  /** the email that answers orders */
  email: "contact@sahn.in" as string | null,
  /** a phone number, or null for none */
  phone: null as string | null,
  /** where the shop is run from, as "city, state" (also where disputes are heard) */
  place: null as string | null,
};

export const POLICIES_READY = !!OPERATOR.email;

/** the day these words last changed, yyyy-mm-dd */
export const POLICIES_UPDATED = "2026-11-27";

export type PolicySlug = "shipping" | "refunds" | "terms" | "privacy" | "contact";
export type Policy = { slug: PolicySlug; title: string; summary: string; sections: { heading: string; body: string[] }[] };

const mail = () => OPERATOR.email ?? "our order email";
const [m0, m1] = SHOP.make, [r0, r1] = SHOP.road;

export const POLICIES: Record<PolicySlug, Policy> = {
  shipping: {
    slug: "shipping",
    title: "shipping",
    summary: `free across ${SHOP.where}. made for you in ${m0}–${m1} days, then ${r0}–${r1} days on the road.`,
    sections: [
      {
        heading: "where we send",
        body: [
          `anywhere in ${SHOP.where} with a pin code a courier reaches. ${SHOP.where === "india" ? "we don't send abroad yet." : "we don't send to other states or abroad yet."}`,
          "shipping is free: the price you see is what you pay, all taxes included.",
        ],
      },
      {
        heading: "how long it takes",
        body: [
          `every shirt is made to order once you've paid. making it (printing, checking and packing) takes ${m0}–${m1} working days.`,
          `then it's ${r0}–${r1} days on the road, depending on your pin code. most of india gets it in about a week and a half from ordering.`,
          "a few remote pin codes are only reached by india post, which takes 3–15 working days and gives less tracking.",
          "these are what usually happens, not promises: couriers, weather and holidays can slow things down. if you want it for a show, order early.",
        ],
      },
      {
        heading: "tracking",
        body: [
          "we email you the courier and a tracking link the moment it leaves, and every step after that. the link in any of our emails opens your order's page, which always shows where it is.",
        ],
      },
      {
        heading: "if it doesn't arrive",
        body: [
          "if the courier hasn't reached you within 20 days of dispatch, write to us: we make it again and send it at no cost, or refund you in full, whichever you'd like.",
          "if a parcel comes back to us because the address was wrong or incomplete, or nobody could be reached at the phone number given, we can send it again once you cover the shipping for the second trip, or refund the shirt less the shipping both ways.",
          "check your address and phone number at checkout: the courier calls before delivering.",
        ],
      },
    ],
  },

  refunds: {
    slug: "refunds",
    title: "returns and refunds",
    summary: "made for you, so no returns for a change of mind. anything wrong with it, we put right.",
    sections: [
      {
        heading: "if something's wrong",
        body: [
          "if your shirt arrives misprinted, damaged, faulty, or isn't the shirt or size you ordered, tell us within 7 days of delivery and we make it right: a new one made and sent free, or a full refund, your choice.",
          `write to ${mail()} with your order number, an unboxing video (from the sealed parcel to the shirt out of it), and clear photos of the problem and of the packaging. the video is how we can show the fault to be ours and fix it fast; without it we may not be able to.`,
          "no need to send the shirt back unless we ask you to. if we do, we arrange and pay for the pickup.",
        ],
      },
      {
        heading: "what isn't a fault",
        body: [
          "each shirt is printed for you, so we can't take it back if you change your mind or it isn't the fit you hoped for. sizes are measured on the garment in the size guide, and fit shows it on a body like yours: please check before ordering.",
          "measurements can differ by up to about 1.5 cm from the size guide, and printed colours can look a little different from a screen. neither counts as a fault.",
          "damage from washing against the care label, wear, or cutting the parcel open with something sharp isn't covered.",
        ],
      },
      {
        heading: "changing your mind before it's made",
        body: [
          "for the first hour after you pay, your order waits before going to print. in that hour you can cancel it yourself on your order's page and be refunded in full, straight away, or fix the address there.",
          `after that it goes to print within a few hours. if you need to cancel or change the size or address then, write to ${mail()} with your order number as soon as you can: if printing hasn't started, we cancel it and refund you in full. once printing has started it can't be cancelled.`,
        ],
      },
      {
        heading: "how refunds are paid",
        body: [
          "refunds go back the way you paid (UPI, card, net banking or wallet), in full, within 2 working days of us agreeing them. your bank then takes 5–7 working days to show the money.",
        ],
      },
    ],
  },

  terms: {
    slug: "terms",
    title: "terms",
    summary: "the agreement between you and us when you buy a shirt.",
    sections: [
      {
        heading: "who we are",
        body: [
          OPERATOR.legalName
            ? `sahn (this site and its shirts) is run by ${OPERATOR.legalName}${OPERATOR.place ? `, from ${OPERATOR.place}` : ""}, india. "we" and "us" here mean them; "you" means whoever buys or uses the site.`
            : `sahn (this site and its shirts) is an independent label from india. "we" and "us" here mean sahn; "you" means whoever buys or uses the site.`,
        ],
      },
      {
        heading: "the shirts",
        body: [
          "every shirt is made to order after you pay: printed for you, in the size you picked. what's shown on the site (the 3D, the renders, fit) is drawn from the real print files and garment measurements, but a screen can't show colour exactly.",
          "lineup 01 is fan made: our own drawings, made by fans for the shows. it isn't affiliated with, sponsored or endorsed by fred again.., the artists, the venues or the shows' promoters. names are used only to say which nights the shirts are about.",
          "the drawings, lettering and everything else on this site are ours. you can share pictures of your shirt and of the site; please don't copy or sell the designs.",
        ],
      },
      {
        heading: "prices and payment",
        body: [
          `prices are in indian rupees and include all taxes and shipping within ${SHOP.where}. each shirt's price is shown on its page, and the price charged is the one at checkout.`,
          "payment is taken by Razorpay, a payment gateway, in its own secure payment window. your UPI, card and bank details go only to it; we never see or store them.",
          "an order is ours to make once the payment is confirmed. if a price is ever shown wrongly or we can't make an order, we tell you and refund it in full.",
          `you can buy at most ${SHOP.maxPerBag} shirts in one order.`,
        ],
      },
      {
        heading: "delivery, returns and refunds",
        body: [
          "how and when shirts are sent, and what happens if something's wrong, are set out in the shipping and the returns and refunds policies, which are part of these terms.",
        ],
      },
      {
        heading: "liability",
        body: [
          "if something goes wrong with an order, the most we owe you is to make it again or refund what you paid for it. nothing here takes away your rights under the Consumer Protection Act, 2019 or any other law that protects you.",
        ],
      },
      {
        heading: "the law",
        body: [
          `these terms are governed by the laws of india. any dispute is for the courts ${OPERATOR.place ? `at ${OPERATOR.place}` : "of india"}, though we'd always rather hear from you first and sort it out.`,
          `we may update these terms; the version on this page when you order is the one that applies to that order. last updated ${POLICIES_UPDATED}.`,
        ],
      },
    ],
  },

  privacy: {
    slug: "privacy",
    title: "privacy",
    summary: "what we know about you, why, and who else sees it. no ads, no trackers.",
    sections: [
      {
        heading: "what we collect",
        body: [
          "when you order: your name, email, phone number, delivery address, what you bought and what you paid. you give these at checkout, and we need them to make and send your shirt.",
          "when you just look: nothing that names you. no ad trackers, no analytics cookies, no third-party pixels.",
          "the site keeps its own visit log, and nobody else sees it: the pages you open, how long each is on screen and how far down you read, whether you came from a link, a search or a post (the site, never who), the kind of device and browser, your rough city from the connection, and the shop steps you take (a size picked, a shirt put in the bag, checkout opened, paid). it isn't tied to your name, your email or your orders. visits from one browser are tied together by a random code that browser makes for itself and keeps in its own storage; it's made from nothing about you, and no cookie and no IP address are kept.",
          "the full log is kept for 90 days, then only daily totals stay. do not track or global privacy control turns it off, and so does the switch at the end of this page, where you can also see everything kept about your browser and delete it at once.",
          "the bag is kept in your own browser (which shirts, which sizes, how many) until you pay or empty it. no cookies are set for it.",
          "if you sign in (with a code we email you, no password), we keep your name, phone and up to five delivery addresses so checkout fills itself in, and one cookie that keeps you signed in while you keep coming back; 90 days away signs you out. your account shows every order placed with your email. you can sign out any time, on one device or all of them, and delete the account yourself from its details: your orders stay on their way and in our records, the account and its addresses go.",
          "to show the nearest show, the site uses the rough city your connection comes from (the hosting service adds it to every request). it's rounded to about 10 km and used once for the distance; only the city's name goes in the visit log.",
        ],
      },
      {
        heading: "who sees it",
        body: [
          "Razorpay processes your payment; your UPI, card or bank details go only to it, never to us. your order is kept in our order store (Neon, on servers in Singapore, reached only over encrypted connections), and our order emails are sent through Resend.",
          "our production partner, who prints, packs and sends your shirt, and the courier who delivers it get your name, address and phone number, only to do that.",
          "we don't sell, rent or share your details with anyone else, or use them for ads.",
        ],
      },
      {
        heading: "what we use it for",
        body: [
          "making and sending your order, emailing you about it (confirmation, dispatch, tracking, delivery) and the sign-in codes you ask for, answering you, and keeping the records indian tax law requires.",
          "we only email you about your orders. if we ever start a newsletter, it will be one you choose to join.",
        ],
      },
      {
        heading: "how long we keep it",
        body: [
          "the visit log: 90 days in full, then daily totals with nothing about any one visit.",
          "order records are kept for as long as GST law requires (about 6 years), then deleted. emails you send us are kept while we're helping you and for a year after.",
        ],
      },
      {
        heading: "your rights",
        body: [
          `under the Digital Personal Data Protection Act, 2023 you can ask what we hold about you, have it corrected, or have it erased (apart from what tax law makes us keep). write to ${mail()}; we answer within 7 days. ${OPERATOR.legalName ? `${OPERATOR.legalName} handles` : "we handle"} these requests and any complaint about how your data is used.`,
          `last updated ${POLICIES_UPDATED}.`,
        ],
      },
    ],
  },

  contact: {
    slug: "contact",
    title: "contact",
    summary: "a person reads every email.",
    sections: [
      {
        heading: "write to us",
        body: [
          `${mail()}: about an order (put its number in), a size, a fault, anything. we answer within 2 working days, usually sooner.`,
          ...(OPERATOR.phone ? [`phone: ${OPERATOR.phone}, 11 am – 7 pm, monday to saturday.`] : []),
        ],
      },
      {
        heading: "your order",
        body: ["every order email has a link to your order's page. or open /order and put in the order number and your email, or sign in at /account to see all your orders."],
      },
      {
        heading: "who runs sahn",
        body: [OPERATOR.legalName ? `${OPERATOR.legalName}${OPERATOR.place ? `, ${OPERATOR.place}` : ""}, india.` : "sahn, an independent label from india. write to us at the address above."],
      },
    ],
  },
};

export const POLICY_ORDER: PolicySlug[] = ["shipping", "refunds", "terms", "privacy", "contact"];
