"use client";

import { useEffect, useState } from "react";
import { SIZE_ORDER, type Size } from "@/content/tee";
import type { Pose, Variant } from "@/lib/viewer/raster";
import type { V3 } from "@/lib/viewer/scene";

/** The five simulated bodies (Indian adult anthropometry) and the three sizes each was sewn into. */
export const BODIES = [
  { id: "m163", sex: "m", height: 163, chest: 86, sizes: ["XS", "S", "M"] },
  { id: "m170", sex: "m", height: 170, chest: 94, sizes: ["S", "M", "L"] },
  { id: "m177", sex: "m", height: 177, chest: 104, sizes: ["L", "XL", "2XL"] },
  { id: "f155", sex: "f", height: 155, chest: 84, sizes: ["XS", "S", "M"] },
  { id: "f162", sex: "f", height: 162, chest: 92, sizes: ["S", "M", "L"] },
] as const;
type Body = (typeof BODIES)[number];

const SKINS: { name: string; lin: V3; hex: string }[] = [
  { name: "wheatish", lin: [0.45, 0.27, 0.17], hex: "#b98d6e" },
  { name: "brown", lin: [0.3, 0.16, 0.095], hex: "#93694f" },
  { name: "deep", lin: [0.15, 0.078, 0.045], hex: "#6a4a37" },
];
const POSES: { id: Pose; label: string }[] = [{ id: "stand", label: "standing" }, { id: "up", label: "hands up" }, { id: "sit", label: "sitting" }];
export const SHOP: Variant = { dir: "form-M", size: "M", pose: "stand", body: false };

type FitData = {
  size: string; body: { height_cm: number; chest_cm: number }; chest_ease_cm: number;
  poses: { stand?: { hem_below_crotch_cm: number; sleeve_above_elbow_cm: number; hem_vs_waistband_cm: number };
    up?: { hem_rise_cm: number | null; hem_vs_waistband_cm: number }; sit?: { back_hem_vs_waistband_cm: number; seat_cm: number } };
};

/** Chest girth from height and weight, through BMI: fitted to the five bodies (men 2.2 x BMI + 46, women 2.0 x BMI + 45). */
function chestFrom(sex: "m" | "f", h: number, kg: number) {
  const bmi = kg / (h / 100) ** 2;
  return sex === "m" ? 2.2 * bmi + 46 : 2.0 * bmi + 45;
}
function nearest(sex: "m" | "f", h: number, chest: number): Body {
  return BODIES.filter((b) => b.sex === sex).reduce((best, b) =>
    Math.abs(b.height - h) / 6 + Math.abs(b.chest - chest) / 4 < Math.abs(best.height - h) / 6 + Math.abs(best.chest - chest) / 4 ? b : best);
}
function closestSize(want: Size, have: readonly string[]) {
  const i = SIZE_ORDER.indexOf(want);
  return [...have].sort((a, b) => Math.abs(SIZE_ORDER.indexOf(a as Size) - i) - Math.abs(SIZE_ORDER.indexOf(b as Size) - i))[0] as Size;
}

/** Plain words for what the simulation measured. */
function words(f: FitData, pose: Pose): string[] {
  const e = f.chest_ease_cm, out: string[] = [];
  out.push(e < 12 ? `${e} cm of room round the chest: close, not the oversized look` : e <= 24 ? `${e} cm of room round the chest: the loose, straight fall it's cut for` : `${e} cm of room round the chest: big and boxy`);
  const st = f.poses.stand, up = f.poses.up, sit = f.poses.sit;
  if (pose === "stand" && st) {
    out.push(st.hem_below_crotch_cm >= 0 ? `the hem falls ${st.hem_below_crotch_cm} cm below the crotch` : `the hem stops ${-st.hem_below_crotch_cm} cm above the crotch`);
    out.push(st.sleeve_above_elbow_cm > 1 ? `the sleeves end ${st.sleeve_above_elbow_cm} cm above the elbow` : "the sleeves reach the elbow");
  }
  if (pose === "up" && up) {
    const rise = up.hem_rise_cm ?? 0, w = up.hem_vs_waistband_cm;
    out.push(w > 0 ? `hands up, the hem rises ${rise} cm and shows about ${w} cm of you above a jeans waistband` : `hands up, the hem rises ${rise} cm and still covers a jeans waistband by ${-w} cm`);
  }
  if (pose === "sit" && sit) {
    const w = sit.back_hem_vs_waistband_cm;
    out.push(w > 0 ? `sitting, the back rides up ${w} cm past the waistband` : `sitting, the back still covers the waistband by ${-w} cm`);
  }
  return out;
}

