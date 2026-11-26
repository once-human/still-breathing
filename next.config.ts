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
        ],
      },
    ];
  },
};

export default nextConfig;
