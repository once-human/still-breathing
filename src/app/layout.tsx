import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { SmoothScroll } from "@/components/SmoothScroll";
import { Beacon } from "@/components/Beacon";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ShirtTextProvider } from "@/components/ShirtText";
import { shirtTexts } from "@/lib/live";
import { SITE_URL, og } from "@/lib/site";
import { JsonLd } from "@/components/JsonLd";
import { box } from "@/content/mail";

const description = "sahn makes one shirt per moment. fred again.. india: five fan-made shirts for Fred again..'s December shows in India, drawn by hand from the crowd and the grounds, made to order and sent anywhere in India.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "sahn", template: "%s · sahn" },
  description,
  applicationName: "sahn",
  openGraph: { type: "website", siteName: "sahn", title: "sahn", description, locale: "en_IN", images: [og("home")] },
  twitter: { card: "summary_large_image" },
};

export const viewport: Viewport = { themeColor: "#0d0d0c", colorScheme: "dark" };

/** Bricolage Grotesque: optical sizes, so the same face is quiet at 13 px and loud at 300 px. */
const face = localFont({
  src: "../../node_modules/@fontsource-variable/bricolage-grotesque/files/bricolage-grotesque-latin-opsz-normal.woff2",
  variable: "--font-face",
  weight: "200 800",
  display: "swap",
  adjustFontFallback: "Arial",
});

/** Gochi Hand: the handwriting of the notes and arrows on the shirts, for the few hand-made marks on the page */
const hand = localFont({ src: "./fonts/GochiHand-Regular.ttf", variable: "--font-handwriting", display: "swap", preload: false });

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${face.variable} ${hand.variable}`}>
      <body>
        <SmoothScroll />
        <Beacon />
        <ShirtTextProvider value={await shirtTexts()}>
        <Header />
        <main id="main" className="min-h-[70vh] pt-[5.25rem] md:pt-[5.75rem]">{children}</main>
        <Footer />
        </ShirtTextProvider>
        <JsonLd
          data={{
            "@context": "https://schema.org",
            "@graph": [
              { "@type": "OnlineStore", "@id": `${SITE_URL}/#shop`, name: "sahn", url: SITE_URL, logo: `${SITE_URL}/icons/sahn-512.png`, email: box("hello"), areaServed: "IN" },
              { "@type": "WebSite", "@id": `${SITE_URL}/#site`, name: "sahn", url: SITE_URL, publisher: { "@id": `${SITE_URL}/#shop` }, inLanguage: "en-IN" },
            ],
          }}
        />
      </body>
    </html>
  );
}
