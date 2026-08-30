import { NextResponse, type NextRequest } from "next/server";
import { TOKEN_COOKIE, claimsValid, decodeJwtPayload } from "@/lib/auth-token";

/** UX routing only. API authorization remains the security boundary. */
export function proxy(req: NextRequest) {
  const token = req.cookies.get(TOKEN_COOKIE)?.value;

  // API requests may originate from a browser session whose auth cookie is
  // visible to the server but not to client-side JavaScript (for example an
  // older HttpOnly cookie). The seller page then passes the route guard while
  // FastAPI receives no bearer token and returns 401. Bridge the session cookie
  // to the upstream request here; FastAPI still verifies the JWT signature,
  // expiry and role, so this is transport plumbing rather than authorization.
  if (req.nextUrl.pathname.startsWith("/api/v1/")) {
    if (!token || req.headers.has("authorization")) {
      return NextResponse.next();
    }

    const requestHeaders = new Headers(req.headers);
    requestHeaders.set("authorization", `Bearer ${token}`);
    return NextResponse.next({ request: { headers: requestHeaders } });
  }

  const claims = token ? decodeJwtPayload(token) : null;

  if (!claimsValid(claims)) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(req.nextUrl.pathname + req.nextUrl.search)}`;
    return NextResponse.redirect(url);
  }

  const role = claims!.role;
  const path = req.nextUrl.pathname;
  const onboardingPaths = new Set(["/seller/onboarding", "/seller/workspace"]);
  if (onboardingPaths.has(path)) return NextResponse.next();

  if (role !== "seller" && role !== "admin") {
    const url = req.nextUrl.clone();
    url.pathname = "/seller/onboarding";
    url.search = "";
    return NextResponse.redirect(url);
  }

  if (path === "/seller/content-generator" || path === "/seller/seller-coach") {
    return NextResponse.next();
  }

  if (role !== "admin") {
    const url = req.nextUrl.clone();
    url.pathname = "/seller/workspace";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/seller", "/seller/:path*", "/api/v1/:path*"],
};
