import { OPERATOR, POLICIES_UPDATED } from "@/content/policies";
import { SHOP } from "@/content/shop";
import { adminEmail, requireAdmin } from "@/lib/admin/auth";
import { getSettings } from "@/lib/admin/settings";
import { SignOutAll } from "../../ui/client";
import { Field, Fixed, Group, Page, Row, Section } from "../../ui/ui";

export const metadata = { title: "settings" };
export const dynamic = "force-dynamic";

/** every key the site reads, by what it's for; only whether each is set is shown, never a value */
const KEYS: [string, string[]][] = [
  ["admin", ["ADMIN_EMAIL"]],
  ["database (neon)", ["DATABASE_URL", "POSTGRES_URL"]],
  ["payments (razorpay)", ["RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET"]],
  ["printing (qikink)", ["QIKINK_CLIENT_ID", "QIKINK_CLIENT_SECRET", "QIKINK_SANDBOX", "QIKINK_SANDBOX_SKU"]],
  ["email (resend)", ["RESEND_API_KEY", "SHOP_EMAIL_FROM", "SHOP_OWNER_EMAIL"]],
  ["shop", ["SHOP_SECRET", "SHOP_SITE_URL", "CRON_SECRET", "SITE_URL"]],
];

/**
 * settings: the shop's one switch and where the rest of what's yours lives (prices, site words), then what's fixed
 * elsewhere, shown grey: who emails go to, the policy facts from the code, which keys this deployment has, and sessions.
 */
export default async function SettingsPage() {
  await requireAdmin();
  const s = await getSettings(true);
  const set = (k: string) => !!process.env[k]?.trim();
  const mode = (k: string) => (k === "RAZORPAY_KEY_ID" && set(k) ? (process.env[k]!.trim().startsWith("rzp_live_") ? "live" : "test") : k === "QIKINK_SANDBOX" && set(k) ? "sandbox on" : null);
  return (
    <>
      <Page title="settings" sub="what's yours to change is open; what's set by the partners, vercel or the code is grey. every change goes in the audit log" />

      <Section title="the shop">
        <Group>
          <Row icon="shop" tone={s.open ? "ok" : "warn"} title={s.open ? "taking orders" : "not taking orders"} sub="switch it with shop live at the top right; closed, checkout shows your closed message" />
          <Row icon="card" title="prices" sub={`margin ₹${s.margin} a shirt, and each shirt's own price`} href="/admin/prices" />
          <Row icon="note" title="site words" sub="the top line and the closed message" href="/admin/words" />
          <Row icon="shield" title="health" sub="every service an order passes through, asked now" href="/admin/status" />
        </Group>
      </Section>

      <div className="grid gap-x-6 lg:grid-cols-2">
        <Section title="emails" aside="set in vercel">
          <Group>
            <Field label="admin sign-in goes to"><Fixed>{adminEmail() ?? "–"}</Fixed></Field>
            <Field label="orders are sent from"><Fixed>{process.env.SHOP_EMAIL_FROM?.trim() || "not set"}</Fixed></Field>
            <Field label="new orders and alerts go to"><Fixed>{process.env.SHOP_OWNER_EMAIL?.trim() || "not set"}</Fixed></Field>
            <Field label="buyers reply to"><Fixed>{OPERATOR.email ?? "–"}</Fixed></Field>
          </Group>
        </Section>

        <Section title="policy details" aside={`in the code, last changed ${POLICIES_UPDATED}`}>
          <Group>
            <Field label="seller name"><Fixed>{OPERATOR.legalName ?? "not shown (sahn only)"}</Fixed></Field>
            <Field label="contact email"><Fixed>{OPERATOR.email ?? "–"}</Fixed></Field>
            <Field label="phone"><Fixed>{OPERATOR.phone ?? "not shown"}</Fixed></Field>
            <Field label="place"><Fixed>{OPERATOR.place ?? "not shown"}</Fixed></Field>
            <Field label="ships to"><Fixed>{SHOP.where}</Fixed></Field>
            <Field label="making, then the road"><Fixed>{SHOP.make[0]}–{SHOP.make[1]} days, then {SHOP.road[0]}–{SHOP.road[1]}</Fixed></Field>
            <Field label="most in one order"><Fixed>{SHOP.maxPerLine} of a size, {SHOP.maxPerBag} in all</Fixed></Field>
          </Group>
          <p className="mt-3 px-1 text-[13px] text-quiet">src/content/policies.ts and shop.ts: the policy pages are built ahead from them.</p>
        </Section>
      </div>

      <Section title="keys in this deployment" aside="set or not: the values are never shown">
        <div className="grid gap-x-6 gap-y-3 lg:grid-cols-2">
          {KEYS.map(([group, keys]) => (
            <div key={group}>
              <div className="mb-2 px-1 text-[13px] text-quiet">{group}</div>
              <Group>
                {keys.map((k) => (
                  <Field key={k} label={<span className="font-mono text-[13px]">{k}</span>}>
                    <span className={`inline-flex items-center gap-2 text-[13px] ${set(k) ? "text-ink/85" : "text-quiet"}`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${set(k) ? "bg-ok" : "bg-quiet/50"}`} />{set(k) ? `set${mode(k) ? `, ${mode(k)}` : ""}` : "not set"}
                    </span>
                  </Field>
                ))}
              </Group>
            </div>
          ))}
        </div>
      </Section>

      <Section title="your sessions">
        <Group><SignOutAll /></Group>
      </Section>
    </>
  );
}
