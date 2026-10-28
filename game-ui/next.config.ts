import type { NextConfig } from "next";

// Security headers on every page (S1.1, 2026-10-28). Set here, not in Caddy, so they hold wherever the console runs
// (through Caddy, on 127.0.0.1:4000, in the Docker Caddy later). HSTS is left out on purpose until every office PC
// trusts the Caddy root certificate: with HSTS a browser no longer lets people click past a certificate warning.
const CSP = [
  "default-src 'self'", // only the console's own files
  `script-src 'self' 'unsafe-inline'${process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : ""}`, // Next.js inline start-up scripts (dev reload needs eval)
  "style-src 'self' 'unsafe-inline'", // React style={...}
  "img-src 'self' data: blob:", // 3D textures drawn in the page
  "font-src 'self'", // fonts are files inside the app (offline)
  "connect-src 'self'", // the browser only ever talks to the console itself, never to FastAPI
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'", // never inside another site's frame (clickjacking)
].join("; ");

const SECURITY_HEADERS = [
  { key: "Content-Security-Policy", value: CSP },
  { key: "X-Frame-Options", value: "DENY" }, // frame-ancestors for older browsers
  { key: "X-Content-Type-Options", value: "nosniff" }, // never guess a file's type
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
];

const nextConfig: NextConfig = {
  // Docker (9.5.3): build a self-contained server (.next/standalone) so the image needs no modules folder
  output: "standalone",
  poweredByHeader: false, // no "X-Powered-By: Next.js"
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
};

export default nextConfig;
