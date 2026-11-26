"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

/**
 * The site's own visit counter: one small request per page seen, to /api/e. No cookie, nothing kept in the browser,
 * nothing sent to anyone else. Do Not Track and Global Privacy Control turn it off. The admin pages aren't counted.
 */
const off = () => {
  if (typeof navigator === "undefined") return true;
  const n = navigator as Navigator & { globalPrivacyControl?: boolean };
  return n.globalPrivacyControl === true || n.doNotTrack === "1";
};

function send(body: Record<string, string | undefined>) {
  if (off()) return;
  const data = JSON.stringify(body);
  if (!navigator.sendBeacon?.("/api/e", data)) fetch("/api/e", { method: "POST", body: data, keepalive: true }).catch(() => {});
}

/** a shop moment: something put in the bag, or checkout opened */
export function track(k: "bag" | "checkout", d?: string, s?: string) {
  send({ k, p: location.pathname, d, s });
}

let first = true;

export function Beacon() {
  const path = usePathname();
  useEffect(() => {
    if (!path || path.startsWith("/admin")) return;
    const utm = new URLSearchParams(location.search).get("utm_source") ?? undefined;
    // the referrer only on the first page of a visit; after that it's our own site
    const ref = first && document.referrer && !document.referrer.startsWith(location.origin) ? document.referrer : undefined;
    first = false;
    send({ k: "view", p: path, r: ref, u: utm });
    if (path === "/checkout") track("checkout");
  }, [path]);
  return null;
}
