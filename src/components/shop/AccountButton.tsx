"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useShop } from "@/lib/shop/client";

/** the plain "signed in" hint cookie the server sets beside the real (httpOnly) session; nothing personal in it */
const signedIn = () => typeof document !== "undefined" && /(?:^|;\s*)sahn_in=1/.test(document.cookie);

/**
 * The header's profile link, next to the bag: "sign in" when signed out; signed in, the person's first name
 * (asked of the server only when the hint says there's a session, and again on each page change). Nothing while
 * accounts aren't set up.
 */
export function AccountButton({ className = "" }: { className?: string }) {
  const { pay } = useShop();
  const path = usePathname();
  const [name, setName] = useState<string | null>(null);
  const [inNow, setIn] = useState(false);
  useEffect(() => {
    const on = signedIn();
    setIn(on);
    if (!on) return setName(null);
    let live = true;
    fetch("/api/shop/account", { cache: "no-store" })
      .then((r) => r.json() as Promise<{ signedIn: boolean; name?: string }>)
      .then((j) => { if (!live) return; setIn(j.signedIn); setName(j.signedIn ? j.name || "" : null); })
      .catch(() => {});
    return () => { live = false; };
  }, [path]);
  if (!pay?.accounts) return null;
  const label = inNow ? (name ? name.toLowerCase() : "profile") : "sign in";
  return <Link href="/profile" className={`hit inline-block max-w-[12ch] truncate align-bottom hover:text-ink ${className}`}>{label}</Link>;
}
