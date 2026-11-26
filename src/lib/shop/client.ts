"use client";

import { useSyncExternalStore } from "react";
import type { Design, Size } from "@/content/tee";
import type { BagItem, CatalogView } from "./types";

/**
 * The page's side of the shop: one store shared by every buy button, the bag button, the drawer and checkout. The
 * bag lives in this browser (which shirt, which size, how many); prices come from the server, and the server prices
 * the bag again when it's paid for.
 */
type State = { catalog: CatalogView | null; bag: BagItem[]; drawer: boolean };

const STORE = "sahn:bag";
let state: State = { catalog: null, bag: [], drawer: false };
const subs = new Set<() => void>();
const set = (p: Partial<State>) => {
  state = { ...state, ...p };
  if (p.bag) {
    try {
      localStorage.setItem(STORE, JSON.stringify(p.bag));
    } catch {
      /* private mode: the bag lasts the visit */
    }
  }
  subs.forEach((f) => f());
};

let started = false;
function start() {
  if (started || typeof window === "undefined") return;
  started = true;
  let saved: BagItem[] = [];
  try {
    saved = JSON.parse(localStorage.getItem(STORE) ?? "[]");
  } catch {
    /* nothing kept */
  }
  fetch("/api/shop/catalog")
    .then((r) => r.json() as Promise<CatalogView>)
    .catch((): CatalogView => ({ open: false }))
    // a shop that can't be reached right now leaves the kept bag alone for next time
    .then((catalog) => (catalog.open ? set({ catalog, bag: fit(Array.isArray(saved) ? saved : [], catalog) }) : set({ catalog })));
  // another tab changed the bag (or paid for it)
  window.addEventListener("storage", (e) => {
    if (e.key === STORE && state.catalog) {
      try {
        state = { ...state, bag: fit(JSON.parse(e.newValue ?? "[]"), state.catalog) };
        subs.forEach((f) => f());
      } catch {
        /* ignore */
      }
    }
  });
}

/** keep only lines that can still be bought, within the limits */
function fit(bag: BagItem[], c: CatalogView): BagItem[] {
  if (!c.open) return [];
  let left = c.maxPerBag;
  const out: BagItem[] = [];
  for (const l of bag) {
    const s = c.shirts[l?.design as Design];
    if (!s || !s.sizes.includes(l.size) || !Number.isInteger(l.quantity) || l.quantity < 1) continue;
    const q = Math.min(l.quantity, c.maxPerLine, left);
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

export const shop = {
  add: (design: Design, size: Size) => {
    if (!state.catalog?.open) return;
    const bag = [...state.bag];
    const l = bag.find((x) => x.design === design && x.size === size);
    if (l) bag.splice(bag.indexOf(l), 1, { ...l, quantity: l.quantity + 1 });
    else bag.push({ design, size, quantity: 1 });
    set({ bag: fit(bag, state.catalog), drawer: true });
  },
  setQuantity: (design: Design, size: Size, quantity: number) => {
    if (!state.catalog?.open) return;
    const bag = state.bag.map((x) => (x.design === design && x.size === size ? { ...x, quantity } : x)).filter((x) => x.quantity > 0);
    set({ bag: fit(bag, state.catalog) });
  },
  empty: () => set({ bag: [] }),
  open: () => set({ drawer: true }),
  close: () => set({ drawer: false }),
};

const SERVER: State = { catalog: null, bag: [], drawer: false };
export const useShop = () => useSyncExternalStore(subscribe, () => state, () => SERVER);

/** what the bag comes to at the server's prices (the charge itself is worked out again on the server) */
export const bagTotal = (bag: BagItem[], c: CatalogView | null) =>
  c?.open ? bag.reduce((t, l) => t + (c.shirts[l.design]?.price ?? 0) * l.quantity, 0) : 0;
export const bagCount = (bag: BagItem[]) => bag.reduce((t, l) => t + l.quantity, 0);

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
