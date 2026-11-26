import { OPERATOR, POLICIES_UPDATED } from "@/content/policies";
import { SHOP } from "@/content/shop";
import { adminEmail, requireAdmin } from "@/lib/admin/auth";
import { getSettings, DEFAULTS } from "@/lib/admin/settings";
import { SettingsForm } from "./SettingsForm";
import { SignOutAll } from "../../ui/client";
import { KV, PageHead, Pill, Section } from "../../ui/ui";

export const metadata = { title: "settings" };

/** every key the site reads, by what it's for; only whether each is set is shown, never a value */
const KEYS: [string, string[]][] = [
  ["admin", ["ADMIN_EMAIL"]],
  ["database (neon)", ["DATABASE_URL", "POSTGRES_URL"]],
  ["payments (razorpay)", ["RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET"]],
  ["printing (qikink)", ["QIKINK_CLIENT_ID", "QIKINK_CLIENT_SECRET", "QIKINK_SANDBOX", "QIKINK_SANDBOX_SKU"]],
  ["email (resend)", ["RESEND_API_KEY", "SHOP_EMAIL_FROM", "SHOP_OWNER_EMAIL"]],
  ["shop", ["SHOP_SECRET", "SHOP_SITE_URL", "CRON_SECRET", "SITE_URL"]],
];

export default async function SettingsPage() {
  await requireAdmin();
  const s = await getSettings(true);
  const set = (k: string) => !!process.env[k]?.trim();
  const mode = (k: string) => (k === "RAZORPAY_KEY_ID" && set(k) ? (process.env[k]!.trim().startsWith("rzp_live_") ? "live" : "test") : null);
  return (
    <>
      <PageHead title="settings" />
      <Section title="shop" aside="saved to the database, in the audit log">
        <SettingsForm initial={s} defaults={DEFAULTS} />
      </Section>

      <div className="grid gap-x-12 lg:grid-cols-2">
        <Section title="policy details" aside={`policies last changed ${POLICIES_UPDATED}`}>
          <KV items={[
            ["seller name", OPERATOR.legalName ?? "not shown (sahn only)"],
            ["contact email", OPERATOR.email ?? "–"],
            ["phone", OPERATOR.phone ?? "not shown"],
            ["place", OPERATOR.place ?? "not shown"],
            ["ships to", SHOP.where],
            ["make / road", `${SHOP.make[0]}–${SHOP.make[1]} days, then ${SHOP.road[0]}–${SHOP.road[1]} days`],
            ["per order", `at most ${SHOP.maxPerLine} of one size, ${SHOP.maxPerBag} in all`],
          ]} />
          <p className="mt-3 text-[12px] text-quiet">these are in the code (src/content/policies.ts and shop.ts), because the policy pages are built ahead from them.</p>
        </Section>

        <Section title="emails">
          <KV items={[
            ["admin sign-in goes to", adminEmail() ?? "–"],
            ["orders are sent from", process.env.SHOP_EMAIL_FROM?.trim() || "not set"],
            ["“needs you” alerts go to", process.env.SHOP_OWNER_EMAIL?.trim() || "not set"],
            ["buyers reply to", OPERATOR.email ?? "–"],
          ]} />
        </Section>
      </div>

      <Section title="keys in this deployment" aside="set or not: the values are never shown">
        <div className="grid gap-x-12 gap-y-4 md:grid-cols-2 xl:grid-cols-3">
          {KEYS.map(([group, keys]) => (
            <div key={group}>
              <div className="mb-1 text-[13px] font-medium">{group}</div>
              <ul className="grid gap-1 text-[12px]">
                {keys.map((k) => (
                  <li key={k} className="flex items-center justify-between gap-3 border-b border-line/60 py-1">
                    <span className="font-mono">{k}</span>
                    {set(k) ? <Pill tone="ok">set{mode(k) ? ` · ${mode(k)}` : ""}</Pill> : <Pill>not set</Pill>}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>

      <Section title="sessions">
        <SignOutAll />
      </Section>
    </>
  );
}
