import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { shopOpen } from "@/lib/shop/config";
import { Checkout } from "./Checkout";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "checkout", robots: { index: false, follow: false } };

/** Where the bag is paid for. There's no checkout at all while the shop can't take orders. */
export default function CheckoutPage() {
  if (!shopOpen()) notFound();
  return (
    <div className="px-4 pt-6 pb-24">
      <h1 className="page-in bigword text-[20vw] md:text-[12vw]">checkout</h1>
      <div className="page-in-2 mt-10"><Checkout /></div>
    </div>
  );
}
