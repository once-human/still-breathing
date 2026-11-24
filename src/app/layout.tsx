import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { SmoothScroll } from "@/components/SmoothScroll";

const description = "again..: two shirts for the December shows in India, the crowd and the map. Lineup 01 of Still Breathing.";

export const metadata: Metadata = {
  title: "still breathing",
  description,
  openGraph: { type: "website", siteName: "still breathing", title: "still breathing", description, locale: "en_IN" },
};

/** Bricolage Grotesque: optical sizes, so the same face is quiet at 13 px and loud at 300 px. */
const face = localFont({
  src: "../../node_modules/@fontsource-variable/bricolage-grotesque/files/bricolage-grotesque-latin-opsz-normal.woff2",
  variable: "--font-face",
  weight: "200 800",
  display: "swap",
  adjustFontFallback: "Arial",
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={face.variable}>
      <body>
        <SmoothScroll />
        {children}
      </body>
    </html>
  );
}
