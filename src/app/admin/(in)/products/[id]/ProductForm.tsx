"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { SIZE_ORDER, type Size } from "@/content/tee";
import type { Product, ProductStatus } from "@/lib/shop/products";
import { BTN, useAdminPost } from "../../../ui/client";

const rule = (cost: number, margin: number) => Math.ceil((cost + margin) / 10) * 10;
const field = "h-9 bg-transparent px-2 text-[14px] ring-1 ring-line focus:ring-ink focus:outline-none";

/**
 * What can be changed on a shirt, and what each change does: status (on sale, sold out, draft: off sale), what
 * qikink charges, its own margin or a fixed price (else the shop's margin), and the qikink SKU for each size (a size
 * with no SKU can't be bought). The new price is shown before it's saved.
 */
export function ProductForm({ p, shopMargin }: { p: Product; shopMargin: number }) {
  const post = useAdminPost();
  const router = useRouter();
  const [status, setStatus] = useState<ProductStatus>(p.status);
  const [name, setName] = useState(p.name);
  const [about, setAbout] = useState(p.about);
  const [sort, setSort] = useState(String(p.sort));
  const [cost, setCost] = useState(String(p.cost));
  const [margin, setMargin] = useState(p.margin == null ? "" : String(p.margin));
  const [fixed, setFixed] = useState(p.fixedPrice == null ? "" : String(p.fixedPrice));
  const [skus, setSkus] = useState<Partial<Record<Size, string>>>(p.skus);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const wordsOk = name.trim().length >= 1 && about.trim().length >= 1 && Number.isInteger(Number(sort));

  const c = Number(cost), m = margin === "" ? shopMargin : Number(margin), f = fixed === "" ? null : Number(fixed);
  const price = f ?? (Number.isFinite(c) && Number.isFinite(m) ? rule(c, m) : NaN);
  const patch: Record<string, unknown> = {};
  if (status !== p.status) patch.status = status;
  if (name.trim() !== p.name) patch.name = name.trim();
  if (about.trim() !== p.about) patch.about = about.trim();
  if (Number(sort) !== p.sort) patch.sort = Number(sort);
  if (c !== p.cost) patch.cost = c;
  if ((margin === "" ? null : Number(margin)) !== p.margin) patch.margin = margin === "" ? null : Number(margin);
  if (f !== p.fixedPrice) patch.fixedPrice = f;
  const cleanSkus = Object.fromEntries(SIZE_ORDER.map((z) => [z, (skus[z] ?? "").trim()]).filter(([, v]) => v));
  if (JSON.stringify(cleanSkus) !== JSON.stringify(Object.fromEntries(SIZE_ORDER.map((z) => [z, p.skus[z] ?? ""]).filter(([, v]) => v)))) patch.skus = Object.fromEntries(SIZE_ORDER.map((z) => [z, (skus[z] ?? "").trim()]));
  const changes = Object.keys(patch);

  const save = async () => {
    setBusy(true);
    const r = await post(`/api/admin/products/${p.id}`, patch);
    setBusy(false);
    setConfirm(false);
    setMsg(r.ok ? { ok: true, text: "saved: the site and checkout have it within a minute" } : { ok: false, text: r.error });
    if (r.ok) router.refresh();
  };

  return (
    <div className="grid max-w-2xl gap-8">
      <fieldset className="grid gap-2">
        <legend className="mb-2 text-[12px] font-semibold uppercase tracking-[0.12em] text-quiet">status</legend>
        {([["live", "on sale", "the buy button works in every size with a sku"], ["soldout", "sold out", "the shirt stays on the site, its button says sold out"], ["draft", "draft", "hidden: off the shop, the lineup and the header, its own page is not found"]] as const).map(([v, label, hint]) => (
          <label key={v} className="flex items-baseline gap-3 text-[14px]">
            <input type="radio" name="status" checked={status === v} onChange={() => setStatus(v)} className="accent-[var(--blue)]" />
            <span>{label} <span className="text-[12px] text-quiet">{hint}</span></span>
          </label>
        ))}
      </fieldset>

      <fieldset className="grid gap-3">
        <legend className="mb-2 text-[12px] font-semibold uppercase tracking-[0.12em] text-quiet">on the site</legend>
        <label className="grid gap-1 text-[12px] text-quiet">name <span>the shirt&apos;s title on its page, cards, the header and share text</span>
          <input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} className={`${field} text-ink`} />
        </label>
        <label className="grid gap-1 text-[12px] text-quiet">about <span>the short words on its page and in its share description ({about.trim().length}/600)</span>
          <textarea value={about} onChange={(e) => setAbout(e.target.value)} maxLength={600} rows={5} className="resize-y bg-transparent p-2 text-[14px] leading-snug text-ink ring-1 ring-line focus:ring-ink focus:outline-none" />
        </label>
        <label className="flex items-center justify-between gap-4 text-[14px]"><span>order <span className="block text-[12px] text-quiet">lower comes first, within its group</span></span>
          <input type="number" step="1" value={sort} onChange={(e) => setSort(e.target.value)} className={`${field} w-24 text-right`} />
        </label>
      </fieldset>

      <fieldset className="grid gap-3">
        <legend className="mb-2 text-[12px] font-semibold uppercase tracking-[0.12em] text-quiet">price</legend>
        <label className="flex items-center justify-between gap-4 text-[14px]">qikink cost (gst included)
          <span className="text-quiet">₹ <input type="number" step="0.01" value={cost} onChange={(e) => setCost(e.target.value)} className={`${field} w-32 text-right`} /></span>
        </label>
        <label className="flex items-center justify-between gap-4 text-[14px]"><span>own margin <span className="block text-[12px] text-quiet">empty: the shop&apos;s {shopMargin}</span></span>
          <span className="text-quiet">₹ <input type="number" step="10" value={margin} onChange={(e) => setMargin(e.target.value)} placeholder={String(shopMargin)} className={`${field} w-32 text-right`} /></span>
        </label>
        <label className="flex items-center justify-between gap-4 text-[14px]"><span>fixed price <span className="block text-[12px] text-quiet">empty: worked out by the rule</span></span>
          <span className="text-quiet">₹ <input type="number" step="10" value={fixed} onChange={(e) => setFixed(e.target.value)} className={`${field} w-32 text-right`} /></span>
        </label>
        <p className="text-[14px]">sells at <span className="tnum text-[20px] font-bold">{Number.isFinite(price) ? `₹${price.toLocaleString("en-IN")}` : "–"}</span>
          {price !== p.price && Number.isFinite(price) ? <span className="text-quiet"> (now ₹{p.price.toLocaleString("en-IN")})</span> : null}
          <span className="block text-[12px] text-quiet">leaves {Number.isFinite(price - c) ? `₹${(Math.round((price - c) * 100) / 100).toLocaleString("en-IN")}` : "–"} a shirt before post and the payment fee</span></p>
      </fieldset>

      <fieldset className="grid gap-2">
        <legend className="mb-2 text-[12px] font-semibold uppercase tracking-[0.12em] text-quiet">qikink sku per size</legend>
        <p className="text-[12px] text-quiet">from qikink → my products. a size without one can&apos;t be bought.</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {SIZE_ORDER.map((z) => (
            <label key={z} className="flex items-center gap-3 text-[14px]"><span className="w-8">{z}</span>
              <input value={skus[z] ?? ""} onChange={(e) => setSkus({ ...skus, [z]: e.target.value })} maxLength={80} spellCheck={false} className={`${field} min-w-0 flex-1 font-mono text-[13px]`} />
            </label>
          ))}
        </div>
      </fieldset>

      <div className="flex flex-wrap items-center gap-3">
        {confirm ? (
          <>
            <span className="text-[13px]">save {changes.join(", ")}{patch.status ? ` (${status})` : ""}{price !== p.price ? `: it sells at ₹${price.toLocaleString("en-IN")} from now` : ""}?</span>
            <button type="button" disabled={busy} onClick={save} className={BTN.main}>{busy ? "saving…" : "yes, save"}</button>
            <button type="button" onClick={() => setConfirm(false)} className={BTN.plain}>no</button>
          </>
        ) : (
          <button type="button" disabled={!changes.length || !Number.isFinite(price) || !wordsOk} onClick={() => { setMsg(null); setConfirm(true); }} className={BTN.main}>save changes</button>
        )}
        {msg ? <span className={`text-[12px] ${msg.ok ? "text-[#8fd19e]" : "text-[#f08a7a]"}`}>{msg.text}</span> : null}
      </div>
    </div>
  );
}
