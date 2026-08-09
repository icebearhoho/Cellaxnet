"use client";
/**
 * Client-side journey tracker. As a shopper acts in the Shop app (search, click,
 * view, add-to-cart, …) we record the events in localStorage; the seller's
 * Customer Journey panel then analyses that REAL session (same origin, so the
 * data is shared across /shop and /seller). No backend session store needed.
 */
export type TrackType = "search" | "click" | "view" | "review" | "cart" | "purchase" | "livestream";
export type TrackedEvent = { type: TrackType; category?: string; query?: string; ts: number };

const KEY = "area303:journey";
const MAX = 60;
export const JOURNEY_EVENT = "area303:journey";

export function trackEvent(type: TrackType, opts?: { category?: string; query?: string }): void {
  if (typeof window === "undefined") return;
  try {
    const arr = getTracked();
    arr.push({ type, category: opts?.category, query: opts?.query, ts: Date.now() });
    localStorage.setItem(KEY, JSON.stringify(arr.slice(-MAX)));
    window.dispatchEvent(new Event(JOURNEY_EVENT));
  } catch {
    /* localStorage unavailable — tracking is best-effort */
  }
}

export function getTracked(): TrackedEvent[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as TrackedEvent[]) : [];
  } catch {
    return [];
  }
}

const SESSION_ID_KEY = "area303:journey:sid";

/** Stable per-browser session id, used to group persisted events server-side. */
export function getSessionId(): string {
  if (typeof window === "undefined") return "";
  try {
    let sid = localStorage.getItem(SESSION_ID_KEY);
    if (!sid) {
      sid = crypto.randomUUID();
      localStorage.setItem(SESSION_ID_KEY, sid);
    }
    return sid;
  } catch {
    return "";
  }
}

export function clearTracked(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(KEY);
    window.dispatchEvent(new Event(JOURNEY_EVENT));
  } catch {
    /* ignore */
  }
}

/** Best-effort category guess from a free-text query (fashion vs cosmetics vs accessories). */
export function guessCategory(text: string): string | undefined {
  const q = text.toLowerCase();
  const has = (...ks: string[]) => ks.some((k) => q.includes(k));
  if (has("son", "serum", "kem", "skincare", "toner", "mặt nạ", "cushion", "chống nắng",
          "mỹ phẩm", "dưỡng", "retinol", "niacinamide", "tẩy trang", "mascara", "nước hoa"))
    return "Mỹ phẩm";
  if (has("túi", "balo", "ví", "kính", "đồng hồ", "mũ", "nón", "thắt lưng", "vòng", "khăn",
          "phụ kiện", "tote", "kẹp"))
    return "Phụ kiện";
  if (has("áo", "quần", "váy", "đầm", "jean", "hoodie", "khoác", "sơ mi", "croptop", "blazer",
          "len", "chân váy", "short", "thời trang"))
    return "Thời trang";
  return undefined;
}
