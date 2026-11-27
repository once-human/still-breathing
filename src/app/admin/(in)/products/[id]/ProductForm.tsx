"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Product } from "@/lib/shop/products";
import { FIELD, SaveBar, useAdminPost, useToast } from "../../../ui/client";
import { Field, Fixed, Group, Section } from "../../../ui/ui";

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

  const money = `${FIELD} !w-32 text-right tnum`;
  return (
    <>
      <Section title="on the site">
        <Group>
          <Field stack label="name" hint="its title on its page, the cards, the header and share text" count={[v.name.trim().length, 60]}>
            <input value={v.name} onChange={set("name")} maxLength={60} className={FIELD} />
          </Field>
          <Field stack label="about" hint="the words on its page and its share description" count={[v.about.trim().length, 600]}>
            <textarea value={v.about} onChange={set("about")} maxLength={600} rows={5} className={`${FIELD} !h-auto resize-y py-3 leading-snug`} />
          </Field>
          <Field label="order" hint="lower comes first in its group">
            <input inputMode="numeric" value={v.sort} onChange={set("sort")} className={`${FIELD} !w-24 text-right tnum`} />
          </Field>
        </Group>
      </Section>

      <Section title="price" id="price">
        <Group>
          <Field label="qikink cost" hint="what qikink charges for one, GST included"><Fixed>{rs(p.cost)}</Fixed></Field>
          <Field label="own margin" hint={`empty: the shop's ₹${shopMargin}, from prices`}>
            <span className="flex items-center gap-1.5 text-quiet">₹<input inputMode="decimal" value={v.margin} onChange={set("margin")} placeholder={String(shopMargin)} className={money} /></span>
          </Field>
          <Field label="fixed price" hint="empty: cost + margin, up to the next ₹10">
            <span className="flex items-center gap-1.5 text-quiet">₹<input inputMode="decimal" value={v.fixed} onChange={set("fixed")} placeholder="–" className={money} /></span>
          </Field>
          <div className="flex flex-wrap items-end justify-between gap-3 px-5 py-5">
            <div>
              <div className="text-[13px] text-quiet">sells at{Number.isFinite(price) && price !== was ? <span className="ml-2 text-warn">was {rs(was)}</span> : null}</div>
              <div className="tnum mt-1 text-[34px] font-extrabold leading-none tracking-[-0.04em]">{Number.isFinite(price) ? rs(price) : "–"}</div>
            </div>
            <div className="tnum text-right text-[13px] text-quiet">leaves {Number.isFinite(price) ? rs(price - p.cost) : "–"} a shirt<br />before post and the payment fee</div>
          </div>
        </Group>
      </Section>

      {problems.length && changes.length ? <p className="-mt-6 mb-10 px-1 text-[13px] text-bad">needs {problems.join("; ")}</p> : null}

      <SaveBar dirty={changes.length > 0} busy={busy} onSave={save} onDiscard={() => setV(base)}
        summary={changes.map((k) => WORD[k]).join(", ")}
        warn={Number.isFinite(price) && price !== was ? `the price goes from ${rs(was)} to ${rs(price)} on the site and at checkout, at once. orders already paid keep their price.` : null} />
    </>
  );
}
