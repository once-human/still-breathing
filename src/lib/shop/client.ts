"use client";

import { useSyncExternalStore } from "react";
import { SHOP, priceOf } from "@/content/shop";
import { DESIGNS, SIZE_ORDER, type Design, type Size } from "@/content/tee";
import type { BagItem, PayView } from "./types";

/**
 * The page's side of the shop: one store shared by every buy button, the bag button, the drawer and checkout. The
 * bag lives in this browser (which shirt, which size, how many) and works whether or not payment is connected;
 * prices come from content/shop.ts, the same numbers the server charges when the bag is paid for.
 */
type State = { pay: PayView | null; bag: BagItem[]; drawer: boolean };

const STORE = "sahn:bag";
let state: State = { pay: null, bag: [], drawer: false };
const subs = new Set<() => void>();
const set = (p: Partial<State>, keep = true) => {
  state = { ...state, ...p };
  if (p.bag && keep) {
    try {
      localStorage.setItem(STORE, JSON.stringify(p.bag));
    } catch {
      /* private mode: the bag lasts the visit */
    }
  }
  subs.forEach((f) => f());
};

const read = (): BagItem[] => {
  try {
    const v = JSON.parse(localStorage.getItem(STORE) ?? "[]");
    return Array.isArray(v) ? fit(v) : [];
  } catch {
    return [];
  }
};

let started = false;
function start() {
  if (started || typeof window === "undefined") return;
  started = true;
  set({ bag: read() }, false);
  fetch("/api/shop/catalog")
    .then((r) => r.json() as Promise<PayView>)
    .catch((): PayView => ({ pay: false, payable: {} }))
    .then((pay) => set({ pay }));
  // another tab changed the bag (or paid for it)
  window.addEventListener("storage", (e) => { if (e.key === STORE) set({ bag: read() }, false); });
}

/** keep only real shirts and sizes, within the limits */
function fit(bag: BagItem[]): BagItem[] {
  let left = SHOP.maxPerBag;
  const out: BagItem[] = [];
  for (const l of bag) {
    if (!l || !Object.hasOwn(DESIGNS, l.design) || !(SIZE_ORDER as readonly string[]).includes(l.size) || !Number.isInteger(l.quantity) || l.quantity < 1) continue;
    const q = Math.min(l.quantity, SHOP.maxPerLine, left);
    if (q < 1) break;
    left -= q;
    out.push({ design: l.design, size: l.size, quantity: q });
  }
  return out;
}

const subscribe = (f: () => void) => {
  subs.add(f);
  start();
  return () => subs.delete(f);
};

function put(design: Design, size: Size) {
  const bag = [...state.bag];
  const l = bag.find((x) => x.design === design && x.size === size);
  if (l) bag.splice(bag.indexOf(l), 1, { ...l, quantity: l.quantity + 1 });
  else bag.push({ design, size, quantity: 1 });
  return fit(bag);
}

export const shop = {
  /** into the bag, and the bag opens */
  add: (design: Design, size: Size) => set({ bag: put(design, size), drawer: true }),
  /** into the bag without opening it (buy now goes straight on to checkout) */
  addQuietly: (design: Design, size: Size) => set({ bag: put(design, size) }),
  setQuantity: (design: Design, size: Size, quantity: number) =>
    set({ bag: fit(state.bag.map((x) => (x.design === design && x.size === size ? { ...x, quantity } : x)).filter((x) => x.quantity > 0)) }),
  /** a past order's shirts back in the bag (reorder), on top of what's there */
  addLines: (lines: BagItem[]) => {
    const bag = [...state.bag];
    for (const l of lines) {
      const x = bag.find((y) => y.design === l.design && y.size === l.size);
      if (x) bag.splice(bag.indexOf(x), 1, { ...x, quantity: x.quantity + l.quantity });
      else bag.push({ design: l.design, size: l.size, quantity: l.quantity });
    }
    set({ bag: fit(bag) });
  },
  empty: () => set({ bag: [] }),
  open: () => set({ drawer: true }),
  close: () => set({ drawer: false }),
};

const SERVER: State = { pay: null, bag: [], drawer: false };
export const useShop = () => useSyncExternalStore(subscribe, () => state, () => SERVER);

/** a shirt's price as the server charges it now (the code's rule until the catalog has answered) */
export const priceIn = (p: PayView | null, d: Design) => p?.prices?.[d] ?? priceOf(d);
export const bagTotal = (bag: BagItem[], p: PayView | null) => bag.reduce((t, l) => t + priceIn(p, l.design) * l.quantity, 0);
export const bagCount = (bag: BagItem[]) => bag.reduce((t, l) => t + l.quantity, 0);
/** whether every line of this bag can be paid for right now */
export const bagPayable = (bag: BagItem[], p: PayView | null) => !!p?.pay && bag.length > 0 && bag.every((l) => p.payable[l.design]?.includes(l.size));
/** a size this shirt can't be bought in while payment is on (no partner SKU for it); never true while it's off */
export const notMade = (p: PayView | null, design: Design, size: Size) => !!p?.pay && !p.payable[design]?.includes(size);

/** Only one drawer on the page: the earliest mounted shop control still on the page hosts it; when that one goes
 *  (leaving a shirt page), the next one takes over, so the header's bag still opens. */
const hosts: { me: symbol; tell: (mine: boolean) => void }[] = [];
const retell = () => hosts.forEach((h, i) => h.tell(i === 0));
export const claimDrawer = (me: symbol, tell: (mine: boolean) => void) => { hosts.push({ me, tell }); retell(); };
export const releaseDrawer = (me: symbol) => {
  const i = hosts.findIndex((h) => h.me === me);
  if (i >= 0) hosts.splice(i, 1);
  retell();
};
