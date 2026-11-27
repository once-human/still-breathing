import { DESIGNS, SIZE_ORDER, type Design } from "@/content/tee";
import { adminEmail, requireAdmin } from "@/lib/admin/auth";
import { rows } from "@/lib/admin/db";
import { shirtName } from "@/lib/admin/data";
import { payView } from "@/lib/shop/catalog";
import { kvKeys, mailKeys, ownerEmail, partnerKeys, razorpayKeys, shopSecret } from "@/lib/shop/config";
import { kv } from "@/lib/shop/kv";
import { partnerCheck } from "@/lib/shop/partner";
import { products } from "@/lib/shop/products";
import { rzpGet } from "@/lib/shop/razorpay";
import { getSettings } from "@/lib/shop/settings";
import { PageHead, Section, ago } from "../../ui/ui";

export const metadata = { title: "what's live" };
export const dynamic = "force-dynamic";

type Tone = "ok" | "warn" | "bad";
type Check = { name: string; tone: Tone; state: string; detail?: string };

const TONE: Record<Tone, string> = { ok: "bg-[#8fd19e]", warn: "bg-[#f0a35b]", bad: "bg-[#f08a7a]" };
const timed = <T,>(p: Promise<T>, ms = 6000) => Promise.race([p, new Promise<never>((_, no) => setTimeout(() => no(new Error("no answer in 6 s")), ms))]);

