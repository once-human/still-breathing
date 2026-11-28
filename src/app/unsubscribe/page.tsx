import type { Metadata } from "next";
import { Unsubscribe } from "./Unsubscribe";

export const metadata: Metadata = { title: "new drop emails", robots: { index: false, follow: false }, referrer: "no-referrer" };

/** off the new-drop list: one button (so a mail scanner opening the link can't do it for them) */
export default async function Page({ searchParams }: { searchParams: Promise<{ e?: string; t?: string }> }) {
  const { e = "", t = "" } = await searchParams;
  return (
    <div className="px-4 pt-6 pb-24">
      <h1 className="page-in bigword text-[18vw] md:text-[9vw]">emails</h1>
      <div className="page-in-2 mt-10 max-w-[420px]"><Unsubscribe e={e.slice(0, 120)} t={t.slice(0, 40)} /></div>
    </div>
  );
}
