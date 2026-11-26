"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { shopOpen } from "@/lib/shop/config";
import { clientIp, limited } from "@/lib/shop/guard";
import { loadOrder, orderPath, validId } from "@/lib/shop/orders";

export type FindState = { error: string | null };

/**
 * Order number + email → that order's page. Tight limits per IP (5 a minute, 30 an hour), and one answer for every
 * miss, so it can't be used to find out which numbers or emails exist. Next checks a server action's origin itself.
 */
export async function findOrder(_: FindState, form: FormData): Promise<FindState> {
  if (!shopOpen()) return { error: "couldn't look it up just now. try again in a minute" };
  const ip = clientIp(await headers()) ?? "?";
  if ((await limited(`find:${ip}`, 5, 60_000)) || (await limited(`find-h:${ip}`, 30, 3_600_000))) return { error: "too many tries. wait a few minutes and try again" };
  const id = String(form.get("number") ?? "").trim().toUpperCase().replace(/^#/, "");
  const email = String(form.get("email") ?? "").trim().toLowerCase();
  if (!validId(id) || email.length > 200) return { error: "check the order number: it's in your order email, like #S261126K7QX" };
  let ok = false;
  try {
    const o = await loadOrder(id);
    ok = !!o && o.stage !== "paying" && o.contact.email === email;
  } catch (e) {
    console.error("order find:", e instanceof Error ? e.message : e);
    return { error: "couldn't look it up just now. try again in a minute" };
  }
  if (!ok) return { error: "no order with that number and email" };
  redirect(orderPath(id));
}
