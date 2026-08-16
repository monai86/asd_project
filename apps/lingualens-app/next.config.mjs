/** @type {import('next').NextConfig} */
const nextConfig = {
  devIndicators: false,
  // The e2e Playwright suite drives the app through the 127.0.0.1 loopback
  // host, which Next 16 blocks by default as a "cross-origin" dev resource
  // host. Allow it so dev resources load for e2e runs (localhost stays the
  // default-allowed host).
  allowedDevOrigins: ["127.0.0.1"]
};

export default nextConfig;
