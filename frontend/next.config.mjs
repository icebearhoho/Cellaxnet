const publicApiOrigin = (() => {
  try {
    const configured = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
    return configured.startsWith("http") ? new URL(configured).origin : null;
  } catch {
    return null;
  }
})();

const backendInternalUrl = (
  process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8010"
).replace(/\/$/, "");

const connectSources = ["'self'", "http://127.0.0.1:8000", "http://127.0.0.1:8010"];
if (publicApiOrigin) connectSources.push(publicApiOrigin);

const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  "style-src 'self' 'unsafe-inline'",
  `script-src 'self' 'unsafe-inline'${process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : ""}`,
  `connect-src ${connectSources.join(" ")}`,
  "media-src 'self' blob:",
  "worker-src 'self' blob:",
  ...(process.env.NODE_ENV === "production" ? ["upgrade-insecure-requests"] : []),
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: contentSecurityPolicy },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(self)" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
];

if (process.env.NODE_ENV === "production") {
  securityHeaders.push({
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload",
  });
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // FastAPI mounts several collection endpoints at a trailing-slash route
  // (for example /api/v1/risk-portfolio/), and the backend runs with
  // redirect_slashes=False so a slash-less request 404s instead of bouncing
  // the browser to the backend origin. Next normalises the trailing slash off
  // every incoming pathname before matching, so the rewrite has to put it back.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      // Collection routes: append the slash Next stripped during normalisation.
      // A `:path*` source never sees the trailing slash, so matching on one
      // (`/api/v1/:path*/`) is dead weight — these segments carry it instead.
      // Covers risk-portfolio, churn, regret, return-prediction, pricing, etc.
      ...[
        "workspaces",
        "recsys",
        "content-generator",
        "review-sentiment",
        "fake-review",
        "seller-coach",
        "segmentation",
        "dynamic-pricing",
        "churn",
        "journey",
        "return-prediction",
        "regret",
        "risk-portfolio",
        "inventory-alert",
        "supply-chain",
        "product-knowledge",
        "market-intelligence",
        "creator-performance",
        "decision-intelligence",
        "flash-sale",
      ].map((segment) => ({
        source: `/api/v1/${segment}`,
        destination: `${backendInternalUrl}/api/v1/${segment}/`,
      })),
      // Everything else passes through untouched.
      {
        source: "/api/v1/:path*",
        destination: `${backendInternalUrl}/api/v1/:path*`,
      },
    ];
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
