"use client";

import { useEffect, useSyncExternalStore } from "react";
import type { Design, Size } from "@/content/tee";

/**
 * Who's here, for the header and the shirt pages: signed in or not, the first name, their size and their saved
 * shirts. Asked of the server only when the plain "signed in" hint cookie says there's a session, once per page
 * change at most, and shared by everything on the page. Signed out, a size picked is remembered in this browser.
 */
export type Me = { signedIn: boolean; name: string; size: Size | null; saved: Design[] };
const NONE: Me = { signedIn: false, name: "", size: null, saved: [] };
const LOCAL_SIZE = "sahn:size";

let me: Me = NONE;
let asked = "";
const subs = new Set<() => void>();
const set = (m: Me) => { me = m; subs.forEach((f) => f()); };
const hinted = () => /(?:^|;\s*)sahn_in=1/.test(document.cookie);
const localSize = () => { try { return (localStorage.getItem(LOCAL_SIZE) as Size | null) ?? null; } catch { return null; } };

export function refreshMe(key = String(Date.now())) {
  if (asked === key) return;
  asked = key;
  if (!hinted()) return set({ ...NONE, size: localSize() });
  fetch("/api/shop/account", { cache: "no-store" })
    .then((r) => r.json() as Promise<Partial<Me>>)
    .then((j) => set(j.signedIn ? { signedIn: true, name: j.name ?? "", size: j.size ?? localSize(), saved: j.saved ?? [] } : { ...NONE, size: localSize() }))
    .catch(() => {});
}

/** the shared "me", refreshed when `key` (the page's path) changes */
export function useMe(key: string) {
  useEffect(() => refreshMe(key), [key]);
  return useSyncExternalStore((f) => { subs.add(f); return () => subs.delete(f); }, () => me, () => NONE);
}

/** a size picked on a shirt: kept in this browser, and the next shirt opens on it */
export function pickedSize(z: Size) {
  try { localStorage.setItem(LOCAL_SIZE, z); } catch {}
}

/** save or unsave a shirt (signed in only); shown at once, put right if the server says no */
export async function toggleSaved(d: Design) {
  const was = me.saved.includes(d);
  set({ ...me, saved: was ? me.saved.filter((x) => x !== d) : [d, ...me.saved] });
  const r = await fetch("/api/shop/account", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "save", design: d, on: !was }) }).catch(() => null);
  if (!r?.ok) set({ ...me, saved: was ? [d, ...me.saved.filter((x) => x !== d)] : me.saved.filter((x) => x !== d) });
}
