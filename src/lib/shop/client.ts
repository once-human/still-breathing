"use client";

import { useSyncExternalStore } from "react";
import type { Design, Size } from "@/content/tee";
import { EMPTY_BAG, type BagView, type CatalogView } from "./types";

/**
 * The page's side of the shop: one store shared by every buy button, the bag button and the drawer. It only knows
 * what the server tells it (prices, the bag's lines and totals) and only asks for a shirt, a size and a count.
 */
type State = {
  catalog: CatalogView | null;
  bag: BagView;
  busy: boolean;
  error: string | null;
  drawer: boolean;
};

let state: State = { catalog: null, bag: EMPTY_BAG, busy: false, error: null, drawer: false };
const subs = new Set<() => void>();
const set = (p: Partial<State>) => {
  state = { ...state, ...p };
  subs.forEach((f) => f());
};
const subscribe = (f: () => void) => {
  subs.add(f);
  start();
  return () => subs.delete(f);
};

let started = false;
function start() {
  if (started || typeof window === "undefined") return;
  started = true;
  fetch("/api/shop/catalog")
    .then((r) => r.json() as Promise<CatalogView>)
    .catch((): CatalogView => ({ open: false }))
    .then((catalog) => {
      set({ catalog });
      if (catalog.open) refresh();
    });
  // coming back from checkout (the back button, another tab): the bag may have been bought
  window.addEventListener("pageshow", (e) => { if (e.persisted && state.catalog?.open) refresh(); });
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && state.catalog?.open) refresh(); });
}

async function call<T>(url: string, body?: unknown): Promise<T> {
  const r = await fetch(url, body === undefined ? { cache: "no-store" } : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = (await r.json().catch(() => ({}))) as T & { error?: string };
  if (!r.ok) throw new Error(j.error ?? "something went wrong, try again");
  return j;
}

async function refresh() {
  try {
    set({ bag: await call<BagView>("/api/shop/bag") });
  } catch {
    /* the bag stays as it was shown */
  }
}

async function change(op: "add" | "set", design: Design, size: Size, quantity: number) {
  if (state.busy) return false;
  set({ busy: true, error: null });
  try {
    set({ bag: await call<BagView>("/api/shop/bag", { op, design, size, quantity }), busy: false });
    return true;
  } catch (e) {
    set({ busy: false, error: (e as Error).message });
    return false;
  }
}

export const shop = {
  add: async (design: Design, size: Size) => {
    if (await change("add", design, size, 1)) set({ drawer: true });
  },
  setQuantity: (design: Design, size: Size, quantity: number) => change("set", design, size, quantity),
  open: () => set({ drawer: true, error: null }),
  close: () => set({ drawer: false, error: null }),
  checkout: async () => {
    if (state.busy) return;
    set({ busy: true, error: null });
    try {
      const { url } = await call<{ url: string }>("/api/shop/checkout", {});
      window.location.assign(url);
    } catch (e) {
      set({ busy: false, error: (e as Error).message });
    }
  },
};

const server = (): State => ({ catalog: null, bag: EMPTY_BAG, busy: false, error: null, drawer: false });
const SERVER = server();
export const useShop = () => useSyncExternalStore(subscribe, () => state, () => SERVER);

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
