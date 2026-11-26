import { accountOrders, loadAccount, saveAccount, sendCode, sessionEmail, signOut, validEmail, verifyCode } from "@/lib/shop/account";
import { accountsOpen } from "@/lib/shop/config";
import { failed, guardWrite, json, limited } from "@/lib/shop/guard";
import { checkDetails } from "@/lib/shop/india";
import { randomBytes } from "node:crypto";

export const dynamic = "force-dynamic";

/**
 * The account, one route, by `action`:
 *   code {email}           email a 6-digit sign-in code (always "sent", so it can't tell which emails have accounts)
 *   verify {email, code}   the code → a 30-day session cookie
 *   signout
 *   profile {name, phone}  (signed in)
 *   add-address {details}, remove-address {id}  (signed in)
 */
export async function POST(req: Request) {
  if (!accountsOpen()) return json({ error: "accounts aren't open right now" }, 503);
  const g = await guardWrite(req, "account", 30, 10 * 60_000);
  if ("fail" in g) return g.fail;
  const b = (g.body ?? {}) as Record<string, unknown>;
  const email = typeof b.email === "string" ? b.email.trim().toLowerCase() : "";
  try {
    switch (b.action) {
      case "code": {
        if (!validEmail(email)) return json({ error: "an email we can send the code to", field: "email" }, 400);
        if (await limited(`acct-code:${email}`, 5, 3_600_000)) return json({ ok: true });
        await sendCode(email);
        return json({ ok: true });
      }
      case "verify": {
        const code = typeof b.code === "string" ? b.code.replace(/\D/g, "") : "";
        if (!validEmail(email)) return json({ error: "put your email in again" }, 400);
        if (!(await verifyCode(email, code))) return json({ error: "that code isn't right, or it's run out. ask for a new one", field: "code" }, 400);
        return json({ ok: true });
      }
      case "signout":
        await signOut();
        return json({ ok: true });
    }
    const me = await sessionEmail();
    if (!me) return json({ error: "sign in again" }, 401);
    const a = await loadAccount(me);
    if (!a) return json({ error: "sign in again" }, 401);
    switch (b.action) {
      case "profile": {
        const name = typeof b.name === "string" ? b.name.replace(/[\u0000-\u001f<>]/g, " ").replace(/\s+/g, " ").trim().slice(0, 80) : "";
        const phone = typeof b.phone === "string" ? b.phone.replace(/[\s-]/g, "").replace(/^(\+91|0091|91(?=\d{10}$)|0)/, "") : "";
        if (name && (name.length < 2 || !/\p{L}/u.test(name))) return json({ error: "your name, as the courier should read it", field: "name" }, 400);
        if (phone && !/^[6-9]\d{9}$/.test(phone)) return json({ error: "a 10-digit indian mobile number", field: "phone" }, 400);
        await saveAccount({ ...a, name, phone });
        return json({ ok: true });
      }
      case "add-address": {
        const d = checkDetails({ ...(b.details as object), email: me });
        if ("error" in d) return json({ error: d.error, field: d.field }, 400);
        const { email: _e, ...rest } = d.ok;
        void _e;
        if (a.addresses.length >= 5) return json({ error: "five addresses at most: remove one first" }, 400);
        await saveAccount({ ...a, addresses: [...a.addresses, { ...rest, id: randomBytes(4).toString("hex") }] });
        return json({ ok: true });
      }
      case "remove-address":
        await saveAccount({ ...a, addresses: a.addresses.filter((x) => x.id !== b.id) });
        return json({ ok: true });
      case "orders":
        return json({ ids: await accountOrders(me) });
    }
    return json({ error: "unknown action" }, 400);
  } catch (e) {
    return failed(e);
  }
}
