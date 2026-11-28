import "server-only";
import { IDLE_DAYS, adminEmail, adminReady } from "@/lib/admin/auth";
import { rows } from "@/lib/admin/db";
import { lastSync } from "@/lib/admin/sync";
import { kvKeys, mailKeys, ownerEmail, partnerKeys, razorpayKeys, shopSecret, googleKeys } from "@/lib/shop/config";
import { kv } from "@/lib/shop/kv";
import { partnerCheck } from "@/lib/shop/partner";
import { rzpGet } from "@/lib/shop/razorpay";
import { getSettings } from "@/lib/shop/settings";

/**
 * Every service an order passes through, asked just now. Only something that stops or slows an order is amber or
 * red; things that simply haven't happened yet (no payment since the webhook was first watched, say) stay grey.
 */
export type Health = "ok" | "warn" | "bad" | "quiet";
export type Check = { key: string; name: string; tone: Health; state: string; detail: string; fix?: string; href?: string };

const timed = <T,>(p: Promise<T>, ms = 6000) => Promise.race([p, new Promise<never>((_, no) => setTimeout(() => no(new Error("no answer in 6 seconds")), ms))]);
let cache: { at: number; v: Check[] } | null = null;

/**
 * `fresh` asks Razorpay and Qikink again; `quick` never waits on them (the overview's way: the last answer from the
 * past 10 minutes if there is one, else only what the keys and the database say).
 */
export async function health(fresh = false, quick = false): Promise<Check[]> {
  if (!fresh && cache && Date.now() - cache.at < (quick ? 600_000 : 120_000)) return cache.v;
  const rz = razorpayKeys(), pk = partnerKeys(), store = kvKeys(), mail = mailKeys();
  const [db, razor, qikink, sync, hook, s] = await Promise.all([
    timed(rows("SELECT 1")).then(() => null, (e: Error) => e.message),
    !rz ? Promise.resolve("not set up") : quick ? Promise.resolve(null) : timed(rzpGet("/orders?count=1")).then(() => null, (e: Error) => e.message),
    !pk ? Promise.resolve({ mode: null, ok: false, why: "not set up" })
      : quick ? Promise.resolve({ mode: pk.sandbox ? "sandbox" : "live", ok: true, why: undefined as string | undefined })
      : timed(partnerCheck()).catch((e: Error) => ({ mode: null, ok: false, why: e.message })),
    lastSync(),
    kv<string | null>("GET", "hook:razorpay:last").then((v) => (v ? (JSON.parse(v) as { at: string; event: string }) : null)).catch(() => null),
    getSettings({ fresh: !quick }),
  ]);
  const hours = sync ? (Date.now() - Date.parse(sync)) / 3600_000 : null;
  const ago = (iso: string) => {
    const m = Math.round((Date.now() - Date.parse(iso)) / 60000);
    return m < 1 ? "just now" : m < 60 ? `${m} min ago` : m < 48 * 60 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} days ago`;
  };

  const v: Check[] = [
    {
      key: "open", name: "taking orders", tone: s.open ? "ok" : "warn", state: s.open ? "on" : "closed",
      detail: s.open ? "checkout is open on every shirt" : "people can look, but checkout shows the closed message", fix: s.open ? undefined : "open it with the switch at the top right",
    },
    {
      key: "pay", name: "payments", tone: !rz || razor ? "bad" : rz.test ? "warn" : "ok", state: !rz ? "not set up" : razor ? "not answering" : rz.test ? "test mode" : "live",
      detail: razor && rz ? `razorpay: ${razor}` : rz?.test ? "razorpay test keys: nobody is really charged" : rz ? "razorpay answered just now, real money" : "no razorpay keys in this deployment",
      fix: !rz ? "add the razorpay keys in vercel" : razor ? "check razorpay's status page; payments wait until it answers" : rz.test ? "swap in the live keys in vercel" : undefined,
    },
    {
      key: "hook", name: "payment backup", tone: !rz ? "bad" : hook ? "ok" : "quiet", state: hook ? `last ${ago(hook.at)}` : "waiting for the next payment",
      detail: "razorpay's webhook: it catches a payment when the buyer closes the tab too soon. it shows here after the next paid order.",
    },
    {
      key: "print", name: "printing", tone: !pk || !qikink.ok ? "bad" : qikink.mode === "sandbox" ? "warn" : "ok",
      state: !pk ? "not set up" : !qikink.ok ? "refused the keys" : qikink.mode === "sandbox" ? "sandbox" : "live",
      detail: !qikink.ok ? `qikink: ${qikink.why ?? "no answer"}` : qikink.mode === "sandbox" ? "orders go to qikink's sandbox: nothing gets printed" : "qikink signed in just now: paid orders go to print",
      fix: !pk || !qikink.ok ? "check the qikink keys in vercel" : qikink.mode === "sandbox" ? "remove QIKINK_SANDBOX in vercel" : undefined,
    },
    {
      key: "sync", name: "order updates", tone: hours == null ? "quiet" : hours < 8 ? "ok" : hours < 24 ? "warn" : "bad",
      state: sync ? `last ${ago(sync)}` : "first run soon",
      detail: "moves orders on: late payments, print hand-offs, tracking, refunds. every 3 hours, and whenever you open the admin after a gap.",
      fix: hours != null && hours >= 8 ? "open the shop-sync workflow on github and run it" : undefined,
    },
    {
      key: "db", name: "order store", tone: !store || db ? "bad" : "ok", state: !store ? "not set up" : db ? "not answering" : "working",
      detail: db ? `neon: ${db}` : "neon, where every order and account is kept", fix: !store || db ? "check neon's dashboard and DATABASE_URL in vercel" : undefined,
    },
    {
      key: "mail", name: "emails", tone: mail ? "ok" : "bad", state: mail ? "working" : "not set up",
      detail: mail ? `sent through resend as ${mail.from}` : "no order emails and no sign-in codes go out", fix: mail ? undefined : "add RESEND_API_KEY and SHOP_EMAIL_FROM in vercel",
    },
    {
      key: "alerts", name: "alerts to you", tone: ownerEmail() ? "ok" : "warn", state: ownerEmail() ? "on" : "off",
      detail: ownerEmail() ? `new orders and problems are emailed to ${ownerEmail()}` : "you won't be emailed about new orders or a refused print", fix: ownerEmail() ? undefined : "add SHOP_OWNER_EMAIL in vercel",
    },
    { key: "secret", name: "link secret", tone: shopSecret() ? "ok" : "bad", state: shopSecret() ? "set" : "missing", detail: "signs order links and the sync job", fix: shopSecret() ? undefined : "add SHOP_SECRET (32+ characters) in vercel" },
    { key: "google", name: "google sign-in", tone: googleKeys() ? "ok" : "warn", state: googleKeys() ? "on" : "off", detail: googleKeys() ? "buyers can continue with google" : "buyers sign in by email code or password only", fix: googleKeys() ? undefined : "add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in vercel" },
    { key: "admin", name: "admin sign-in", tone: adminReady() ? "ok" : "bad", state: adminReady() ? "set" : "missing", detail: adminReady() ? `by the site key; ${IDLE_DAYS} days away signs a browser out${adminEmail() ? `, and each sign-in is emailed to ${adminEmail()}` : ""}` : "nobody can sign in", fix: adminReady() ? undefined : "add ADMIN_SECRET (16+ characters) in vercel" },
  ];
  if (!quick) cache = { at: Date.now(), v };
  return v;
}

/** what's amber or red, worst first */
export const problems = (v: Check[]) => v.filter((c) => c.tone === "bad").concat(v.filter((c) => c.tone === "warn"));
