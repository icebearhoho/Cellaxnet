/**
 * Token storage + claim decoding, shared by the browser and the edge runtime.
 *
 * Deliberately NOT a `"use client"` module and it never touches `document` at
 * module scope, because `proxy.ts` imports from here and runs on the edge.
 *
 * The JWT lives in a plain, JS-readable cookie rather than an httpOnly one so
 * that both the middleware (route redirects) and `lib/api.ts` (Authorization
 * header) can read it. This makes CSP and output escaping important because a
 * successful same-origin XSS could read the token. Backend role and tenant
 * checks remain the authorization boundary.
 */

export const TOKEN_COOKIE = "area303_token";

export type Role = "admin" | "seller" | "buyer";

export type JwtClaims = {
  sub: string;
  exp: number;
  role: Role;
  email: string;
  name: string | null;
};

export type AuthUser = {
  id: number;
  email: string;
  name: string | null;
  role: Role;
};

/** Decode a JWT payload without verifying it — the client has no secret. */
export function decodeJwtPayload(token: string): JwtClaims | null {
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const raw = part.replace(/-/g, "+").replace(/_/g, "/");
    const padded = raw + (raw.length % 4 ? "=".repeat(4 - (raw.length % 4)) : "");
    const bin = atob(padded);
    // Decode as UTF-8: the `name` claim carries Vietnamese diacritics, which a
    // bare atob() would mangle into mojibake.
    const bytes = Uint8Array.from(bin, (ch) => ch.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes)) as JwtClaims;
  } catch {
    return null;
  }
}

export function claimsValid(claims: JwtClaims | null): boolean {
  return !!claims && typeof claims.exp === "number" && claims.exp * 1000 > Date.now();
}

export function claimsToUser(claims: JwtClaims): AuthUser {
  return {
    id: Number(claims.sub),
    email: claims.email ?? "",
    name: claims.name ?? null,
    role: claims.role ?? "buyer",
  };
}

export function readTokenCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp(`(?:^|;\\s*)${TOKEN_COOKIE}=([^;]*)`),
  );
  return match ? decodeURIComponent(match[1]) : null;
}

export function writeTokenCookie(token: string): void {
  if (typeof document === "undefined") return;
  const secure = typeof location !== "undefined" && location.protocol === "https:";
  document.cookie =
    `${TOKEN_COOKIE}=${encodeURIComponent(token)}; path=/; max-age=86400; samesite=lax` +
    (secure ? "; secure" : "");
}

export function clearTokenCookie(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${TOKEN_COOKIE}=; path=/; max-age=0; samesite=lax`;
}
