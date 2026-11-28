import type { MetadataRoute } from "next";

/** Added to a phone's home screen, sahn opens like an app: its own icon, the site's dark paper, straight to the shop. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "sahn",
    short_name: "sahn",
    description: "one shirt per moment. made to order, sent anywhere in India.",
    start_url: "/?utm_source=home-screen",
    scope: "/",
    display: "standalone",
    background_color: "#0d0d0c",
    theme_color: "#0d0d0c",
    icons: [
      { src: "/icons/sahn-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/sahn-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/sahn-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
