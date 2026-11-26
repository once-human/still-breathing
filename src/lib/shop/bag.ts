import { cookies, headers } from "next/headers";
import { SHOP } from "@/content/shop";
import { DESIGNS, type Design, type Size } from "@/content/tee";
import { shopOpen } from "./config";
import { clientIp } from "./guard";
import { designOfHandle, getCatalog, sizeOf } from "./catalog";
import { ShopError, storefront, userErrors } from "./storefront";
import { EMPTY_BAG, type BagView } from "./types";

/**
 * The bag is a Shopify cart. Its ID carries a secret key (Shopify: treat it like a password), so it lives only in an
 * httpOnly cookie the page's scripts can't read, and the browser only ever names a shirt and a size. Shopify works
 * out every price and total; nothing the browser sends is a price.
 */
const COOKIE = process.env.NODE_ENV === "production" ? "__Host-sb_bag" : "sb_bag";
const TEN_DAYS = 60 * 60 * 24 * 10;

const LINES = `
  id
  checkoutUrl
  totalQuantity
  cost { subtotalAmount { amount currencyCode } }
  lines(first: 30) {
    nodes {
      id
      quantity
      cost { totalAmount { amount } }
      merchandise { ... on ProductVariant { id selectedOptions { name value } product { handle } } }
    }
  }`;

type Line = { id: string; quantity: number; cost: { totalAmount: { amount: string } }; merchandise: { id: string; selectedOptions: { name: string; value: string }[]; product: { handle: string } } };
type Cart = { id: string; checkoutUrl: string; totalQuantity: number; cost: { subtotalAmount: { amount: string } }; lines: { nodes: Line[] } };
type Mut = { cart: Cart | null; userErrors: { message: string; code?: string | null }[] };

/** the visitor's IP as Vercel saw it, for Shopify's buyer-traffic header and our rate limit */
export async function buyerIp() {
  return clientIp(await headers());
}

async function cartId() {
  const v = (await cookies()).get(COOKIE)?.value;
  return v && v.startsWith("gid://shopify/Cart/") && v.length < 300 ? v : null;
}

