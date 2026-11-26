import type { Metadata } from "next";
import { loadAccount, sessionEmail } from "@/lib/shop/account";
import { Checkout } from "./Checkout";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "checkout", robots: { index: false, follow: false } };

/** Where the bag is paid for: always here; it says so plainly while payment isn't connected. Signed in, it's filled in. */
export default async function CheckoutPage() {
  const email = await sessionEmail().catch(() => null);
  const saved = email ? await loadAccount(email).catch(() => null) : null;
  return (
    <div className="px-4 pt-6 pb-24">
      <h1 className="page-in bigword text-[20vw] md:text-[12vw]">checkout</h1>
      <div className="page-in-2 mt-10"><Checkout saved={saved} /></div>
    </div>
  );
}
