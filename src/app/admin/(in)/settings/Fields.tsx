"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Settings } from "@/lib/admin/settings";
import { FIELD, SaveBar, useAdminPost, useToast } from "../../ui/client";
import { Field, Fixed, Group } from "../../ui/ui";

type Keys = "margin" | "lowWallet" | "notice" | "closed";
const NUM: Keys[] = ["margin", "lowWallet"];
const WORD: Record<Keys, string> = { margin: "margin", lowWallet: "wallet reminder", notice: "top line", closed: "closed message" };

/** a few of the shop's settings, collected in a "save changes" bar and saved together */
function useSettings<K extends Keys>(initial: Settings, keys: K[], check: (v: Record<K, string>) => string[]) {
  const post = useAdminPost();
  const say = useToast();
  const router = useRouter();
  const pick = () => Object.fromEntries(keys.map((k) => [k, String(initial[k] ?? "")])) as Record<K, string>;
  const [base, setBase] = useState(pick);
  const [v, setV] = useState(base);
  const [busy, setBusy] = useState(false);
  const changed = keys.filter((k) => v[k] !== base[k]);
  const problems = check(v);
  const set = (k: K) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setV({ ...v, [k]: e.target.value });
  const save = async () => {
    if (problems.length) return say(false, problems[0]);
    setBusy(true);
    const patch = Object.fromEntries(changed.map((k) => [k, NUM.includes(k) ? Number(v[k]) : v[k].trim()]));
    const r = await post("/api/admin/settings", patch);
    setBusy(false);
    if (!r.ok) return say(false, r.error);
    const next = Object.fromEntries(keys.map((k) => [k, v[k].trim()])) as Record<K, string>;
    setBase(next);
    setV(next);
    say(true, "saved: the site has it within a minute");
    router.refresh();
  };
  return { v, base, set, changed, problems, busy, save, discard: () => setV(base), summary: changed.map((k) => WORD[k]).join(", ") };
}

/** the margin every shirt is priced by, and the wallet reminder; the partners' rates shown grey beside them */
export function PricesForm({ initial }: { initial: Settings }) {
  const f = useSettings(initial, ["margin", "lowWallet"], (v) => [
    ...(/^\d{1,5}$/.test(v.margin) ? [] : ["margin: a whole number of rupees"]),
    ...(/^\d{1,6}$/.test(v.lowWallet) ? [] : ["wallet reminder: a whole number of rupees"]),
  ]);
  const input = `${FIELD} !w-32 text-right tnum`;
  return (
    <div className="grid gap-6">
      <Group>
        <Field label="margin per shirt" hint="added to qikink's cost, then up to the next ₹10. a shirt with its own margin or price keeps it">
          <span className="flex items-center gap-1.5 text-quiet">₹<input inputMode="numeric" value={f.v.margin} onChange={f.set("margin")} className={input} /></span>
        </Field>
        <Field label="qikink wallet reminder" hint="qikink takes each print from its wallet: keep at least this much in it">
          <span className="flex items-center gap-1.5 text-quiet">₹<input inputMode="numeric" value={f.v.lowWallet} onChange={f.set("lowWallet")} className={input} /></span>
        </Field>
      </Group>
      <Group>
        <Field label="razorpay fee" hint="2% + 18% GST, until an order's own fee comes from razorpay"><Fixed>{(initial.feeRate * 100).toFixed(2)}%</Fixed></Field>
        <Field label="post per parcel" hint="qikink's air rate under 500 g, GST included"><Fixed>₹{initial.shipPerParcel.toFixed(2)}</Fixed></Field>
        <Field label="shirts per parcel" hint="how many fit under 500 g"><Fixed>{initial.shirtsPerParcel}</Fixed></Field>
      </Group>
      <SaveBar dirty={f.changed.length > 0} busy={f.busy} onSave={f.save} onDiscard={f.discard} summary={f.summary}
        warn={f.changed.includes("margin") ? `every shirt on the shop rule moves by ₹${Number(f.v.margin) - Number(f.base.margin)} on the site and at checkout, at once. orders already paid keep their price.` : null} />
    </div>
  );
}

/** the two lines of the site's own words that are yours: the top line and what a closed checkout says */
export function WordsForm({ initial }: { initial: Settings }) {
  const f = useSettings(initial, ["notice", "closed"], (v) => [
    ...(v.notice.length > 140 ? ["top line: up to 140 characters"] : []),
    ...(v.closed.length > 200 ? ["closed message: up to 200 characters"] : []),
  ]);
  return (
    <div className="grid gap-6">
      <Group>
        <Field stack label="top line" hint="the line over the header on every page. empty: the usual one" count={[f.v.notice.length, 140]}>
          <input value={f.v.notice} onChange={f.set("notice")} maxLength={140} placeholder="free delivery anywhere in india, made to order" className={FIELD} />
        </Field>
        <Field stack label="closed message" hint="what checkout says while you're not taking orders. empty: the usual one" count={[f.v.closed.length, 200]}>
          <textarea value={f.v.closed} onChange={f.set("closed")} maxLength={200} rows={3} placeholder="the shop is closed for a bit. your bag stays as it is." className={`${FIELD} !h-auto resize-y py-3 leading-snug`} />
        </Field>
      </Group>
      <SaveBar dirty={f.changed.length > 0} busy={f.busy} onSave={f.save} onDiscard={f.discard} summary={f.summary} />
    </div>
  );
}