/** every service an order passes through, asked just now, plus what's on sale in each size */
export default async function Status() {
  await requireAdmin();
  const rz = razorpayKeys(), pk = partnerKeys();
  const [db, razor, qikink, cron, hook, settings, pay, list] = await Promise.all([
    timed(rows<{ ok: number }>("SELECT 1 AS ok")).then(() => null, (e: Error) => e.message),
    rz ? timed(rzpGet("/orders?count=1")).then(() => null, (e: Error) => e.message) : Promise.resolve("keys not set"),
    timed(partnerCheck()).catch((e: Error) => ({ mode: null, ok: false, why: e.message })),
    kv<string | null>("GET", "cron:last").catch(() => null),
    kv<string | null>("GET", "hook:razorpay:last").then((v) => (v ? (JSON.parse(v) as { at: string; event: string }) : null)).catch(() => null),
    getSettings({ fresh: true }),
    payView().catch(() => null),
    products().catch(() => []),
  ]);
  const cronAge = cron ? (Date.now() - Date.parse(cron)) / 3600_000 : null;

  const checks: Check[] = [
    { name: "taking orders", tone: settings.open ? "ok" : "warn", state: settings.open ? "on" : "switched off", detail: settings.open ? "checkout is open" : "checkout shows the closed message: switch it on from home or settings" },
    { name: "payments (razorpay)", tone: !rz ? "bad" : razor ? "bad" : rz.test ? "warn" : "ok", state: !rz ? "not set up" : razor ? "not answering" : rz.test ? "test mode" : "live", detail: razor ?? (rz?.test ? "test keys: nobody is charged" : "real money, answered just now") },
    { name: "razorpay webhook", tone: !rz ? "bad" : hook ? "ok" : "warn", state: hook ? `last ${ago(hook.at)}` : "nothing yet", detail: hook ? `signed ${hook.event}` : "fills in after the first paid order; it catches payments whose buyer closed the tab" },
    { name: "printing (qikink)", tone: !pk ? "bad" : !qikink.ok ? "bad" : qikink.mode === "sandbox" ? "warn" : "ok", state: !pk ? "not set up" : qikink.ok ? (qikink.mode ?? "") : "refused the keys", detail: qikink.ok ? (qikink.mode === "sandbox" ? "orders go to qikink's sandbox: nothing gets printed" : "signed in just now: paid orders go to print") : qikink.why },
    { name: "order store (neon)", tone: !kvKeys() ? "bad" : db ? "bad" : "ok", state: !kvKeys() ? "not set up" : db ? "not answering" : "answering", detail: db ?? kvKeys()?.host.replace(/^([^.]+)\..*$/, "$1…") },
    { name: "email (resend)", tone: mailKeys() ? "ok" : "bad", state: mailKeys() ? "set up" : "not set up", detail: mailKeys() ? `sends as ${mailKeys()!.from}` : "no order emails, no sign-in codes" },
    { name: "order sync", tone: cronAge == null ? "warn" : cronAge < 4 ? "ok" : "bad", state: cron ? `last ${ago(cron)}` : "not seen yet", detail: cronAge != null && cronAge >= 4 ? "it runs every 3 hours from GitHub Actions; it's late: check the shop-sync workflow" : "every 3 hours: print status, tracking, refunds, old visits folded" },
    { name: "link secret", tone: shopSecret() ? "ok" : "bad", state: shopSecret() ? "set" : "missing", detail: "signs order links and the sync job" },
    { name: "admin sign-in", tone: adminEmail() ? "ok" : "bad", state: adminEmail() ? "set" : "missing", detail: adminEmail() ? `links go to ${adminEmail()}` : "nobody can sign in" },
    { name: "“needs you” alerts", tone: ownerEmail() ? "ok" : "warn", state: ownerEmail() ? "set" : "not set", detail: ownerEmail() ? `to ${ownerEmail()}` : "you won't hear about a refused print order by email" },
  ];
  const bad = checks.filter((c) => c.tone === "bad").length, warn = checks.filter((c) => c.tone === "warn").length;
  const designs = Object.keys(DESIGNS) as Design[];
  const byId = new Map(list.map((p) => [p.id, p]));

  return (
    <>
      <PageHead title="what's live" sub={<>asked just now · {bad ? <span className="text-[#f08a7a]">{bad} not working</span> : warn ? <span className="text-[#f0a35b]">{warn} to look at</span> : <span className="text-[#8fd19e]">everything is working</span>}</>} />

      <Section title="services">
        <ul className="grid gap-2 md:grid-cols-2">
          {checks.map((c) => (
            <li key={c.name} className="flex items-start gap-3 rounded-xl border border-line p-4">
              <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${TONE[c.tone]}`} />
              <div className="min-w-0">
                <div className="flex flex-wrap items-baseline gap-x-2 text-[14px]"><span className="font-medium">{c.name}</span><span className="text-quiet">{c.state}</span></div>
                {c.detail ? <div className="mt-0.5 break-words text-[12px] text-quiet">{c.detail}</div> : null}
              </div>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="can be bought now" aside={pay?.pay ? "the checkout's own answer, size by size" : "checkout is closed: nothing can be bought"}>
        <div className="-mx-4 overflow-x-auto px-4 md:mx-0 md:px-0">
          <table className="w-full min-w-[560px] text-left text-[13px]">
            <thead><tr className="border-b border-line text-[11px] uppercase tracking-[0.1em] text-quiet"><th className="py-2 pr-4 font-medium">shirt</th><th className="py-2 pr-4 font-medium">status</th>{SIZE_ORDER.map((z) => <th key={z} className="py-2 pr-2 text-center font-medium">{z}</th>)}</tr></thead>
            <tbody>
              {designs.map((d) => {
                const p = byId.get(d);
                const ok = new Set(pay?.payable[d] ?? []);
                return (
                  <tr key={d} className="border-b border-line/60">
                    <td className="py-2.5 pr-4">{shirtName(d)}</td>
                    <td className="py-2.5 pr-4 text-quiet">{p ? { live: "on sale", soldout: "sold out", draft: "hidden" }[p.status] : "–"}</td>
                    {SIZE_ORDER.map((z) => (
                      <td key={z} className="py-2.5 pr-2 text-center" title={ok.has(z) ? "on sale" : p?.skus[z] ? "not on sale" : "no qikink product"}>
                        <span className={`inline-block h-2.5 w-2.5 rounded-full ${ok.has(z) ? "bg-[#8fd19e]" : p?.skus[z] ? "bg-ink/25" : "border border-ink/25"}`} />
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-[12px] text-quiet">green: anyone can buy it now · grey: has a qikink product but isn&apos;t on sale · ring: qikink has no product for that size</p>
      </Section>
    </>
  );
}
