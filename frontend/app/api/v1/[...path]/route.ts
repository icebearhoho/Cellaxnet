import type { NextRequest } from "next/server";

const backendUrl = (
  process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8010"
).replace(/\/$/, "");

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-length",
  "content-encoding",
  "expect",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxyRequest(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const upstream = new URL(`${backendUrl}/api/v1/${path.join("/")}`);
  upstream.search = request.nextUrl.search;

  const requestHeaders = new Headers(request.headers);
  for (const name of HOP_BY_HOP_HEADERS) requestHeaders.delete(name);

  const response = await fetch(upstream, {
    method: request.method,
    headers: requestHeaders,
    body:
      request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.arrayBuffer(),
    cache: "no-store",
    redirect: "follow",
  });

  const responseHeaders = new Headers(response.headers);
  for (const name of HOP_BY_HOP_HEADERS) responseHeaders.delete(name);

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

export const dynamic = "force-dynamic";

export const GET = proxyRequest;
export const HEAD = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
export const OPTIONS = proxyRequest;