async function keep(id: string | null) {
  const jar = await cookies();
  if (!id) return void jar.delete(COOKIE);
  jar.set(COOKIE, id, { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/", maxAge: TEN_DAYS });
}

function view(cart: Cart | null): BagView {
  if (!cart) return { ...EMPTY_BAG, open: true };
  const lines: BagView["lines"] = [];
  for (const l of cart.lines.nodes) {
    const design = designOfHandle(l.merchandise.product.handle), size = sizeOf(l.merchandise.selectedOptions);
    if (!design || !size) continue;
    const d = DESIGNS[design];
    lines.push({ id: `${design}-${size}`, design, size, name: `${d.no} ${d.name}${d.city ? ` ${d.city}` : ""}`, quantity: l.quantity, total: Number(l.cost.totalAmount.amount) });
  }
  return { open: true, lines, count: cart.totalQuantity, subtotal: Number(cart.cost.subtotalAmount.amount) };
}

async function fetchCart(id: string, ip: string | null): Promise<Cart | null> {
  const r = await storefront<{ cart: Cart | null }>(`query Bag($id: ID!) { cart(id: $id) { ${LINES} } }`, { id }, { buyerIp: ip });
  return r.cart;
}

/** the bag as it stands; a bag Shopify no longer knows (bought, or expired) is simply empty */
export async function readBag(): Promise<BagView> {
  if (!shopOpen()) return EMPTY_BAG;
  const id = await cartId();
  if (!id) return view(null);
  const cart = await fetchCart(id, await buyerIp());
  if (!cart) await keep(null);
  return view(cart);
}

async function variantFor(design: Design, size: Size) {
  const v = (await getCatalog())[design]?.sizes[size];
  if (!v) throw new ShopError("not sold in that size", 404);
  if (!v.available) throw new ShopError("sold out in that size", 409);
  return v.id;
}

/** put `quantity` of a shirt in a size in the bag (add: on top of what's there; set: exactly; 0 takes it out) */
export async function changeBag(op: "add" | "set", design: Design, size: Size, quantity: number): Promise<BagView> {
  if (!shopOpen()) throw new ShopError("shop closed", 503);
  const ip = await buyerIp();
  const id = await cartId();
  const cart = id ? await fetchCart(id, ip) : null;
  const merchandiseId = await variantFor(design, size).catch((e) => {
    // taking a sold-out size out of the bag must still work
    if (op === "set" && quantity === 0) return null;
    throw e;
  });
  const line = cart?.lines.nodes.find((l) => designOfHandle(l.merchandise.product.handle) === design && sizeOf(l.merchandise.selectedOptions) === size);
  const now = line?.quantity ?? 0;
  const want = op === "add" ? now + quantity : quantity;
  if (want > SHOP.maxPerLine) throw new ShopError(`at most ${SHOP.maxPerLine} of one shirt in one size`, 409);
  if ((cart?.totalQuantity ?? 0) - now + want > SHOP.maxPerBag) throw new ShopError(`at most ${SHOP.maxPerBag} shirts in a bag`, 409);

  let next: Cart | null;
  if (!cart) {
    if (want === 0 || !merchandiseId) return view(null);
    const r = await storefront<{ cartCreate: Mut }>(
      `mutation New($input: CartInput!) { cartCreate(input: $input) { cart { ${LINES} } userErrors { message code } } }`,
      { input: { lines: [{ merchandiseId, quantity: want }], buyerIdentity: { countryCode: "IN" } } },
      { buyerIp: ip },
    );
    userErrors(r.cartCreate.userErrors);
    next = r.cartCreate.cart;
  } else if (!line) {
    if (want === 0 || !merchandiseId) return view(cart);
    const r = await storefront<{ cartLinesAdd: Mut }>(
      `mutation Add($id: ID!, $lines: [CartLineInput!]!) { cartLinesAdd(cartId: $id, lines: $lines) { cart { ${LINES} } userErrors { message code } } }`,
      { id: cart.id, lines: [{ merchandiseId, quantity: want }] },
      { buyerIp: ip },
    );
    userErrors(r.cartLinesAdd.userErrors);
    next = r.cartLinesAdd.cart;
  } else if (want === 0) {
    const r = await storefront<{ cartLinesRemove: Mut }>(
      `mutation Remove($id: ID!, $lineIds: [ID!]!) { cartLinesRemove(cartId: $id, lineIds: $lineIds) { cart { ${LINES} } userErrors { message code } } }`,
      { id: cart.id, lineIds: [line.id] },
      { buyerIp: ip },
    );
    userErrors(r.cartLinesRemove.userErrors);
    next = r.cartLinesRemove.cart;
  } else {
    const r = await storefront<{ cartLinesUpdate: Mut }>(
      `mutation Set($id: ID!, $lines: [CartLineUpdateInput!]!) { cartLinesUpdate(cartId: $id, lines: $lines) { cart { ${LINES} } userErrors { message code } } }`,
      { id: cart.id, lines: [{ id: line.id, quantity: want }] },
      { buyerIp: ip },
    );
    userErrors(r.cartLinesUpdate.userErrors);
    next = r.cartLinesUpdate.cart;
  }
  await keep(next?.id ?? null);
  return view(next);
}

/** Shopify's checkout for this bag, asked for fresh at the moment the buyer goes (Shopify: it can go stale) */
export async function checkoutUrl(): Promise<string> {
  if (!shopOpen()) throw new ShopError("shop closed", 503);
  const id = await cartId();
  const cart = id ? await fetchCart(id, await buyerIp()) : null;
  if (!cart || cart.totalQuantity === 0) throw new ShopError("the bag is empty", 409);
  const url = new URL(cart.checkoutUrl);
  // only ever send the buyer to Shopify's own checkout over https (or the checkout domain set for it later)
  const own = process.env.SHOPIFY_CHECKOUT_HOST?.trim().toLowerCase();
  if (url.protocol !== "https:" || !(url.hostname.endsWith(".myshopify.com") || (own && url.hostname === own))) {
    throw new ShopError("checkout address unexpected");
  }
  return url.toString();
}
