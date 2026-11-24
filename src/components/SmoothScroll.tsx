"use client";

import Lenis from "lenis";
import { useEffect } from "react";

/** Lenis, as on 1618. The studio stage stops it while you drag the tee. */
export function SmoothScroll() {
  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const lenis = new Lenis({ lerp: 0.12, prevent: (node) => !!node.closest?.("[data-lenis-prevent]") });
    let id = requestAnimationFrame(function raf(t) { lenis.raf(t); id = requestAnimationFrame(raf); });
    return () => { cancelAnimationFrame(id); lenis.destroy(); };
  }, []);
  return null;
}
