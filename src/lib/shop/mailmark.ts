import { SITE_URL } from "@/lib/site";

/**
 * How every email from the shop ends. Two kinds:
 *   footer()   the shop's own mail (orders, codes, drops, replies from hello@ and the rest): a thin rule, the sahn
 *              wordmark (text, so no mail app hides it as a blocked image) and a quiet line of the few links people
 *              need; bulk mail adds its one-tap way off here.
 *   personal() mail from the owner's own address: his name beside a slim bar, the mark and sahn.in under it. No rule,
 *              no link row, so it reads like a person signing off, not the shop.
 */
const site = () => (process.env.SHOP_SITE_URL?.trim() || SITE_URL).replace(/\/$/, "");
const host = () => site().replace(/^https?:\/\/(www\.)?/, "");
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const MARK = "font-family:Helvetica,Arial,sans-serif;font-weight:800;letter-spacing:-0.05em;color:#111;text-decoration:none";

export type Off = { url: string; why: string };

export function footer(off?: Off | null) {
  const s = site();
  const links: [string, string][] = [["shop", `${s}/shop`], ["your order", `${s}/order`], ["help", `${s}/help`], ["contact", `${s}/contact`]];
  const text = `—\nsahn · ${host()}\nhelp: ${s}/help${off ? `\n\n${off.why} stop these emails: ${off.url}` : ""}`;
  const html = `<div style="margin-top:32px;padding-top:14px;border-top:1px solid #e6e6e6;font-family:Helvetica,Arial,sans-serif">`
    + `<a href="${esc(s)}" style="${MARK};font-size:20px;line-height:1">sahn</a>`
    + `<p style="margin:8px 0 0;font-size:12px;line-height:1.5;color:#8a8a8a">${links.map(([l, u]) => `<a href="${esc(u)}" style="color:#8a8a8a;text-decoration:none">${l}</a>`).join(" &nbsp;·&nbsp; ")}</p>`
    + (off ? `<p style="margin:10px 0 0;font-size:12px;line-height:1.5;color:#8a8a8a">${esc(off.why)} <a href="${esc(off.url)}" style="color:#8a8a8a">stop these emails</a>.</p>` : "")
    + `</div>`;
  return { text, html };
}

export function personal(name = "Onkar", off?: Off | null) {
  const s = site();
  const text = `${name}\nsahn · ${host()}${off ? `\n\n—\n${off.why} stop these emails: ${off.url}` : ""}`;
  const html = `<div style="margin-top:28px;padding-left:12px;border-left:2px solid #111;font-family:Helvetica,Arial,sans-serif">`
    + `<p style="margin:0;font-size:15px;line-height:1.3;font-weight:600;color:#111">${esc(name)}</p>`
    + `<p style="margin:3px 0 0;font-size:13px;line-height:1.3;color:#777"><a href="${esc(s)}" style="${MARK};font-size:14px">sahn</a> &nbsp;·&nbsp; <a href="${esc(s)}" style="color:#777;text-decoration:none">${esc(host())}</a></p>`
    + `</div>`
    + (off ? `<p style="margin:24px 0 0;font-size:12px;line-height:1.5;color:#8a8a8a;font-family:Helvetica,Arial,sans-serif">${esc(off.why)} <a href="${esc(off.url)}" style="color:#8a8a8a">stop these emails</a>.</p>` : "");
  return { text, html };
}

/** the right ending for mail from this box */
export const signature = (local: string, owner: string, off?: Off | null) => (local === owner ? personal("Onkar", off) : footer(off));
