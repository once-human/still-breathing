import { audit } from "@/lib/admin/auth";
import { allOrders, costs, istDay, marginOf, knownFees, shirtName } from "@/lib/admin/data";
import { refunded } from "@/lib/shop/orders";
import { adminRead } from "@/lib/admin/guard";
import { getSettings } from "@/lib/admin/settings";
import { ipOf } from "@/lib/shop/guard";

export const dynamic = "force-dynamic";

const cell = (v: unknown) => {
  const s = v == null ? "" : String(v);
  // quoted, and a leading = + - @ neutralised so a spreadsheet never runs it as a formula
  return `"${(/^[=+\-@\t\r]/.test(s) ? "'" + s : s).replace(/"/g, '""')}"`;
};

/** every paid order as CSV (the same filters as the list: stage, shirt, size, from, to, q) */
export async function GET(req: Request) {
  const g = await adminRead();
  if ("fail" in g) return g.fail;
  const p = new URL(req.url).searchParams;
  const [orders, s, fees, c] = await Promise.all([allOrders(), getSettings(), knownFees(), costs()]);
  const q = p.get("q")?.toLowerCase().trim();
  const list = orders.filter((o) => {
    const st = p.get("stage");
    if (st === "open" ? !["paid", "printing", "shipped", "out", "attention"].includes(o.stage) : st ? o.stage !== st : o.stage === "paying") return false;
    if (p.get("shirt") && !o.lines.some((l) => l.design === p.get("shirt"))) return false;
    if (p.get("size") && !o.lines.some((l) => l.size === p.get("size"))) return false;
    const day = istDay(o.createdAt);
    if (p.get("from") && day < p.get("from")!) return false;
    if (p.get("to") && day > p.get("to")!) return false;
    return !q || JSON.stringify([o.id, o.contact, o.ship.city, o.ship.pin, o.payment?.id, o.partnerId, o.tracking?.awb]).toLowerCase().includes(q);
  });
  const head = ["order", "placed", "paid", "stage", "name", "email", "phone", "address", "city", "state", "pin", "items", "total", "refund", "payment", "razorpay order", "razorpay payment", "fee", "qikink cost", "post", "margin", "qikink id", "courier", "awb"];
  const lines = list.map((o) => {
    const m = marginOf(o, s, c, fees.get(o.id));
    return [o.id, o.createdAt, o.paidAt, o.stage, o.contact.name, o.contact.email, o.contact.phone, [o.ship.address1, o.ship.address2].filter(Boolean).join(", "), o.ship.city, o.ship.state, o.ship.pin,
      o.lines.map((l) => `${shirtName(l.design)} ${l.size} x${l.quantity}`).join("; "), o.total, refunded(o) || "", o.payment?.label, o.rzpOrderId, o.payment?.id, m?.fee, m?.cost, m?.ship, m?.margin, o.partnerId, o.tracking?.courier, o.tracking?.awb].map(cell).join(",");
  });
  await audit(g.admin.email, "orders.export", null, { rows: list.length }, ipOf(req));
  return new Response("﻿" + [head.map(cell).join(","), ...lines].join("\r\n"), {
    headers: { "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": `attachment; filename="sahn-orders-${new Date().toISOString().slice(0, 10)}.csv"`, "Cache-Control": "no-store, private" },
  });
}
