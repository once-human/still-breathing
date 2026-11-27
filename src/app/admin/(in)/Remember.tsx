"use client";

import { useEffect } from "react";

/** keeps the period you picked for next time (a cookie only the admin reads) */
export function Remember({ name, value }: { name: string; value: string }) {
  useEffect(() => {
    document.cookie = `${name}=${encodeURIComponent(value)}; path=/admin; max-age=31536000; samesite=strict; secure`;
  }, [name, value]);
  return null;
}
