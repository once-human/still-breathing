import "server-only";
import { rzpGet } from "@/lib/shop/razorpay";

/**
 * Which settlement paid a payment out to the bank. Razorpay's reconciliation report is by day, so this looks at the
 * days from the capture onwards (settlement is usually T+2 working days) until the payment shows up in one.
 */
type Recon = { items?: { entity_id?: string; type?: string; settlement_id?: string | null; settled_at?: number | null; settled?: boolean }[] };

export async function settlementOf(paymentId: string, capturedAt?: number | null): Promise<{ id: string; at: string | null } | null> {
  const start = (capturedAt ? capturedAt * 1000 : Date.now() - 7 * 86400_000) + 5.5 * 3600_000;
  for (let i = 0; i <= 7; i++) {
    const t = start + i * 86400_000;
    if (t > Date.now() + 5.5 * 3600_000) break;
    const d = new Date(t);
    const r = await rzpGet<Recon>(`/settlements/recon/combined?year=${d.getUTCFullYear()}&month=${d.getUTCMonth() + 1}&day=${d.getUTCDate()}&count=1000`);
    const hit = r.items?.find((x) => x.entity_id === paymentId && x.type === "payment");
    if (hit?.settlement_id) return { id: hit.settlement_id, at: hit.settled_at ? new Date(hit.settled_at * 1000).toISOString() : null };
  }
  return null;
}
