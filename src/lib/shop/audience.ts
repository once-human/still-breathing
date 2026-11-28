import "server-only";
import { accountsRead, validEmail } from "./account";
import { everyone, turnedOff } from "./drops";
import { ordersRead } from "./orders";

/**
 * Who an admin email goes to: a named group, over a window of days where it has one, plus anyone typed in. Every group
 * is worked out from the tables at send time (never a stale list). People who turned drop emails off are left out of
 * everything except news about an order of theirs that's still on its way, and the email to a group carries a one-tap
 * way off, as bulk mail must.
 */
export const GROUPS = {
  typed: { label: "only the people i type", hint: "up to 50, each on their own copy", days: false, service: true },
  everyone: { label: "everyone", hint: "every profile and everyone who has bought", days: false, service: false },
  bought: { label: "bought", hint: "paid for an order", days: true, service: false },
  active: { label: "around lately", hint: "signed in, visited signed in, or ordered", days: true, service: false },
  onTheWay: { label: "order on its way", hint: "paid, not with them yet: for news about their order", days: false, service: true },
  lapsed: { label: "bought before, not since", hint: "paid once, nothing in the window", days: true, service: false },
  profileOnly: { label: "profile, never bought", hint: "made a profile, no paid order", days: false, service: false },
  leftCheckout: { label: "left at checkout", hint: "started paying, never finished", days: true, service: false },
  drops: { label: "the drop list", hint: "asked for new-drop emails", days: false, service: false },
} as const;
export type Group = keyof typeof GROUPS;
export const DAYS = [7, 30, 90, 365] as const;

const PAID = "paid_at IS NOT NULL";
const ON_WAY = "stage IN ('paid', 'printing', 'shipped', 'out', 'attention')";
const col = async (q: Promise<(string | null)[][]>) => (await q.catch(() => [] as (string | null)[][])).map((r) => (r[0] ?? "").toLowerCase()).filter(Boolean);

async function members(g: Group, days: number): Promise<string[]> {
  const d = String(days);
  switch (g) {
    case "typed": return [];
    case "everyone": return [...new Set([...(await col(accountsRead("SELECT email FROM users"))), ...(await col(ordersRead(`SELECT DISTINCT email FROM orders WHERE ${PAID}`)))])];
    case "bought": return col(ordersRead(`SELECT DISTINCT email FROM orders WHERE ${PAID} AND paid_at > now() - ($1 || ' days')::interval`, [d]));
    case "onTheWay": return col(ordersRead(`SELECT DISTINCT email FROM orders WHERE ${ON_WAY}`));
    case "lapsed": return col(ordersRead(`SELECT email FROM orders WHERE ${PAID} GROUP BY email HAVING max(paid_at) <= now() - ($1 || ' days')::interval`, [d]));
    case "leftCheckout": return col(ordersRead(`SELECT DISTINCT email FROM orders o WHERE stage = 'paying' AND created_at > now() - ($1 || ' days')::interval
      AND NOT EXISTS (SELECT 1 FROM orders p WHERE p.email = o.email AND p.${PAID})`, [d]));
    case "profileOnly": {
      const buyers = new Set(await col(ordersRead(`SELECT DISTINCT email FROM orders WHERE ${PAID}`)));
      return (await col(accountsRead("SELECT email FROM users"))).filter((e) => !buyers.has(e));
    }
    case "active": {
      const w = "> now() - ($1 || ' days')::interval";
      const [a, b, c, o] = await Promise.all([
        col(accountsRead(`SELECT DISTINCT email FROM user_sessions WHERE seen_at ${w}`, [d])),
        col(accountsRead(`SELECT DISTINCT email FROM visitor_people WHERE at ${w}`, [d])),
        col(accountsRead(`SELECT DISTINCT email FROM user_events WHERE at ${w}`, [d])),
        col(ordersRead(`SELECT DISTINCT email FROM orders WHERE ${PAID} AND created_at ${w}`, [d])),
      ]);
      return [...new Set([...a, ...b, ...c, ...o])];
    }
    case "drops": return (await everyone()).map((e) => e.toLowerCase());
  }
}

export const parseTyped = (raw: string) => [...new Set(raw.toLowerCase().split(/[\s,;]+/).filter(Boolean))];

/** the final list for a group, the typed extras, and who was left out for having turned emails off */
export async function audience(group: Group, days: number, typedRaw: string) {
  const typed = parseTyped(typedRaw);
  const bad = typed.filter((e) => !validEmail(e));
  const d = (DAYS as readonly number[]).includes(days) ? days : 30;
  const fromGroup = await members(group, d);
  const off = GROUPS[group].service ? new Set<string>() : await turnedOff().catch(() => new Set<string>());
  const kept = fromGroup.filter((e) => validEmail(e) && !off.has(e));
  const list = [...new Set([...kept, ...typed.filter((e) => !bad.includes(e))])];
  return { list, bad, typed: typed.length, leftOut: fromGroup.length - kept.length, days: d, bulk: !GROUPS[group].service };
}
