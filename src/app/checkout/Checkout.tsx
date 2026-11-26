"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { POLICIES_READY } from "@/content/policies";
import { SHOP, priceOf } from "@/content/shop";
import { shirtName } from "@/components/shop/BagDrawer";
import { bagCount, bagPayable, bagTotal, shop, useShop } from "@/lib/shop/client";
import { STATES, checkDetails, type Details } from "@/lib/shop/india";
import { rupees } from "@/lib/shop/money";
import type { PayStart } from "@/lib/shop/types";

type RzpResponse = { razorpay_payment_id: string; razorpay_order_id: string; razorpay_signature: string };
type RzpCheckout = { open(): void; on(ev: string, f: (r: unknown) => void): void };
declare global {
  interface Window { Razorpay?: new (o: Record<string, unknown>) => RzpCheckout }
}

/** Razorpay's payment window, loaded only when the buyer pays (from Razorpay itself; payment details go only there) */
const loadRazorpay = () =>
  new Promise<void>((ok, fail) => {
    if (window.Razorpay) return ok();
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => ok();
    s.onerror = () => fail(new Error("the payment window didn't load. check your connection and try again"));
    document.head.appendChild(s);
  });

const FIELDS: { k: keyof Details; label: string; auto: string; type?: string; mode?: "numeric" | "tel" | "email"; wide?: boolean; optional?: boolean }[] = [
  { k: "name", label: "full name", auto: "name", wide: true },
  { k: "email", label: "email, for the confirmation and tracking", auto: "email", type: "email", mode: "email", wide: true },
  { k: "phone", label: "mobile, for the courier", auto: "tel-national", type: "tel", mode: "tel", wide: true },
  { k: "address1", label: "house, flat or building, street", auto: "address-line1", wide: true },
  { k: "address2", label: "area, landmark (optional)", auto: "address-line2", wide: true, optional: true },
  { k: "city", label: "city or town", auto: "address-level2" },
  { k: "pin", label: "pin code", auto: "postal-code", mode: "numeric" },
];

const input = "mt-1 h-12 w-full border border-line bg-transparent px-3 text-[16px] text-ink outline-none focus:border-ink";

