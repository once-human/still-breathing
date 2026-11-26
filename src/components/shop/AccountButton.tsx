"use client";

import Link from "next/link";
import { useShop } from "@/lib/shop/client";

/** The header's "account", next to the bag: sign in, profile, addresses, every order. Nothing while accounts aren't set up. */
export function AccountButton({ className = "" }: { className?: string }) {
  const { pay } = useShop();
  if (!pay?.accounts) return null;
  return <Link href="/account" className={`hit hover:text-ink ${className}`}>account</Link>;
}
