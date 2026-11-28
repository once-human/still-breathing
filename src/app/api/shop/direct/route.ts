import { sessionEmail, validEmail } from "@/lib/shop/account";
import { failed, guardWrite, json, limited } from "@/lib/shop/guard";
import { noteDirect } from "@/lib/shop/inbox";
import { askedFrom } from "@/lib/visits/ua";

export const dynamic = "force-dynamic";

/** a note straight to the top: {name, email, order?, body}; 3 an hour from one connection, 5 a day from one email */
export async function POST(req: Request) {
  const g = await guardWrite(req, "direct", 3, 3_600_000, 8000);
  if ("fail" in g) return g.fail;
  const b = (g.body ?? {}) as Record<string, unknown>;
  if (typeof b.website === "string" && b.website) return json({ ok: true }); // the box only bots fill in
  const s = (v: unknown, max: number) => (typeof v === "string" ? v.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, "").trim().slice(0, max) : "");
  const name = s(b.name, 80).replace(/\s+/g, " "), email = s(b.email, 120).toLowerCase(), body = s(b.body, 5000);
  const order = s(b.order, 20).replace(/^#/, "").toUpperCase() || null;
  if (name.length < 2) return json({ error: "your name", field: "name" }, 400);
  if (!validEmail(email)) return json({ error: "an email to write back to", field: "email" }, 400);
  if (order && !/^S\d{6}[A-Z0-9]{4}$/.test(order)) return json({ error: "the order number from your order email, like S2611281A2B", field: "order" }, 400);
  if (body.length < 10) return json({ error: "what's happened, in a few words", field: "body" }, 400);
  if (await limited(`direct-email:${email}`, 5, 86_400_000)) return json({ error: "your notes have arrived: you'll hear back soon" }, 429);
  try {
    const me = await sessionEmail().catch(() => null);
    await noteDirect({ name, email, order, body, device: askedFrom(req), signedIn: me === email });
    return json({ ok: true });
  } catch (e) {
    return failed(e);
  }
}