/**
 * Fit mode: tell it roughly who you are, and the tee is shown sewn onto the nearest of five simulated Indian
 * bodies, in your size, standing, with hands up at the show, or sitting.
 */
export function Fit({ size, onVariant }: { size: Size; onVariant: (v: Variant) => void }) {
  const [on, setOn] = useState(false);
  const [sex, setSex] = useState<"m" | "f">("m");
  const [height, setHeight] = useState(170);
  const [weight, setWeight] = useState(65);
  const [skin, setSkin] = useState(1);
  const [pose, setPose] = useState<Pose>("stand");
  const [index, setIndex] = useState<Record<string, FitData> | null>(null);

  const body = nearest(sex, height, chestFrom(sex, height, weight));
  const shown = closestSize(size, body.sizes);
  const dir = `${body.id}-${shown}`;
  const data = index?.[dir];

  useEffect(() => { if (on && !index) fetch("/tee/fit/index.json").then((r) => r.json()).then(setIndex).catch(() => setIndex({})); }, [on, index]);
  const seat = data?.poses.sit?.seat_cm;
  useEffect(() => {
    onVariant(on ? { dir, size: shown, pose, body: true, skin: SKINS[skin].lin, seat: seat ? seat / 100 : undefined } : SHOP);
  }, [on, dir, shown, pose, skin, seat]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="mt-8 border-t border-line pt-1.5 text-[13px]">
      <div className="flex items-baseline justify-between">
        <p className="text-quiet">fit</p>
        <button onClick={() => setOn(!on)} aria-pressed={on} className={on ? "font-semibold" : "text-blue hover:text-ink"}>{on ? "back to the tee" : "see it on a body like yours →"}</button>
      </div>
      {on ? (
        <div className="mt-3 space-y-3">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            {(["m", "f"] as const).map((x) => (
              <button key={x} onClick={() => setSex(x)} className={x === sex ? "font-semibold" : "text-quiet hover:text-ink"}>{x === "m" ? "man" : "woman"}</button>
            ))}
            <label className="flex items-baseline gap-1.5 tnum">
              <input type="number" inputMode="numeric" min={140} max={200} value={height} onChange={(e) => setHeight(+e.target.value || 0)} className="w-14 border-b border-line bg-transparent text-[15px] font-semibold outline-none focus:border-ink" />
              <span className="text-quiet">cm tall</span>
            </label>
            <label className="flex items-baseline gap-1.5 tnum">
              <input type="number" inputMode="numeric" min={35} max={150} value={weight} onChange={(e) => setWeight(+e.target.value || 0)} className="w-12 border-b border-line bg-transparent text-[15px] font-semibold outline-none focus:border-ink" />
              <span className="text-quiet">kg</span>
            </label>
            <span className="ml-auto flex gap-1.5" role="group" aria-label="Skin">
              {SKINS.map((k, i) => (
                <button key={k.name} onClick={() => setSkin(i)} aria-label={k.name} aria-pressed={i === skin}
                  className={`h-5 w-5 rounded-full border ${i === skin ? "border-ink ring-1 ring-ink ring-offset-1 ring-offset-paper" : "border-line"}`} style={{ background: k.hex }} />
              ))}
            </span>
          </div>
          <div className="flex gap-4" role="group" aria-label="Pose">
            {POSES.map((p) => (
              <button key={p.id} onClick={() => setPose(p.id)} className={p.id === pose ? "font-semibold" : "text-quiet hover:text-ink"}>{p.label}</button>
            ))}
          </div>
          <p className="text-quiet">
            shown on {sex === "m" ? "a man" : "a woman"}, {body.height} cm, chest {body.chest} cm, in {shown}
            {shown !== size ? `. ${size} on this body isn't simulated yet, so this is the nearest size` : ""}.
          </p>
          {data ? (
            <ul className="space-y-1">{words(data, pose).map((w) => <li key={w}>{w}</li>)}</ul>
          ) : index ? <p className="text-quiet">this body is still being simulated.</p> : null}
        </div>
      ) : null}
    </div>
  );
}
