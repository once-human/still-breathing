import { BOXES, type Box } from "@/content/mail";
import { mailKeys } from "./config";
import { ShopError } from "./errors";

/** "sahn orders <orders@sahn.in>": a named sender on the verified domain; any name@ works, the shop's boxes have their own names */
export function sender(local: Box | string, name?: string) {
  const k = mailKeys();
  if (!k) throw new ShopError("email not set up", 503);
  const shown = (name ?? (local in BOXES ? BOXES[local as Box].name : "sahn")).replace(/["<>\r\n]/g, "").trim() || "sahn";
  return { k, from: `${shown} <${local}@${k.domain}>`, address: `${local}@${k.domain}` };
}

/**
 * One email through Resend, from the box it belongs to (orders@ for an order, security@ for a code
 * or a notice). A reply goes back to that box, which lands in the shop's inbox like every sahn.in address. Each send carries
 * an idempotency key, so a retried job can't send the same email twice.
 */
export async function sendEmail(to: string, subject: string, text: string, idempotencyKey: string, from: Box = "orders", replyTo?: string | null) {
  const s = sender(from);
  const html = `<div style="font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;color:#111;max-width:520px">${text
    .split("\n\n")
    .map((p) => `<p>${esc(p).replace(/\n/g, "<br>").replace(/(https:\/\/[^\s<]+)/g, '<a href="$1">$1</a>')}</p>`)
    .join("")}</div>`;
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${s.k.key}`, "Content-Type": "application/json", "Idempotency-Key": idempotencyKey.slice(0, 256) },
    body: JSON.stringify({ from: s.from, to: [to], subject, text, html, reply_to: replyTo || s.address }),
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  }).catch(() => null);
  if (!res?.ok) throw new ShopError(`email ${res?.status ?? "unreachable"}: ${(await res?.text().catch(() => "")) ?? ""}`.slice(0, 300));
}

export const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
