"use client";
// Which show the page is talking about. A city shirt speaks for its own city everywhere on the page
// (countdown, the sky, the nav); a lineup-wide shirt speaks for the show nearest the visitor.
import { useSyncExternalStore } from "react";

let focus: string | null = null;   // the shirt's city, null for a lineup-wide shirt
let near: string | null = null;    // nearest show to the visitor, city-level, asked once
let asked = false;
const subs = new Set<() => void>();
const emit = () => subs.forEach((f) => f());

export function setFocusCity(city: string | null) {
  if (city === focus) return;
  focus = city; emit();
  if (!city && !asked) {
    asked = true;
    fetch("/api/near").then((r) => r.json()).then((j: { city: string | null }) => { near = j.city; emit(); }).catch(() => {});
  }
}

const subscribe = (f: () => void) => { subs.add(f); return () => subs.delete(f); };
const snap = () => focus ?? near;
/** the show city the page is about, or null (no shirt picked and no location: fall back to the next show) */
export function useShowCity() { return useSyncExternalStore(subscribe, snap, () => null); }
