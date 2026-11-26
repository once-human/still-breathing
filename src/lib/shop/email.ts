import { mailKeys } from "./config";
import { ShopError } from "./errors";

/**
 * Order emails, sent through Resend from the shop's own address on sahn.in. Each send carries an idempotency key, so
 * a retried job can't send the same email twice.
 */
export async function sendEmail(to: string, subject: string, text: string, idempotencyKey: string, replyTo?: string | null) {
  const k = mailKeys();
  if (!k) throw new ShopError("email not set up", 503);
  const html = `<div style="font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;color:#111;max-width:520px">${text
    .split("\n\n")
    .map((p) => `<p>${esc(p).replace(/\n/g, "<br>").replace(/(https:\/\/[^\s<]+)/g, '<a href="$1">$1</a>')}</p>`)
    .join("")}</div>`;
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${k.key}`, "Content-Type": "application/json", "Idempotency-Key": idempotencyKey.slice(0, 256) },
    body: JSON.stringify({ from: k.from, to: [to], subject, text, html, ...(replyTo ? { reply_to: replyTo } : {}) }),
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
  }).catch(() => null);
  if (!res?.ok) throw new ShopError(`email ${res?.status ?? "unreachable"}: ${(await res?.text().catch(() => "")) ?? ""}`.slice(0, 300));
}

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
