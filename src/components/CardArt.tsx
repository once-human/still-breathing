"use client";

import { useEffect, useRef, useState } from "react";
import { COLOURS, DESIGNS, type Design } from "@/content/tee";
import { printArt } from "@/content/lineups";

/**
 * A shirt card's hover: the print itself on the shirt's own colour, no tee shape, no collar. Each side's whole print
 * area is shown uncropped and both at one scale (front 30 x 50 cm, back 34.3 x 45.7 cm), so a small chest mark reads as
 * small and the back as big. The front for about two seconds while it slowly comes closer, then the back, and round
 * again (globals.css .art-*). Its pictures load the first time a pointer or keyboard reaches the card.
 */
export function CardArt({ d }: { d: Design }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    const card = ref.current?.closest("a");
    if (!card || armed) return;
    const arm = () => setArmed(true);
    card.addEventListener("pointerenter", arm);
    card.addEventListener("focusin", arm);
    return () => { card.removeEventListener("pointerenter", arm); card.removeEventListener("focusin", arm); };
  }, [armed]);
  return (
    <span ref={ref} aria-hidden className="art-layer absolute inset-0 overflow-hidden" style={{ background: COLOURS[DESIGNS[d].colour].hex }}>
      {armed ? (
        <>
          {/* one scale: the front's area is 50 cm tall in 86 % of the box, so the 45.7 cm back takes 78.6 % */}
          <img src={printArt(d, "front")} alt="" decoding="async" className="art-front absolute inset-x-0 top-[7%] mx-auto h-[86%] w-auto" />
          <img src={printArt(d, "back")} alt="" decoding="async" className="art-back absolute inset-x-0 top-[7%] mx-auto h-[78.6%] w-auto" />
        </>
      ) : null}
    </span>
  );
}
