import Link from "next/link";
import { requireAdmin } from "@/lib/admin/auth";
import { getSettings } from "@/lib/admin/settings";
import { syncIfLate } from "@/lib/admin/sync";
import { shopOpen } from "@/lib/shop/config";
import { CsrfProvider, Nav, ShopSwitch } from "../ui/client";

/**
 * Signed in only (each page checks the session again itself). The frame: the six places on the left (along the
 * bottom on a phone), the shop's on/off at the top right of every page, the page in the middle.
 */
export default async function InLayout({ children }: { children: React.ReactNode }) {
  const a = await requireAdmin();
  // GitHub skips scheduled runs when it's busy: a late sync runs after this page is sent
  await syncIfLate().catch(() => {});
  const s = await getSettings().catch(() => null);
  return (
    <CsrfProvider token={a.csrf}>
      <Nav email={a.email} />
      <div className="md:pl-64">
        <div className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 bg-paper px-4 md:h-20 md:justify-end md:px-10">
          <Link href="/admin" className="text-[24px] font-extrabold tracking-[-0.05em] md:hidden">sahn</Link>
          <ShopSwitch open={!!s?.open} connected={shopOpen()} />
        </div>
        <main className="mx-auto max-w-6xl px-4 pb-32 pt-2 md:px-10 md:pb-24 md:pt-4">{children}</main>
      </div>
    </CsrfProvider>
  );
}
