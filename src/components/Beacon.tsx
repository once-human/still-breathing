"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { startTracking, trackPage, trackStep } from "@/lib/visits/client";
import type { Step } from "@/lib/visits/shared";

/**
 * The site's own visitor log (src/lib/visits): pages, time on them, how far down, links out and the shop's steps,
 * sent only to this site. Do Not Track, Global Privacy Control and the switch on the privacy page turn it off. The
 * admin pages aren't logged.
 */
export function track(k: Step, d?: string, s?: string, x?: string) {
  trackStep(k, d, s, x);
}

export function Beacon() {
  const path = usePathname();
  useEffect(() => {
    if (!path || path.startsWith("/admin")) return;
    startTracking();
    trackPage(path);
    if (path === "/checkout") track("checkout");
  }, [path]);
  return null;
}
