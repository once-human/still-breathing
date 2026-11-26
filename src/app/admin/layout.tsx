import type { Metadata, Viewport } from "next";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: { default: "admin", template: "%s · admin · sahn" }, robots: { index: false, follow: false, nocache: true } };
export const viewport: Viewport = { themeColor: "#0d0d0c" };

/**
 * The admin sits over the whole window, above the site's own header and footer, and scrolls on its own
 * (data-lenis-prevent keeps the site's smooth scroll out of it).
 */
export default function AdminRoot({ children }: { children: React.ReactNode }) {
  return (
    <div data-lenis-prevent className="fixed inset-0 z-[200] overflow-y-auto overscroll-contain bg-paper text-ink">
      {children}
    </div>
  );
}
