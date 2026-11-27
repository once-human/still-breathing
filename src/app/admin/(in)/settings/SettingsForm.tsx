"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Settings } from "@/lib/admin/settings";
import { FIELD, SaveBar, Toggle, useAdminPost, useToast } from "../../ui/client";

type Editable = { margin: string; notice: string; closed: string; lowWallet: string };
const pick = (s: Settings): Editable => ({ margin: String(s.margin), notice: s.notice ?? "", closed: s.closed ?? "", lowWallet: String(s.lowWallet) });
const WORD: Record<keyof Editable, string> = { margin: "margin", notice: "top line", closed: "closed message", lowWallet: "wallet reminder" };

/**
 * The shop's switches and words: "taking orders" saves the moment it's flipped (with a pop-up first when it closes
 * checkout); margin, the top line, the closed message and the wallet reminder collect in a "save changes" bar.
 */
export function SettingsForm({ initial }: { initial: Settings }) {
  const post = useAdminPost();
  const say = useToast();
  const router = useRouter();
  const [base, setBase] = useState(pick(initial));
  const [v, setV] = useState(base);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof Editable) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setV({ ...v, [k]: e.target.value });

  const changed = (Object.keys(v) as (keyof Editable)[]).filter((k) => v[k] !== base[k]);
  const problems: string[] = [];
  if (!/^\d{1,5}$/.test(v.margin)) problems.push("margin: a whole number of rupees");
  if (!/^\d{1,6}$/.test(v.lowWallet)) problems.push("wallet reminder: a whole number of rupees");
  if (v.notice.length > 140) problems.push("top line: up to 140 characters");
  if (v.closed.length > 200) problems.push("closed message: up to 200 characters");

  const save = async () => {
    if (problems.length) return say(false, problems[0]);
    setBusy(true);
    const patch: Record<string, unknown> = {};
    for (const k of changed) patch[k] = k === "margin" || k === "lowWallet" ? Number(v[k]) : v[k].trim();
    const r = await post("/api/admin/settings", patch);
    setBusy(false);
    if (!r.ok) return say(false, r.error);
    const next = { ...v, notice: v.notice.trim(), closed: v.closed.trim() };
    setBase(next);
    setV(next);
    say(true, "saved: the site has it within a minute");
    router.refresh();
  };

  const card = "rounded-xl border border-line p-4 md:p-5";
  const row = "flex flex-wrap items-center justify-between gap-4 text-[14px]";
  return (
    <div className="grid max-w-3xl gap-6 pb-24">
      <div className={`${card} !py-1`}>
        <Toggle label="taking orders" field="open" url="/api/admin/settings" value={initial.open}
          hint="off: the shirts stay on the site, checkout shows your closed message"
          confirmOff="checkout closes on the whole site at once. people can still look and fill their bag; anyone mid-payment can finish."
          confirmOn="checkout opens again for everyone, at the prices shown now." />
      </div>

      <section className={`${card} grid gap-4`}>
        <h2 className="text-[12px] font-semibold uppercase tracking-[0.12em] text-quiet">words on the site</h2>
        <label className="grid gap-1 text-[12px] text-quiet">
          <span className="flex justify-between">top line · replaces the line above the header on every page. empty: the usual one <span className="tnum">{v.notice.length}/140</span></span>
          <input value={v.notice} onChange={set("notice")} maxLength={140} placeholder="free shipping across india" className={FIELD} />
        </label>
        <label className="grid gap-1 text-[12px] text-quiet">
          <span className="flex justify-between">closed message · what checkout says while orders are off. empty: the usual one <span className="tnum">{v.closed.length}/200</span></span>
          <textarea value={v.closed} onChange={set("closed")} maxLength={200} rows={2} placeholder="the shop is closed for a bit. your bag stays as it is." className={`${FIELD} !h-auto resize-y py-2`} />
        </label>
      </section>

      <section className={`${card} grid gap-4`}>
        <h2 className="text-[12px] font-semibold uppercase tracking-[0.12em] text-quiet">money</h2>
        <label className={row}><span>margin per shirt <span className="block text-[12px] text-quiet">over qikink&apos;s cost, then up to the next ₹10. a shirt with its own margin or price keeps it</span></span>
          <span className="flex items-center gap-1 text-quiet">₹<input inputMode="numeric" value={v.margin} onChange={set("margin")} className={`${FIELD} !w-28 text-right tnum`} /></span>
        </label>
        <label className={row}><span>qikink wallet reminder <span className="block text-[12px] text-quiet">the least to keep in it; shown on the home page</span></span>
          <span className="flex items-center gap-1 text-quiet">₹<input inputMode="numeric" value={v.lowWallet} onChange={set("lowWallet")} className={`${FIELD} !w-28 text-right tnum`} /></span>
        </label>
        {[
          ["razorpay fee", `${(initial.feeRate * 100).toFixed(2)}% of an order`, "2% + 18% GST, until an order's real fee is fetched from razorpay"],
          ["post per parcel", `₹${initial.shipPerParcel.toFixed(2)}`, "qikink's air rate under 500 g, GST included"],
          ["shirts per parcel", String(initial.shirtsPerParcel), "how many fit under 500 g"],
        ].map(([l, val, hint]) => (
          <div key={l} className={row}><span>{l} <span className="block text-[12px] text-quiet">{hint}</span></span>
            <span className="tnum rounded-md bg-ink/[0.04] px-3 py-2 text-quiet" title="the partner's rate: locked">{val}</span>
          </div>
        ))}
      </section>

      {problems.length && changed.length ? <p className="rounded-md bg-[#f08a7a]/10 px-3 py-2 text-[12px] text-[#f08a7a]">{problems.join("; ")}</p> : null}

      <SaveBar dirty={changed.length > 0} busy={busy} onSave={save} onDiscard={() => setV(base)} summary={changed.map((k) => WORD[k]).join(", ")}
        warn={changed.includes("margin") ? `every shirt on the shop rule moves by ₹${Number(v.margin) - Number(base.margin)} on the site and at checkout, at once. orders already paid keep their price.` : null} />
    </div>
  );
}
