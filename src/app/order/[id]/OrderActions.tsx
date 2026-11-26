"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AddressFields, EMPTY, addressLine, post } from "@/components/shop/AddressFields";
import type { Details } from "@/lib/shop/india";
import { rupees } from "@/lib/shop/money";
import type { ShipTo } from "@/lib/shop/partner";

const IST = { hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" } as const;

/**
 * The change-of-mind hour, on the order's own page: cancel (refunded in full, straight away) or fix the address,
 * with the time it closes counting down. The server checks again: once it has gone to print, neither goes through.
 */
export function OrderActions({ id, k, until, total, ship }: { id: string; k: string | null; until: string; total: number; ship: Omit<ShipTo, "email"> }) {
  const router = useRouter();
  const [left, setLeft] = useState<number | null>(null);
  const [mode, setMode] = useState<"idle" | "cancel" | "address">("idle");
  const [d, setD] = useState<Details>({ ...EMPTY, ...ship });
  const [bad, setBad] = useState<{ field?: string; error: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const tick = () => setLeft(Math.max(0, Date.parse(until) - Date.now()));
    tick();
    const t = setInterval(tick, 15_000);
    return () => clearInterval(t);
  }, [until]);

  async function act(body: object) {
    setBusy(true);
    setBad(null);
    try {
      await post("/api/shop/order", { id, k, ...body });
      setMode("idle");
      router.refresh();
    } catch (e) {
      setBad({ field: (e as { field?: string }).field, error: (e as Error).message });
    } finally {
      setBusy(false);
    }
  }

  const mins = left === null ? null : Math.ceil(left / 60_000);
  return (
    <section className="border-t border-line pt-1.5 text-[14px]" aria-labelledby="change">
      <h2 id="change" className="text-quiet">
        changed your mind? until {new Date(until).toLocaleTimeString("en-IN", IST).toLowerCase()}
        {mins !== null && mins > 0 ? ` (${mins} min left)` : mins === 0 ? " (it goes to print at the next check)" : ""}
      </h2>
      <p className="mt-2">{ship.name} · {addressLine(ship)} · {ship.phone}</p>

      {mode === "idle" && (
        <div className="mt-3 flex gap-5">
          <button type="button" onClick={() => setMode("address")} className="hit font-semibold">fix the address</button>
          <button type="button" onClick={() => setMode("cancel")} className="hit text-quiet hover:text-ink">cancel the order</button>
        </div>
      )}

      {mode === "cancel" && (
        <div className="mt-3">
          <p>cancel it? nothing will be made, and {rupees(total)} goes back the way you paid.</p>
          <div className="mt-3 flex gap-5">
            <button type="button" disabled={busy} onClick={() => act({ action: "cancel" })} className="hit font-semibold">{busy ? "cancelling.." : `yes, cancel and refund ${rupees(total)}`}</button>
            <button type="button" onClick={() => setMode("idle")} className="hit text-quiet hover:text-ink">keep it</button>
          </div>
        </div>
      )}

      {mode === "address" && (
        <form onSubmit={(e) => { e.preventDefault(); act({ action: "address", details: d }); }} className="mt-4" noValidate>
          <AddressFields d={d} onChange={setD} bad={bad?.field as keyof Details | undefined} email={false} />
          <div className="mt-4 flex gap-5">
            <button disabled={busy} className="hit font-semibold">{busy ? "saving.." : "save the address"}</button>
            <button type="button" onClick={() => { setMode("idle"); setD({ ...EMPTY, ...ship }); setBad(null); }} className="hit text-quiet hover:text-ink">leave it</button>
          </div>
        </form>
      )}
      {bad && <p role="alert" className="mt-3">{bad.error}</p>}
    </section>
  );
}
