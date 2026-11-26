"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { ordersOpen } from "@/lib/shop/config";
import { clientIp, limited } from "@/lib/shop/guard";
import { keyFor, orderNumber } from "@/lib/shop/orders";

export type FindState = { error: string | null };

/**
 * Order number + email → that order's page. Tight limits per IP (5 a minute, 30 an hour), and one answer for every
 * miss, so it can't be used to test which numbers or emails exist. Next checks a server action's Origin itself.
 */
export async function findOrder(_: FindState, form: FormData): Promise<FindState> {
  if (!ordersOpen()) return { error: "orders open with the shop" };
  const h = await headers();
  const ip = clientIp(h) ?? "?";
  if (limited(`find:${ip}`, 5, 60_000) || limited(`find-h:${ip}`, 30, 3_600_000)) return { error: "too many tries. wait a few minutes and try again" };
  const number = orderNumber(String(form.get("number") ?? ""));
  const email = String(form.get("email") ?? "").trim();
  if (!number || email.length > 200 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return { error: "check the order number and the email" };
  let key: string | null = null;
  try {
    key = await keyFor(number, email);
  } catch (e) {
    console.error("order find:", e instanceof Error ? e.message : e);
    return { error: "couldn't look it up just now. try again in a minute" };
  }
  if (!key) return { error: "no order with that number and email. the number is in your order email, like #1001" };
  redirect(`/order/${number}?k=${encodeURIComponent(key)}`);
}
