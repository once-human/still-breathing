import { SELLS_IN, SHOP } from "@/content/shop";

/** The states and union territories a parcel can go to, as the courier writes them. */
export const STATES = [
  "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chandigarh", "Chhattisgarh",
  "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir",
  "Jharkhand", "Karnataka", "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
  "Mizoram", "Nagaland", "Odisha", "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
  "Uttar Pradesh", "Uttarakhand", "West Bengal",
] as const;

/** the states the shop sends to, in the courier's spelling */
const only = SELLS_IN;
export const SHIP_STATES = only ? STATES.filter((s) => only.includes(s)) : [...STATES];

/** a pin code's first two digits, by state, where a wrong pair is a sure sign of a mistyped state or pin */
const PIN_START: Partial<Record<(typeof STATES)[number], RegExp>> = { Maharashtra: /^4[0-4]/ };

export type Details = { name: string; email: string; phone: string; address1: string; address2: string; city: string; state: string; pin: string };

const clean = (v: unknown, max: number) => (typeof v === "string" ? v.replace(/[\u0000-\u001f\u007f<>]/g, " ").replace(/\s+/g, " ").trim().slice(0, max) : "");

/** the buyer's details, checked the same way in the page and on the server; returns the problem with a field */
export function checkDetails(raw: unknown): { ok: Details } | { field: keyof Details; error: string } {
  const r = (raw ?? {}) as Record<string, unknown>;
  const d: Details = {
    name: clean(r.name, 80),
    email: clean(r.email, 120).toLowerCase(),
    phone: clean(r.phone, 20).replace(/[\s-]/g, "").replace(/^(\+91|0091|91(?=\d{10}$)|0)/, ""),
    address1: clean(r.address1, 120),
    address2: clean(r.address2, 120),
    city: clean(r.city, 60),
    state: clean(r.state, 60),
    pin: clean(r.pin, 6),
  };
  if (d.name.length < 3 || !/\p{L}/u.test(d.name)) return { field: "name", error: "your full name, as the courier should read it" };
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(d.email)) return { field: "email", error: "an email we can send the tracking to" };
  if (!/^[6-9]\d{9}$/.test(d.phone)) return { field: "phone", error: "a 10-digit indian mobile number, for the courier" };
  if (d.address1.length < 5) return { field: "address1", error: "house, flat or building, and street" };
  if (d.city.length < 2) return { field: "city", error: "your city or town" };
  if (!(STATES as readonly string[]).includes(d.state)) return { field: "state", error: "pick your state" };
  if (SELLS_IN && !SELLS_IN.includes(d.state)) return { field: "state", error: `we send only within ${SHOP.where}` };
  if (!/^[1-9]\d{5}$/.test(d.pin)) return { field: "pin", error: "your 6-digit pin code" };
  const start = PIN_START[d.state as (typeof STATES)[number]];
  if (start && !start.test(d.pin)) return { field: "pin", error: `that pin code isn't in ${d.state.toLowerCase()}` };
  return { ok: d };
}
