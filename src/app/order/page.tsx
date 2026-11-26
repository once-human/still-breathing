import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { accountsOpen, shopOpen } from "@/lib/shop/config";
import { Find } from "./Find";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "your order",
  description: "Find your sahn order with its number and email: where it is, from being made to your door.",
  robots: { index: false },
};

/** Find an order: the number from the order email and the email it was placed with. */
export default function OrderFind() {
  // no shop, no orders to find
  if (!shopOpen()) notFound();
  return (
    <div className="px-4 pt-6 pb-24">
      <h1 className="page-in bigword text-[20vw] md:text-[13vw]">your order</h1>
      <p className="page-in-2 mt-6 max-w-[44ch] text-[clamp(18px,1.8vw,24px)] leading-[1.25] text-ink/85">
        every email we send about your order has a link straight to it. or put in its number and your email here.
        {accountsOpen() ? <> or <Link href="/account" className="draw">sign in</Link> to see all your orders.</> : null}
      </p>
      <div className="page-in-3 mt-12"><Find /></div>
    </div>
  );
}
