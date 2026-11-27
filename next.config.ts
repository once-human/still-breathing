import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // the old addresses (lineup 01, the lineups index) go to where those pages are now
  async redirects() {
    return [
      { source: "/lineups", destination: "/shop", permanent: true },
      { source: "/lineup-01", destination: "/fred-again-india", permanent: true },
      { source: "/lineup-01/:shirt", destination: "/fred-again-india/:shirt", permanent: true },
    ];
  },
  async headers() {
    return [
      { source: "/tee/:path*", headers: [{ key: "Cache-Control", value: "public, max-age=86400, stale-while-revalidate=604800" }] },
      { source: "/draco/:path*", headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }] },
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
          // the try-on needs the camera, on this site only; nothing else asks for a sensor
          { key: "Permissions-Policy", value: "camera=(self), microphone=(), geolocation=(), usb=(), serial=(), bluetooth=(), hid=()" },
          { key: "Cross-Origin-Opener-Policy", value: "same-origin-allow-popups" },
          // no plugins, no <base> swaps, no framing by other sites; scripts stay as they are so Razorpay's checkout works
          { key: "Content-Security-Policy", value: "base-uri 'self'; object-src 'none'; frame-ancestors 'self'; upgrade-insecure-requests" },
        ],
      },
      {
        // the admin: never framed, never cached, never indexed
        source: "/admin/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Cache-Control", value: "no-store" },
          { key: "X-Robots-Tag", value: "noindex, nofollow" },
        ],
      },
      { source: "/api/admin/:path*", headers: [{ key: "Cache-Control", value: "no-store" }, { key: "X-Robots-Tag", value: "noindex" }] },
    ];
  },
};

export default nextConfig;
