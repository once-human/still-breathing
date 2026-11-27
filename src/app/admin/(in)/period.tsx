import { cookies } from "next/headers";
import { periodOf, type Period } from "@/lib/admin/data";
import { Tabs } from "../ui/ui";
import { Remember } from "./Remember";

/** the stretches of time every count in the admin can be read over; the one picked last is kept for next time */
export const PERIODS = [["month", "this month"], ["last", "last month"], ["quarter", "3 months"], ["all", "all time"]] as const;

export async function pickPeriod(asked?: string): Promise<Period> {
  const want = asked ?? (await cookies()).get("admin-period")?.value;
  return periodOf(PERIODS.some(([k]) => k === want) ? want : "month");
}

/** the period chips, keeping the page's other search params */
export function PeriodTabs({ p, keep = {} }: { p: Period; keep?: Record<string, string | undefined> }) {
  const href = (k: string) => "?" + new URLSearchParams(Object.entries({ ...keep, p: k }).filter(([, v]) => v) as [string, string][]).toString();
  return (
    <>
      <Remember name="admin-period" value={p.key} />
      <Tabs active={p.key} items={PERIODS.map(([k, l]) => ({ key: k, label: l, href: href(k) }))} />
    </>
  );
}
