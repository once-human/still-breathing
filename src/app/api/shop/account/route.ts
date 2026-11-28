import { randomBytes } from "node:crypto";
import {
  accountOrders, activity, checkPassword, deleteAccount, devices, did, endDevice, loadAccount, openSession, passwordSetAt, removePassword,
  saveAccount, sendCode, sessionAge, sessionEmail, setPassword, signOut, signOutEverywhere, validEmail, verifyCode, weakPassword,
} from "@/lib/shop/account";
import { accountsOpen, googleKeys } from "@/lib/shop/config";
import { failed, guardWrite, ipOf, json, limited } from "@/lib/shop/guard";
import { checkDetails } from "@/lib/shop/india";
import { loadOrder, view } from "@/lib/shop/orders";
import { askedFrom } from "@/lib/visits/ua";

export const dynamic = "force-dynamic";

/** a sign-in only just made may set a new password without the old one (that's how a forgotten one is replaced) */
const FRESH_MS = 15 * 60_000;

/**
 * GET: the signed-in person's first name for the header ({ name } or { signedIn: false }); with ?export=1, everything
 * the shop keeps about them as a JSON file to save.
 */
export async function GET(req: Request) {
  if (!accountsOpen()) return json({ signedIn: false });
  const me = await sessionEmail().catch(() => null);
  if (!me) return json({ signedIn: false });
  const a = await loadAccount(me);
  if (new URL(req.url).searchParams.get("export") !== "1") return json({ signedIn: true, name: a?.name.split(" ")[0] ?? "" });
  const ids = await accountOrders(me).catch(() => []);
  const orders = (await Promise.all(ids.map((id) => loadOrder(id).catch(() => null)))).filter((o) => o && o.contact.email === me).map((o) => view(o!, true));
  const [list, events, pw] = await Promise.all([devices(me), activity(me, 1000), passwordSetAt(me)]);
  await did(me, "downloaded your data");
  const file = {
    exported: new Date().toISOString(),
    account: a,
    signIn: { emailCode: true, password: pw ? { setAt: pw } : null, google: a?.googleOff ? "off" : a?.google ? { firstUsed: a.google } : "not used yet" },
    devices: list.map(({ current: _c, ...d }) => d),
    orders,
    activity: events,
  };
  return new Response(JSON.stringify(file, null, 2), {
    headers: { "Content-Type": "application/json", "Content-Disposition": `attachment; filename="sahn-profile-${new Date().toISOString().slice(0, 10)}.json"`, "Cache-Control": "no-store" },
  });
}

/**
 * The profile, one route, by `action`:
 *   code {email}                 email a 6-digit sign-in code (always "sent", so it can't tell which emails have accounts)
 *   verify {email, code}         the code → a session; {fresh} if the account has no name yet
 *   password {email, password}   sign in with a password, for those who set one
 *   signout
 * signed in:
 *   profile {name, phone}; add-address {details}, remove-address {id}, default-address {id}
 *   set-password {password, current?}, remove-password {current?}
 *   google {on}                  allow or stop Google sign-in for this account
 *   end-device {id}, signout-all, delete
 */
