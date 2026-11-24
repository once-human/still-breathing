"use client";

import { useState } from "react";
import { Viewer } from "@/components/Viewer";
import { Countdown } from "@/components/Countdown";
import { Fit, SHOP } from "@/components/Fit";
import type { Variant } from "@/lib/viewer/raster";
import { COLOURS, DESIGNS, SIZES, SIZE_ORDER, SHOWS, THE_TEE, type Design, type Size } from "@/content/tee";

const fmtDays = (days: string[]) => days.map((d) => d.slice(8, 10)).join("+") + "." + days[0].slice(5, 7);

/** The tee and its sheet, side by side: what you pick on the right is what you see on the left. */
export function Product() {
  const [design, setDesign] = useState<Design>("b");
  const tee = DESIGNS[design].colour;
  const [size, setSize] = useState<Size>("M");
  const [variant, setVariant] = useState<Variant>(SHOP);
  const z = SIZES[size];
  return (
    <section id="studio" className="grid scroll-mt-14 grid-cols-1 gap-x-4 gap-y-8 px-4 md:grid-cols-12">
      <div className="md:col-span-7 lg:col-span-6 lg:col-start-2">
        <Viewer design={design} tee={tee} variant={variant} />
      </div>
      <div className="md:col-span-5 lg:col-span-4 lg:col-start-9">
        <div className="md:sticky md:top-16">
          <p className="border-t border-line pt-1.5 text-[13px] text-quiet">{THE_TEE.lineup} · the india shows, december</p>
          <div className="mt-4 flex gap-5 text-[15px]" role="group" aria-label="Design">
            {(Object.keys(DESIGNS) as Design[]).map((d) => (
              <button key={d} onClick={() => setDesign(d)} aria-pressed={d === design} className={`flex items-baseline gap-1.5 ${d === design ? "text-ink" : "text-quiet hover:text-ink"}`}>
                <span className="text-[11px] tnum">{DESIGNS[d].no}</span>
                <span className={d === design ? "border-b border-blue font-semibold" : ""}>{DESIGNS[d].name}</span>
              </button>
            ))}
          </div>
          <h1 className="mt-6 text-[44px] leading-[0.9] font-extrabold tracking-[-0.04em] lg:text-[64px]">
            {THE_TEE.name}<span className="block text-quiet">{DESIGNS[design].name}</span>
          </h1>
          <p className="mt-5 max-w-[34ch] text-ink/85">{THE_TEE.lede}</p>
          <p className="mt-3 max-w-[34ch] text-[13px] text-quiet">back: {DESIGNS[design].back}.</p>

          <p className="mt-6 flex items-center gap-2 text-[13px]">
            <span className="inline-block h-3 w-3 rounded-full border border-line" style={{ background: COLOURS[tee].hex }} />
            <span>{COLOURS[tee].name}<span className="text-quiet">, the only colour this one comes in</span></span>
          </p>

          <div className="mt-10 border-t border-line pt-1.5">
            <p className="text-[13px] text-quiet">size · {size}</p>
            <div className="mt-3 grid grid-cols-6 gap-1.5">
              {SIZE_ORDER.map((s) => (
                <button key={s} onClick={() => setSize(s)} aria-pressed={s === size}
                  className={`h-10 border text-[14px] transition ${s === size ? "border-ink bg-ink text-paper" : "border-line hover:border-quiet"}`}>{s}</button>
              ))}
            </div>
            <dl className="mt-4 grid grid-cols-3 gap-2 text-[13px] tnum">
              <div><dt className="text-quiet">chest</dt><dd className="text-[20px] font-semibold">{z.chest_round}<span className="text-[13px] font-normal text-quiet"> cm</span></dd></div>
              <div><dt className="text-quiet">length</dt><dd className="text-[20px] font-semibold">{z.length}<span className="text-[13px] font-normal text-quiet"> cm</span></dd></div>
              <div><dt className="text-quiet">shoulder</dt><dd className="text-[20px] font-semibold">{z.shoulder}<span className="text-[13px] font-normal text-quiet"> cm</span></dd></div>
            </dl>
            <p className="mt-2 text-[12px] text-quiet">measured on the garment, around the chest. it&apos;s cut big: most people take their usual size.</p>
          </div>

          <Fit size={size} onVariant={setVariant} />

          <div className="mt-8 border-t border-line pt-1.5 text-[13px]">
            <p className="text-quiet">the shows</p>
            <ul className="mt-2 space-y-0.5 tnum">
              {SHOWS.map((s) => (
                <li key={s.city} className="flex justify-between"><span>{s.city}</span><span className="text-quiet">{fmtDays(s.days)}</span></li>
              ))}
            </ul>
            <p className="mt-3 flex items-center gap-2"><span className="inline-block h-1.5 w-1.5 rounded-full bg-blue" /><Countdown /></p>
          </div>
        </div>
      </div>
    </section>
  );
}