export function Checkout() {
  const { bag, pay: payView } = useShop();
  const router = useRouter();
  const [d, setD] = useState<Details>({ name: "", email: "", phone: "", address1: "", address2: "", city: "", state: "", pin: "" });
  const [bad, setBad] = useState<{ field?: keyof Details; error: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  if (!ready) return <p className="text-quiet">&nbsp;</p>;
  if (bag.length === 0) {
    return <p className="max-w-[44ch] text-[clamp(18px,1.8vw,24px)] leading-[1.25] text-ink/85">your bag is empty. <Link href="/lineup-01" className="draw">the shirts →</Link></p>;
  }

  async function pay(e: React.FormEvent) {
    e.preventDefault();
    const c = checkDetails(d);
    if ("error" in c) return setBad(c);
    setBad(null);
    if (!bagPayable(bag, payView)) {
      return setBad({ error: payView?.pay ? "one of these shirts can't be paid for in that size yet. take it out of the bag to go on." : "payment isn't connected yet, so nothing can be paid or ordered today. nothing has been charged, and your details weren't sent anywhere." });
    }
    setBusy(true);
    try {
      const r = await fetch("/api/shop/checkout", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ bag, details: c.ok }) });
      const j = (await r.json().catch(() => ({}))) as PayStart & { error?: string; field?: keyof Details };
      if (!r.ok) throw Object.assign(new Error(j.error ?? "something went wrong, try again"), { field: j.field });
      await loadRazorpay();
      const rzp = new window.Razorpay!({
        key: j.keyId,
        order_id: j.rzpOrderId,
        amount: j.amount,
        currency: "INR",
        name: j.name,
        description: `order #${j.orderId}`,
        prefill: { ...j.prefill, method: "upi" },
        notes: { order: j.orderId },
        theme: { color: "#0d0d0c" },
        config: { display: { blocks: { upi: { name: "pay by UPI", instruments: [{ method: "upi" }] } }, sequence: ["block.upi"], preferences: { show_default_blocks: true } } },
        modal: { ondismiss: () => setBusy(false), confirm_close: true },
        handler: async (res: RzpResponse) => {
          const p = await fetch("/api/shop/paid", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ orderId: j.orderId, ...res }) });
          const pj = (await p.json().catch(() => ({}))) as { url?: string; error?: string };
          shop.empty();
          // paid either way: if this answer got lost, the payment is still confirmed by Razorpay's own message to us
          router.push(pj.url ?? "/order");
        },
      });
      rzp.on("payment.failed", () => setBad({ error: "that payment didn't go through. nothing was taken; try again, or another way to pay" }));
      rzp.open();
    } catch (err) {
      setBad({ field: (err as { field?: keyof Details }).field, error: (err as Error).message });
      setBusy(false);
    }
  }

  const set = (k: keyof Details) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setD({ ...d, [k]: e.target.value });
  const total = bagTotal(bag);
  const live = bagPayable(bag, payView);

  return (
    <div className="grid grid-cols-1 gap-x-4 gap-y-12 md:grid-cols-12">
      <form onSubmit={pay} noValidate className="md:col-span-6 lg:col-span-5">
        <p className="border-t border-line pt-1.5 text-[13px] text-quiet">where it goes</p>
        <div className="mt-4 grid grid-cols-2 gap-x-3 gap-y-4">
          {FIELDS.map((f) => (
            <label key={f.k} className={`block text-[13px] text-quiet ${f.wide ? "col-span-2" : ""}`}>{f.label}
              <input value={d[f.k]} onChange={set(f.k)} autoComplete={f.auto} type={f.type ?? "text"} inputMode={f.mode} required={!f.optional}
                aria-invalid={bad?.field === f.k} className={`${input} ${bad?.field === f.k ? "border-ink" : ""}`} maxLength={f.k === "pin" ? 6 : 120} />
            </label>
          ))}
          <label className="col-span-2 block text-[13px] text-quiet">state
            <select value={d.state} onChange={set("state")} autoComplete="address-level1" required aria-invalid={bad?.field === "state"} className={`${input} appearance-none`}>
              <option value="" disabled>pick your state</option>
              {STATES.map((s) => <option key={s} value={s} className="bg-paper">{s}</option>)}
            </select>
          </label>
        </div>
        {bad && <p role="alert" className="mt-4 text-[14px]">{bad.error}</p>}
        <button disabled={busy} className="mt-6 flex h-12 w-full items-center justify-between bg-ink px-4 text-[15px] font-semibold text-paper hover:bg-ink/90 disabled:opacity-60">
          <span>{busy ? "one moment.." : "pay"}</span><span className="tnum">{rupees(total)}</span>
        </button>
        <p className="mt-2 text-[12px] text-quiet">
          {live || payView === null ? <>UPI, card or net banking, on Razorpay&apos;s secure payment window. Your payment details go only to Razorpay.</> : <>Payment isn&apos;t connected yet: nothing can be paid or ordered today.</>}
          {POLICIES_READY ? <> By paying you agree to the <Link href="/policies/terms" className="draw hover:text-ink">terms</Link>.</> : null}
        </p>
      </form>

      <div className="md:col-span-5 md:col-start-8 lg:col-span-4 lg:col-start-9">
        <p className="border-t border-line pt-1.5 text-[13px] text-quiet">your bag · {bagCount(bag)}</p>
        <ul className="mt-2 text-[14px]">
          {bag.map((l) => (
            <li key={`${l.design}-${l.size}`} className="flex justify-between border-b border-line py-2">
              <span>{shirtName(l.design)}<span className="text-quiet"> · {l.size} × {l.quantity}</span></span>
              <span className="tnum">{rupees(priceOf(l.design) * l.quantity)}</span>
            </li>
          ))}
        </ul>
        <p className="mt-3 flex justify-between text-[15px]"><span>total</span><span className="tnum font-semibold">{rupees(total)}</span></p>
        <p className="mt-1 text-[12px] text-quiet">GST and shipping included. Made for you in {SHOP.make[0]}–{SHOP.make[1]} days, then {SHOP.road[0]}–{SHOP.road[1]} on the road.</p>
        <button type="button" onClick={shop.open} className="hit mt-3 text-[13px] text-quiet hover:text-ink">change the bag</button>
      </div>
    </div>
  );
}