export async function POST(req: Request) {
  if (!accountsOpen()) return json({ error: "accounts aren't open right now" }, 503);
  const g = await guardWrite(req, "account", 30, 10 * 60_000);
  if ("fail" in g) return g.fail;
  const b = (g.body ?? {}) as Record<string, unknown>;
  const email = typeof b.email === "string" ? b.email.trim().toLowerCase() : "";
  const device = askedFrom(req);
  try {
    switch (b.action) {
      case "code": {
        if (!validEmail(email)) return json({ error: "an email we can send the code to", field: "email" }, 400);
        if (await limited(`acct-code:${email}`, 5, 3_600_000)) return json({ ok: true });
        await sendCode(email, device);
        return json({ ok: true });
      }
      case "verify": {
        const code = typeof b.code === "string" ? b.code.replace(/\D/g, "") : "";
        if (!validEmail(email)) return json({ error: "put your email in again" }, 400);
        const v = await verifyCode(email, code, device);
        if (!v) return json({ error: "that code isn't right, or it's run out. ask for a new one", field: "code" }, 400);
        return json({ ok: true, fresh: v.fresh });
      }
      case "password": {
        const pw = typeof b.password === "string" ? b.password : "";
        if (!validEmail(email)) return json({ error: "your email", field: "email" }, 400);
        // 6 wrong tries an email in 15 minutes, 20 an hour from one connection: plenty for a person, nothing for a guesser
        if ((await limited(`acct-pw:${email}`, 6, 900_000)) || (await limited(`acct-pw-ip:${ipOf(req)}`, 20, 3_600_000)))
          return json({ error: "too many tries: wait a few minutes, or sign in with an email code" }, 429);
        if (!pw || pw.length > 128 || !(await checkPassword(email, pw))) return json({ error: "that email and password don't go together", field: "password" }, 400);
        const v = await openSession(email, "password", device);
        return json({ ok: true, fresh: v.fresh });
      }
      case "signout": {
        const me = await sessionEmail();
        if (me) await did(me, "signed out", device.split(", near")[0]);
        await signOut();
        return json({ ok: true });
      }
    }

    const me = await sessionEmail();
    if (!me) return json({ error: "sign in again" }, 401);
    const a = await loadAccount(me);
    if (!a) return json({ error: "sign in again" }, 401);
    const proven = async (current: unknown) =>
      (typeof current === "string" && current && (await checkPassword(me, current))) || (await sessionAge()) < FRESH_MS;

    switch (b.action) {
      case "profile": {
        const name = typeof b.name === "string" ? b.name.replace(/[\u0000-\u001f<>]/g, " ").replace(/\s+/g, " ").trim().slice(0, 80) : "";
        const phone = typeof b.phone === "string" ? b.phone.replace(/[\s-]/g, "").replace(/^(\+91|0091|91(?=\d{10}$)|0)/, "") : "";
        if (name && (name.length < 2 || !/\p{L}/u.test(name))) return json({ error: "your name, as the courier should read it", field: "name" }, 400);
        if (phone && !/^[6-9]\d{9}$/.test(phone)) return json({ error: "a 10-digit indian mobile number", field: "phone" }, 400);
        await saveAccount({ ...a, name, phone });
        const what = [name !== a.name ? "name" : "", phone !== a.phone ? "mobile" : ""].filter(Boolean).join(" and ");
        if (what) await did(me, `changed your ${what}`);
        return json({ ok: true });
      }
      case "add-address": {
        const d = checkDetails({ ...(b.details as object), email: me });
        if ("error" in d) return json({ error: d.error, field: d.field }, 400);
        const { email: _e, ...rest } = d.ok;
        void _e;
        if (a.addresses.length >= 5) return json({ error: "five addresses at most: remove one first" }, 400);
        await saveAccount({ ...a, addresses: [...a.addresses, { ...rest, id: randomBytes(4).toString("hex") }] });
        await did(me, "added an address", `${rest.city}, ${rest.pin}`);
        return json({ ok: true });
      }
      case "remove-address": {
        const x = a.addresses.find((y) => y.id === b.id);
        await saveAccount({ ...a, addresses: a.addresses.filter((y) => y.id !== b.id) });
        if (x) await did(me, "removed an address", `${x.city}, ${x.pin}`);
        return json({ ok: true });
      }
      case "default-address": {
        const x = a.addresses.find((y) => y.id === b.id);
        if (!x) return json({ error: "that address is gone: refresh the page" }, 400);
        await saveAccount({ ...a, addresses: [x, ...a.addresses.filter((y) => y.id !== x.id)] });
        await did(me, "chose the address checkout uses first", `${x.city}, ${x.pin}`);
        return json({ ok: true });
      }
      case "set-password": {
        const pw = typeof b.password === "string" ? b.password : "";
        const weak = weakPassword(pw, me);
        if (weak) return json({ error: weak, field: "password" }, 400);
        const had = !!(await passwordSetAt(me));
        if (had && !(await proven(b.current))) return json({ error: "your current password, or sign in again with a code to set a new one", field: "current" }, 400);
        await setPassword(me, pw);
        // a new password ends every other session: if someone else knew the old one, they're out
        if (had) {
          for (const d of await devices(me)) if (!d.current) await endDevice(me, d.id);
        }
        await did(me, had ? "changed your password" : "set a password");
        return json({ ok: true });
      }
      case "remove-password": {
        if (!(await passwordSetAt(me))) return json({ ok: true });
        if (!(await proven(b.current))) return json({ error: "your current password, to remove it", field: "current" }, 400);
        await removePassword(me);
        await did(me, "removed your password", "sign in with an email code or google");
        return json({ ok: true });
      }
      case "google": {
        const on = b.on === true;
        await saveAccount({ ...a, googleOff: !on });
        await did(me, on ? "turned google sign-in on" : "turned google sign-in off");
        return json({ ok: true, ready: !!googleKeys() });
      }
      case "end-device": {
        const id = typeof b.id === "string" ? b.id : "";
        const list = await devices(me);
        const d = list.find((x) => x.id === id);
        if (!d) return json({ ok: true });
        if (d.current) { await did(me, "signed out", d.device.split(", near")[0]); await signOut(); return json({ ok: true, out: true }); }
        await endDevice(me, id);
        await did(me, "signed a device out", d.device.split(", near")[0]);
        return json({ ok: true });
      }
      case "signout-all":
        await signOutEverywhere(me);
        await signOut();
        return json({ ok: true });
      case "delete":
        // the orders themselves stay (they're still on their way, and the shop has to keep its records); the account goes
        await deleteAccount(me);
        await signOut();
        return json({ ok: true });
      case "orders":
        return json({ ids: await accountOrders(me) });
    }
    return json({ error: "unknown action" }, 400);
  } catch (e) {
    return failed(e);
  }
}
