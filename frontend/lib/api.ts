/**
 * API client — talks to the FastAPI backend using the
 * {success, data, meta, error} envelope defined in
 * backend/app/core/responses.py.
 *
 * Demo-mode fallback: when no backend is reachable (no NEXT_PUBLIC_API_URL
 * or network error) the caller can opt into demo data via the `fallback`
 * argument. This is the contract D2 uses for `scripts/prepare_demo_data.py`.
 */

import { clearTokenCookie, readTokenCookie } from "@/lib/auth-token";
import { readActiveWorkspaceId } from "@/lib/active-workspace";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

export type ApiError = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

export type ApiEnvelope<T> = {
  success: boolean;
  data: T | null;
  meta: {
    request_id?: string | null;
    page?: number | null;
    page_size?: number | null;
    total?: number | null;
  } | null;
  error: ApiError | null;
};

export class ApiClientError extends Error {
  constructor(public envelope: ApiEnvelope<never>, public status: number) {
    super(envelope.error?.message ?? `HTTP ${status}`);
    this.name = "ApiClientError";
  }
}

async function request<T>(
  path: string,
  init?: RequestInit,
  signal?: AbortSignal,
): Promise<ApiEnvelope<T>> {
  const url = `${BASE_URL}${path}`;
  const token = readTokenCookie();
  const workspaceId = readActiveWorkspaceId();
  const res = await fetch(url, {
    ...init,
    signal,
    headers: {
      "Content-Type": "application/json",
      // Admin-gated endpoints need this; harmless when absent.
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(workspaceId ? { "X-Workspace-ID": String(workspaceId) } : {}),
      // Spread last so an explicit per-call header still wins.
      ...init?.headers,
    },
  });

  let body: ApiEnvelope<T>;
  try {
    body = (await res.json()) as ApiEnvelope<T>;
  } catch {
    throw new ApiClientError(
      {
        success: false,
        data: null,
        meta: null,
        error: { code: "INVALID_JSON", message: `Bad JSON from ${url}` },
      },
      res.status,
    );
  }

  if (!res.ok || body.success === false) {
    // Handle 401 here rather than at the call sites: lib/features.ts wraps
    // every call in try/catch and returns null, so a thrown 401 would be
    // swallowed before any panel could react to it.
    //
    // Only 401 (bad/expired token) logs out. A 403 means "signed in, wrong
    // role" — the middleware and nav gating already cover that, and kicking a
    // valid buyer out over a stray 403 would be a bug.
    if (res.status === 401 && typeof window !== "undefined") {
      clearTokenCookie();
      const here = window.location.pathname;
      if (here !== "/login" && here !== "/register") {
        const next = encodeURIComponent(here + window.location.search);
        window.location.href = `/login?next=${next}`;
      }
    }
    throw new ApiClientError(
      body as unknown as ApiEnvelope<never>,
      res.status,
    );
  }
  return body;
}

export const api = {
  get<T>(path: string, signal?: AbortSignal) {
    return request<T>(path, { method: "GET" }, signal);
  },
  post<T>(path: string, body: unknown, signal?: AbortSignal) {
    return request<T>(path, { method: "POST", body: JSON.stringify(body) }, signal);
  },
  patch<T>(path: string, body: unknown, signal?: AbortSignal) {
    return request<T>(path, { method: "PATCH", body: JSON.stringify(body) }, signal);
  },
  delete<T>(path: string, signal?: AbortSignal) {
    return request<T>(path, { method: "DELETE" }, signal);
  },
};

/**
 * Convenience helper that returns `data` from the envelope,
 * or the supplied `fallback` when the call fails / demo mode is on.
 */
export async function fetchWithFallback<T>(
  path: string,
  fallback: T,
  init?: RequestInit,
  signal?: AbortSignal,
): Promise<{ data: T; fromFallback: boolean }> {
  if (process.env.NEXT_PUBLIC_DEMO_MODE === "true") {
    return { data: fallback, fromFallback: true };
  }
  try {
    const env = await api.get<T>(path, signal);
    return { data: env.data as T, fromFallback: false };
  } catch {
    return { data: fallback, fromFallback: true };
  }
}
