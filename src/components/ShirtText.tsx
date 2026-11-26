"use client";

import { createContext, useContext } from "react";
import { DESIGNS, type Design } from "@/content/tee";
import { CURRENT, shirtsOf } from "@/content/lineups";

/**
 * The shirts' names and words as the admin's catalog has them, handed down once from the root layout so the client
 * parts (the header's shelf, the shirt page) say the same as the server-drawn ones. Falls back to the code.
 */
export type ShirtTexts = { order: Design[]; text: Record<Design, { name: string; about: string }> };

const Ctx = createContext<ShirtTexts | null>(null);

export function ShirtTextProvider({ value, children }: { value: ShirtTexts; children: React.ReactNode }) {
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useShirtText() {
  const v = useContext(Ctx);
  const name = (d: Design) => v?.text[d]?.name ?? DESIGNS[d].name;
  const city = (d: Design) => DESIGNS[d].city;
  return {
    /** the shirts on show, in the admin's order (no drafts) */
    order: v?.order ?? shirtsOf(CURRENT),
    shown: (d: Design) => (v ? v.order.includes(d) : true),
    name,
    about: (d: Design) => v?.text[d]?.about ?? DESIGNS[d].about,
    title: (d: Design) => ({ top: `again.. ${city(d) ?? "india"}`, name: name(d) }),
    label: (d: Design) => `${name(d)}${city(d) ? `, ${city(d)}` : ""}`,
  };
}
