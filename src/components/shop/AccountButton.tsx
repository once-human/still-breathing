"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useShop } from "@/lib/shop/client";
import { useMe } from "@/lib/shop/me";

/**
 * The header's profile link, next to the bag: "sign in" when signed out; signed in, the person's first name.
 * Nothing while accounts aren't set up.
 */
export function AccountButton({ className = "" }: { className?: string }) {
  const { pay } = useShop();
  const me = useMe(usePathname());
  if (!pay?.accounts) return null;
  const label = me.signedIn ? (me.name ? me.name.toLowerCase() : "profile") : "sign in";
  return <Link href="/profile" className={`hit inline-block max-w-[12ch] truncate align-bottom hover:text-ink ${className}`}>{label}</Link>;
}
