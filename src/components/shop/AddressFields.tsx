"use client";

import { SHIP_STATES, type Details } from "@/lib/shop/india";

/** where a shirt goes: the same fields at checkout, on the order page (fixing the address) and in the account */
const FIELDS: { k: keyof Details; label: string; auto: string; type?: string; mode?: "numeric" | "tel" | "email"; wide?: boolean; optional?: boolean }[] = [
  { k: "name", label: "full name", auto: "name", wide: true },
  { k: "email", label: "email, for the confirmation and tracking", auto: "email", type: "email", mode: "email", wide: true },
  { k: "phone", label: "mobile, for the courier", auto: "tel-national", type: "tel", mode: "tel", wide: true },
  { k: "address1", label: "house, flat or building, street", auto: "address-line1", wide: true },
  { k: "address2", label: "area, landmark (optional)", auto: "address-line2", wide: true, optional: true },
  { k: "city", label: "city or town", auto: "address-level2" },
  { k: "pin", label: "pin code", auto: "postal-code", mode: "numeric" },
];

export const input = "mt-1 h-12 w-full border border-line bg-transparent px-3 text-[16px] text-ink outline-none focus:border-ink";
export const EMPTY: Details = { name: "", email: "", phone: "", address1: "", address2: "", city: "", state: SHIP_STATES.length === 1 ? SHIP_STATES[0] : "", pin: "" };

export function AddressFields({ d, onChange, bad, email = true }: { d: Details; onChange: (d: Details) => void; bad?: keyof Details; email?: boolean }) {
  const set = (k: keyof Details) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => onChange({ ...d, [k]: e.target.value });
  return (
    <div className="grid grid-cols-2 gap-x-3 gap-y-4">
      {FIELDS.filter((f) => email || f.k !== "email").map((f) => (
        <label key={f.k} className={`block text-[13px] text-quiet ${f.wide ? "col-span-2" : ""}`}>{f.label}
          <input value={d[f.k]} onChange={set(f.k)} autoComplete={f.auto} type={f.type ?? "text"} inputMode={f.mode} required={!f.optional}
            aria-invalid={bad === f.k} className={`${input} ${bad === f.k ? "border-ink" : ""}`} maxLength={f.k === "pin" ? 6 : 120} />
        </label>
      ))}
      <label className="col-span-2 block text-[13px] text-quiet">state
        <select value={d.state} onChange={set("state")} autoComplete="address-level1" required aria-invalid={bad === "state"} className={`${input} appearance-none`}>
          <option value="" disabled>pick your state</option>
          {SHIP_STATES.map((s) => <option key={s} value={s} className="bg-paper">{s}</option>)}
        </select>
      </label>
    </div>
  );
}

/** one line of an address, for lists */
export const addressLine = (a: Omit<Details, "email">) => [a.address1, a.address2, a.city, `${a.state} ${a.pin}`].filter(Boolean).join(", ");

/** a JSON POST to a shop route; throws the route's own error message */
export async function post<T = { ok: true }>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = (await r.json().catch(() => ({}))) as T & { error?: string; field?: string };
  if (!r.ok) throw Object.assign(new Error(j.error ?? "something went wrong, try again"), { field: j.field });
  return j;
}
