"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { clearActiveWorkspace } from "@/lib/active-workspace";
import {
  claimsToUser,
  claimsValid,
  clearTokenCookie,
  decodeJwtPayload,
  readTokenCookie,
  writeTokenCookie,
  type AuthUser,
} from "@/lib/auth-token";

type AuthState = {
  user: AuthUser | null;
  /** True only for role "admin" — the gate for the whole seller portal. */
  isAdmin: boolean;
  /** True for an activated seller account or a platform administrator. */
  isSeller: boolean;
  /** True while a login/register request is in flight. */
  busy: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  register: (email: string, password: string, name?: string) => Promise<AuthUser>;
  acceptAccessToken: (token: string) => AuthUser;
  refreshSession: () => Promise<AuthUser | null>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

type TokenPayload = { access_token: string; token_type: string; user: AuthUser };

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  // Seed from the cookie synchronously so the first paint already knows who
  // the user is — no /auth/me round trip on every page load, and no flash of
  // "logged out" chrome for a signed-in admin.
  const [user, setUser] = useState<AuthUser | null>(null);
  const [busy, setBusy] = useState(false);

  const acceptAccessToken = useCallback((token: string): AuthUser => {
    const claims = decodeJwtPayload(token);
    if (!claimsValid(claims)) {
      throw new Error("Backend returned an invalid access token.");
    }
    const nextUser = claimsToUser(claims!);
    writeTokenCookie(token);
    setUser(nextUser);
    return nextUser;
  }, []);

  // Drop an expired/garbage cookie left over from a previous session.
  useEffect(() => {
    const token = readTokenCookie();
    const claims = token ? decodeJwtPayload(token) : null;
    if (token && !claimsValid(claims)) {
      clearTokenCookie();
      setUser(null);
    } else if (claims) {
      setUser(claimsToUser(claims));
    }
  }, []);

  const refreshSession = useCallback(async (): Promise<AuthUser | null> => {
    const token = readTokenCookie();
    if (!token || !claimsValid(decodeJwtPayload(token))) return null;
    const env = await api.post<TokenPayload>("/auth/refresh", {});
    return acceptAccessToken((env.data as TokenPayload).access_token);
  }, [acceptAccessToken]);

  // A workspace invitation may promote a buyer while their existing JWT still
  // has the old role. Refresh from database state once per app mount.
  useEffect(() => {
    void refreshSession().catch(() => {
      // api.ts owns 401 handling. A transient error keeps the valid session.
    });
  }, [refreshSession]);

  const authenticate = useCallback(
    async (path: "/auth/login" | "/auth/register", body: unknown) => {
      setBusy(true);
      try {
        const env = await api.post<TokenPayload>(path, body);
        const data = env.data as TokenPayload;
        writeTokenCookie(data.access_token);
        setUser(data.user);
        return data.user;
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  const value = useMemo<AuthState>(
    () => ({
      user,
      isAdmin: user?.role === "admin",
      isSeller: user?.role === "admin" || user?.role === "seller",
      busy,
      login: (email, password) => authenticate("/auth/login", { email, password }),
      register: (email, password, name) =>
        authenticate("/auth/register", { email, password, name: name || null }),
      acceptAccessToken,
      refreshSession,
      logout: () => {
        clearTokenCookie();
        clearActiveWorkspace();
        setUser(null);
        router.replace("/shop");
      },
    }),
    [user, busy, authenticate, acceptAccessToken, refreshSession, router],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>.");
  return ctx;
}
