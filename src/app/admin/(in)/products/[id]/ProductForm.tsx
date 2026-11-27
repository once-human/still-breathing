"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Product } from "@/lib/shop/products";
import { FIELD, SaveBar, useAdminPost, useToast } from "../../../ui/client";

const rule = (cost: number, margin: number) => Math.ceil((cost + margin) / 10) * 10;
const rs = (n: number) => `₹${(Math.round(n * 100) / 100).toLocaleString("en-IN")}`;

/**
 * The parts of a shirt that are Onkar's to change: its words, its order, its margin or a fixed price. Qikink's cost
 * and SKUs are Qikink's, so they're shown locked beside it. Changes collect in a "save changes" bar; a price move
 * asks first. The status switch is on the page above and saves at once.
 */
export function ProductForm({ p, shopMargin }: { p: Product; shopMargin: number }) {
  const post = useAdminPost();
  const say = useToast();
  const router = useRouter();
  const start = { name: p.name, about: p.about, sort: String(p.sort), margin: p.margin == null ? "" : String(p.margin), fixed: p.fixedPrice == null ? "" : String(p.fixedPrice) };
  const [v, setV] = useState(start);
  const [base, setBase] = useState(start);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof start) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setV({ ...v, [k]: e.target.value });

  const m = v.margin === "" ? shopMargin : Number(v.margin), f = v.fixed === "" ? null : Number(v.fixed);
  const price = f ?? (Number.isFinite(m) ? rule(p.cost, m) : NaN);
  const was = base.fixed !== "" ? Number(base.fixed) : rule(p.cost, base.margin === "" ? shopMargin : Number(base.margin));

  const problems: string[] = [];
  if (!v.name.trim() || v.name.trim().length > 60) problems.push("a name, up to 60 characters");
  if (!v.about.trim() || v.about.trim().length > 600) problems.push("some words, up to 600 characters");
  if (!/^\d{1,3}$/.test(v.sort)) problems.push("order: a whole number, 0 to 999");
  if (v.margin !== "" && !(Number.isFinite(m) && m >= 0)) problems.push("a margin of ₹0 or more");
  if (f != null && !(Number.isFinite(f) && f > p.cost)) problems.push(`a fixed price above qikink's ${rs(p.cost)}`);

  const patch: Record<string, unknown> = {};
  if (v.name.trim() !== base.name) patch.name = v.name.trim();
  if (v.about.trim() !== base.about) patch.about = v.about.trim();
  if (v.sort !== base.sort) patch.sort = Number(v.sort);
  if (v.margin !== base.margin) patch.margin = v.margin === "" ? null : Number(v.margin);
  if (v.fixed !== base.fixed) patch.fixedPrice = f;
  const changes = Object.keys(patch);
  const WORD: Record<string, string> = { name: "name", about: "words", sort: "order", margin: "margin", fixedPrice: "fixed price" };

  const save = async () => {
    if (problems.length) return say(false, `needs ${problems[0]}`);
    setBusy(true);
    const r = await post(`/api/admin/products/${p.id}`, patch);
    setBusy(false);
    if (!r.ok) return say(false, r.error);
    const next = { ...v, name: v.name.trim(), about: v.about.trim() };
    setV(next);
    setBase(next);
    say(true, `saved${price !== was ? `: it sells at ${rs(price)} now` : ""}`);
    router.refresh();
  };

  const card = "grid gap-4 rounded-xl border border-line p-4 md:p-5";
  const legend = "text-[12px] font-semibold uppercase tracking-[0.12em] text-quiet";
  return (
    <div className="grid max-w-3xl gap-6 pb-24">
      <section className={card}>
        <h2 className={legend}>on the site</h2>
        <label className="grid gap-1 text-[12px] text-quiet">name · its title on its page, the cards, the header and share text
          <input value={v.name} onChange={set("name")} maxLength={60} className={FIELD} />
        </label>
        <label className="grid gap-1 text-[12px] text-quiet">
          <span className="flex justify-between">about · the words on its page and its share description <span className="tnum">{v.about.trim().length}/600</span></span>
          <textarea value={v.about} onChange={set("about")} maxLength={600} rows={5} className={`${FIELD} !h-auto resize-y py-2 leading-snug`} />
        </label>
        <label className="flex items-center justify-between gap-4 text-[14px]"><span>order <span className="block text-[12px] text-quiet">lower comes first in its group</span></span>
          <input inputMode="numeric" value={v.sort} onChange={set("sort")} className={`${FIELD} !w-24 text-right`} />
        </label>
      </section>

      <section className={card}>
        <h2 className={legend}>price</h2>
        <div className="flex items-center justify-between gap-4 text-[14px]">
          <span>qikink cost <span className="block text-[12px] text-quiet">what qikink charges for one, GST included</span></span>
          <span className="tnum flex items-center gap-2 rounded-md bg-ink/[0.04] px-3 py-2 text-quiet" title="qikink's price: it changes only when qikink's does">{rs(p.cost)}</span>
        </div>
        <label className="flex items-center justify-between gap-4 text-[14px]"><span>own margin <span className="block text-[12px] text-quiet">empty: the shop&apos;s ₹{shopMargin}, from settings</span></span>
          <span className="flex items-center gap-1 text-quiet">₹<input inputMode="decimal" value={v.margin} onChange={set("margin")} placeholder={String(shopMargin)} className={`${FIELD} !w-28 text-right`} /></span>
        </label>
        <label className="flex items-center justify-between gap-4 text-[14px]"><span>fixed price <span className="block text-[12px] text-quiet">empty: cost + margin, up to the next ₹10</span></span>
          <span className="flex items-center gap-1 text-quiet">₹<input inputMode="decimal" value={v.fixed} onChange={set("fixed")} placeholder="–" className={`${FIELD} !w-28 text-right`} /></span>
        </label>
        <div className="flex flex-wrap items-end justify-between gap-3 border-t border-line pt-4">
          <div className="text-[14px]">sells at <span className="tnum text-[26px] font-bold">{Number.isFinite(price) ? rs(price) : "–"}</span>
            {Number.isFinite(price) && price !== was ? <span className="ml-2 rounded-full bg-[#f0a35b]/15 px-2 py-0.5 text-[12px] text-[#f0a35b]">was {rs(was)}</span> : null}</div>
          <div className="tnum text-right text-[12px] text-quiet">leaves {Number.isFinite(price) ? rs(price - p.cost) : "–"} a shirt<br />before post and the payment fee</div>
        </div>
      </section>

      {problems.length && changes.length ? <p className="rounded-md bg-[#f08a7a]/10 px-3 py-2 text-[12px] text-[#f08a7a]">needs {problems.join("; ")}</p> : null}

      <SaveBar dirty={changes.length > 0} busy={busy} onSave={save} onDiscard={() => setV(base)}
        summary={changes.map((k) => WORD[k]).join(", ")}
        warn={Number.isFinite(price) && price !== was ? `the price goes from ${rs(was)} to ${rs(price)} on the site and at checkout, at once. orders already paid keep their price.` : null} />
    </div>
  );
}
