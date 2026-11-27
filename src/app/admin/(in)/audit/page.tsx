import Link from "next/link";
import { requireAdmin } from "@/lib/admin/auth";
import { auditPage, type AuditRow } from "@/lib/admin/log";
import { BTN, FIELD } from "../../ui/client";
import { Icon, type IconName } from "../../ui/icons";
import { Empty, Mark, Page, dt } from "../../ui/ui";

export const metadata = { title: "audit log" };
export const dynamic = "force-dynamic";

/** each action in plain words, with its mark */
const SAY: Record<string, [string, IconName]> = {
  login: ["signed in", "key"], "login.link": ["asked for a sign-in link", "mail"], "login.refused": ["a sign-in link was refused", "shield"],
  logout: ["signed out", "signout"], "logout.all": ["signed out everywhere", "signout"],
  "order.note": ["noted on an order", "note"], "order.sync": ["asked qikink about an order", "refresh"], "order.fees": ["fetched an order's fee", "card"],
  "order.send-to-print": ["sent an order to print", "print"], "order.cancel": ["cancelled an order", "x"], "order.refund": ["refunded an order", "return"],
  "order.resend": ["resent an order email", "mail"], "order.address": ["changed an order's address", "pin"], "order.delete": ["deleted a test order", "trash"],
  "orders.export": ["downloaded the orders", "download"],
  "customer.edit": ["edited a person", "edit"], "customer.signout": ["signed a person out everywhere", "signout"], "customer.delete": ["deleted a person", "trash"], "customer.note": ["noted on a person", "note"],
  "product.save": ["changed a shirt", "shirt"], "settings.save": ["changed settings", "settings"], "visitor.forget": ["forgot a visitor", "trash"],
};
const say = (a: string): [string, IconName, boolean] => {
  const failed = a.endsWith(".failed");
  const [w, i] = SAY[failed ? a.slice(0, -7) : a] ?? [a.replace(/[._-]/g, " "), "dot" as IconName];
  return [failed ? `tried: ${w}, it failed` : w, failed ? "alert" : i, failed || a === "login.refused"];
};

const target = (t: string | null) =>
  !t ? null : /^S\d{6}[A-Z0-9]{4}$/.test(t) ? [`/admin/orders/${t}`, t]
  : t.startsWith("customer:") ? [`/admin/people/${encodeURIComponent(t.slice(9))}`, t.slice(9)]
  : t.startsWith("product:") ? [`/admin/products/${t.slice(8)}`, t.slice(8)]
  : [null, t];

/** what changed, in a line: "margin 300 → 320", "₹500", "why: bad or used link" */
function detailLine(d: AuditRow["detail"]) {
  if (!d) return null;
  return Object.entries(d).slice(0, 6).map(([k, v]) => {
    if (v && typeof v === "object" && "from" in v && "to" in v) return `${k} ${JSON.stringify((v as { from: unknown }).from)} → ${JSON.stringify((v as { to: unknown }).to)}`;
    return `${k}: ${typeof v === "string" ? v : JSON.stringify(v)}`;
  }).join(" · ");
}

/** every admin action and sign-in, newest first; nothing in it can be edited or removed from the admin */
export default async function Audit({ searchParams }: { searchParams: Promise<{ q?: string; before?: string }> }) {
  await requireAdmin();
  const sp = await searchParams;
  const q = typeof sp.q === "string" ? sp.q.slice(0, 100) : "";
  const before = Number(sp.before) || undefined;
  const list = await auditPage({ q, before, limit: 100 });
  return (
    <>
      <Page title="audit log" sub="every sign-in and every change made here, with who and when. nothing in it can be changed or removed" />
      <form method="get" className="relative mb-8">
        <Icon name="search" className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-quiet" />
        <input name="q" defaultValue={q} placeholder="search an action, an order, an email" className={`${FIELD} !pl-12`} />
      </form>
      {list.length ? (
        <div className="divide-y divide-line/50 overflow-hidden rounded-[14px] bg-s1">
          {list.map((r) => {
            const [words, icon, bad] = say(r.action);
            const t = target(r.target);
            const d = detailLine(r.detail);
            return (
              <div key={r.id} className="flex items-start gap-4 px-5 py-3.5">
                <Mark icon={icon} tone={bad ? "warn" : "quiet"} />
                <div className="min-w-0 flex-1">
                  <div className="text-[15px] leading-snug">
                    {words}{t ? <> {t[0] ? <Link href={t[0]} className="underline decoration-ink/25 underline-offset-4 hover:decoration-ink">{t[1]}</Link> : <span>{t[1]}</span>}</> : null}
                  </div>
                  <div className="mt-0.5 text-[13px] leading-snug text-quiet">{dt(r.at)} · {r.who}{r.ip ? ` · ${r.ip}` : ""}</div>
                  {d ? <div className="mt-1 break-words font-mono text-[12px] leading-snug text-quiet">{d}</div> : null}
                </div>
              </div>
            );
          })}
        </div>
      ) : <Empty icon="list" title={q ? "nothing matches" : "nothing logged yet"} />}
      {list.length === 100 ? (
        <div className="mt-6 flex justify-end">
          <Link href={`?${new URLSearchParams({ ...(q ? { q } : {}), before: String(list[list.length - 1].id) })}`} className={BTN.plain}>older</Link>
        </div>
      ) : null}
    </>
  );
}
