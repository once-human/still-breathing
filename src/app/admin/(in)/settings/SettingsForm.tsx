"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Settings } from "@/lib/admin/settings";
import { BTN, useAdminPost } from "../../ui/client";

const NUM: { key: keyof Settings; label: string; hint: string; step: string; unit?: string }[] = [
  { key: "margin", label: "margin per shirt", hint: "over qikink's cost, then up to the next ₹10", step: "10", unit: "₹" },
  { key: "feeRate", label: "razorpay fee rate", hint: "used until an order's actual fee is fetched (0.0236 = 2% + gst)", step: "0.0001" },
  { key: "shipPerParcel", label: "post per parcel", hint: "qikink's air rate under 500 g", step: "0.01", unit: "₹" },
  { key: "shirtsPerParcel", label: "shirts per parcel", hint: "how many fit under 500 g", step: "1" },
  { key: "lowWallet", label: "keep in the qikink wallet", hint: "for the reminder", step: "100", unit: "₹" },
];

export function SettingsForm({ initial, defaults }: { initial: Settings; defaults: Settings }) {
  const post = useAdminPost();
  const router = useRouter();
  const [s, setS] = useState(initial);
  const [confirm, setConfirm] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const changed = (Object.keys(s) as (keyof Settings)[]).filter((k) => s[k] !== initial[k]);
  const save = async () => {
    const patch = Object.fromEntries(changed.map((k) => [k, s[k]]));
    const r = await post("/api/admin/settings", patch);
    setConfirm(false);
    setMsg(r.ok ? { ok: true, text: "saved" } : { ok: false, text: r.error });
    if (r.ok) router.refresh();
  };
  const field = "h-9 w-36 bg-transparent px-2 text-right text-[14px] tnum ring-1 ring-line focus:ring-ink focus:outline-none";
  return (
    <div className="grid gap-6">
      <label className="flex max-w-xl items-center justify-between gap-6 border-b border-line/60 pb-4">
        <span>
          <span className="block text-[14px] font-medium">taking orders</span>
          <span className="block text-[12px] text-quiet">off: checkout says the shop is closed for now; the shirts stay on the site</span>
        </span>
        <input type="checkbox" checked={s.open} onChange={(e) => setS({ ...s, open: e.target.checked })} className="h-5 w-5 accent-[var(--blue)]" />
      </label>
      <div className="grid max-w-xl gap-3">
        {NUM.map((f) => (
          <label key={f.key} className="flex items-center justify-between gap-6">
            <span>
              <span className="block text-[14px]">{f.label}</span>
              <span className="block text-[12px] text-quiet">{f.hint}{s[f.key] !== defaults[f.key] ? ` · default ${defaults[f.key]}` : ""}</span>
            </span>
            <span className="flex items-center gap-1 text-quiet">{f.unit}
              <input type="number" step={f.step} value={String(s[f.key])} onChange={(e) => setS({ ...s, [f.key]: e.target.value === "" ? 0 : Number(e.target.value) })} className={field} />
            </span>
          </label>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {confirm ? (
          <>
            <span className="text-[13px]">save {changed.join(", ")}{changed.includes("margin") ? ": every shirt's price changes on the site and at checkout" : ""}{changed.includes("open") && !s.open ? ": checkout closes now" : ""}?</span>
            <button type="button" onClick={save} className={BTN.main}>yes, save</button>
            <button type="button" onClick={() => setConfirm(false)} className={BTN.plain}>no</button>
          </>
        ) : (
          <button type="button" disabled={!changed.length} onClick={() => { setMsg(null); setConfirm(true); }} className={BTN.main}>save changes</button>
        )}
        {msg ? <span className={`text-[12px] ${msg.ok ? "text-[#8fd19e]" : "text-[#f08a7a]"}`}>{msg.text}</span> : null}
      </div>
    </div>
  );
}
