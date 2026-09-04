"use client";

import { useCallback, useEffect, useState } from "react";
import { Search, MousePointerClick, Eye, MessageSquareText, ShoppingCart, CreditCard, Radio, Loader2, RefreshCw, Sparkles, X, ArrowRight, Video } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ProductCard } from "@/components/genai/product-card";
import {
  analyzeJourney,
  getJourneySessions,
  trackJourneyEvents,
  type JourneyEventInput,
  type JourneyResultMapped,
  type JourneySessions,
  type JourneySession,
} from "@/lib/features";
import { getTracked, clearTracked, getSessionId, JOURNEY_EVENT, type TrackedEvent } from "@/lib/journey-track";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

const EVENT_TYPES = [
  { type: "search", label: "Tìm kiếm", icon: Search },
  { type: "click", label: "Click", icon: MousePointerClick },
  { type: "view", label: "Xem sản phẩm", icon: Eye },
  { type: "review", label: "Đọc đánh giá", icon: MessageSquareText },
  { type: "cart", label: "Thêm vào giỏ", icon: ShoppingCart },
  { type: "purchase", label: "Mua hàng", icon: CreditCard },
  { type: "livestream", label: "Xem livestream", icon: Radio },
] as const;

const NEXT_ACTION_STYLE: Record<string, { cls: string }> = {
  checkout: { cls: "text-success" },
  add_to_cart: { cls: "text-accent" },
  compare: { cls: "text-warning" },
  keep_browsing: { cls: "text-text" },
  leave: { cls: "text-danger" },
};

const FUNNEL_LABEL: Record<string, string> = {
  awareness: "Nhận biết", consideration: "Cân nhắc", intent: "Có ý định", purchase: "Đã mua",
};
const FUNNEL_ORDER = ["awareness", "consideration", "intent", "purchase"];

type Result = JourneyResultMapped;

export function CustomerJourneyPanel() {
  const t = useT();
  // --- primary: real sessions ---
  const [sessions, setSessions] = useState<JourneySessions | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    setSessionsError(false);
    const r = await getJourneySessions();
    setSessionsError(r === null);
    setSessions(r);
    setSessionsLoading(false);
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // --- shared result state ---
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoFailed, setVideoFailed] = useState(false);

  function pickSession(s: JourneySession) {
    setSelectedId(s.id);
    setError(false);
    setVideoUrl(s.video_url ?? null);
    setVideoFailed(false);
    // Reuse the existing rich result view. The session analysis is the raw
    // JourneyResult shape; product cards are skipped to avoid type friction.
    setResult({ ...s.analysis, recommended_products: [] });
  }

  // --- live: the shopper's real tracked session (from the Shop app) ---
  const [live, setLive] = useState<TrackedEvent[]>([]);
  useEffect(() => {
    const sync = () => setLive(getTracked());
    sync();
    window.addEventListener(JOURNEY_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(JOURNEY_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  async function analyzeLive() {
    if (busy || live.length === 0) return;
    setBusy(true);
    setError(false);
    setSelectedId(null);
    setVideoUrl(null);
    setVideoFailed(false);
    const evs: JourneyEventInput[] = live.map((e) => ({
      type: e.type as JourneyEventInput["type"], category: e.category, query: e.query, ts: e.ts,
    }));
    const r = await analyzeJourney(evs);
    setError(r === null);
    setResult(r);
    setBusy(false);
    // Fire-and-forget: persistence must never delay or break the analyze UX.
    void trackJourneyEvents(getSessionId(), evs);
  }

  return (
    <div className="space-y-4">
      {/* Shopper activity from the Shop app. */}
      <Card>
        <CardHeader>
          <div>
            <CardTitle>{t("Phiên của bạn")}</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              {t("Hoạt động trong")} <Link href="/shop/store" className="text-accent hover:underline">{t("Cửa hàng")}</Link> {t("sẽ xuất hiện ở đây. Phiên này không ghi video.")}
            </p>
          </div>
          <Badge variant={live.length ? "live" : "muted"}>{live.length} hành động</Badge>
        </CardHeader>
        <CardContent className="space-y-3">
          {live.length === 0 ? (
            <p className="text-sm text-text-muted">
              {t("Chưa có hoạt động. Hãy mở")} <Link href="/shop/store" className="text-accent hover:underline">{t("Cửa hàng")}</Link> {t("và xem vài sản phẩm.")}
            </p>
          ) : (
            <>
              <div className="flex flex-wrap gap-1.5">
                {live.map((e, i) => {
                  const meta = EVENT_TYPES.find((t) => t.type === e.type);
                  const Icon = meta?.icon ?? Search;
                  return (
                    <span key={i} className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 py-1 text-2xs text-text">
                      <Icon className="h-3 w-3" />
                      {meta?.label ?? e.type}
                      {e.query && <span className="text-text-dim">· &ldquo;{e.query}&rdquo;</span>}
                      {e.category && <span className="text-text-dim">· {t(e.category)}</span>}
                    </span>
                  );
                })}
              </div>
              <div className="flex gap-2">
                <Button onClick={analyzeLive} disabled={busy}>
                  {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                  Xem kết quả
                </Button>
                <Button variant="secondary" onClick={() => clearTracked()}>
                  <X className="h-3.5 w-3.5" /> {t("Xóa phiên")}
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Pre-built sessions picker. */}
      <Card>
        <CardHeader>
          <div>
            <CardTitle>{t("Hành trình tham khảo")}</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              {sessions
                ? `${sessions.total} hành trình đã ghi nhận để xem lại.`
                : t("Chọn một hành trình để xem lại.")}
            </p>
          </div>
          <Button variant="secondary" size="sm" onClick={loadSessions} disabled={sessionsLoading}>
            {sessionsLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Làm mới
          </Button>
        </CardHeader>
        <CardContent>
          {sessionsError ? (
            <p className="text-sm text-danger">{t("Không tải được phiên. Hãy thử lại.")}</p>
          ) : !sessions ? (
            <p className="text-sm text-text-muted">{sessionsLoading ? "Đang tải phiên…" : t("Chưa có dữ liệu.")}</p>
          ) : sessions.sessions.length === 0 ? (
            <p className="text-sm text-text-muted">{t("Chưa có phiên nào.")}</p>
          ) : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {sessions.sessions.map((s) => {
                const active = selectedId === s.id;
                const style = NEXT_ACTION_STYLE[s.analysis.predicted_next_action];
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => pickSession(s)}
                    className={cn(
                      "rounded-md border p-3 text-left transition-colors",
                      active ? "border-accent bg-accent/10" : "border-border bg-bg-alt hover:border-accent/60",
                    )}
                  >
                    <div className="flex items-center gap-1.5 text-sm font-medium text-text">
                      {t(s.label)}
                      {s.video_url && <Video className="h-3.5 w-3.5 shrink-0 text-accent" />}
                    </div>
                    <div className="mono mt-1 text-xs font-medium text-text-dim">
                      {s.events.length} bước{s.video_url && " · video"}
                    </div>
                    <div className={cn("mt-2 flex items-center gap-1 text-xs font-medium", style?.cls)}>
                      <ArrowRight className="h-3.5 w-3.5" />
                      {s.analysis.next_action_label}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {error && (
        <p className="text-sm text-danger">{t("Không tải được kết quả. Hãy thử lại.")}</p>
      )}

      {result && videoUrl && !videoFailed && (
        <Card>
          <CardHeader>
            <div>
              <CardTitle>{t("Video hành trình")}</CardTitle>
              <p className="mt-1 text-xs text-text-muted">
                {t("Video tái hiện chuỗi hành động của phiên, không phải ghi màn hình thời gian thực.")}
              </p>
            </div>
            <Badge variant="muted">
              <Video className="h-3 w-3" /> journey replay
            </Badge>
          </CardHeader>
          <CardContent>
            <video
              key={videoUrl}
              controls
              preload="metadata"
              className="w-full rounded-md border border-border"
              src={videoUrl}
              onError={() => setVideoFailed(true)}
            />
          </CardContent>
        </Card>
      )}

      {result && videoUrl && videoFailed && (
        <p className="rounded-md border border-warning/40 bg-warning/5 px-3 py-2 text-sm text-warning">
          {t("Không tải được video. Kết quả bên dưới vẫn dùng được.")}
        </p>
      )}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>{t("Bước tiếp theo")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <ArrowRight className={cn("h-6 w-6", NEXT_ACTION_STYLE[result.predicted_next_action]?.cls)} />
              <span className={cn("text-2xl font-semibold tracking-tight", NEXT_ACTION_STYLE[result.predicted_next_action]?.cls)}>
                {result.next_action_label}
              </span>
            </div>

            {/* Funnel stage tracker */}
            <div className="flex items-center gap-1">
              {FUNNEL_ORDER.map((s, i) => {
                const active = FUNNEL_ORDER.indexOf(result.funnel_stage) >= i;
                return (
                  <div key={s} className="flex flex-1 items-center gap-1">
                    <div className="flex-1">
                      <div className={cn("h-1.5 rounded-full", active ? "bg-accent" : "bg-surface-2")} />
                      <div className={cn("mono mt-1 text-2xs", active ? "text-text" : "text-text-dim")}>{FUNNEL_LABEL[s]}</div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-md border border-border bg-bg-alt px-3 py-2">
                <div className="text-xs font-medium text-text-dim">{t("Mức quan tâm")}</div>
                <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-surface-2">
                  <div className="h-full rounded-full bg-accent" style={{ width: `${Math.round(result.engagement_score * 100)}%` }} />
                </div>
                <div className="mono mt-1 text-2xs text-text-muted">{Math.round(result.engagement_score * 100)}%</div>
              </div>
              <div className="rounded-md border border-accent/30 bg-accent/5 px-3 py-2">
                <div className="text-xs font-medium text-accent">{t("Nên làm")}</div>
                <p className="mt-1 text-xs text-text">{result.nudge}</p>
              </div>
            </div>

            {(result.session_duration_seconds != null || result.avg_dwell_seconds != null
              || result.cart_abandoned != null || result.time_to_purchase_seconds != null) && (
              <div className="flex flex-wrap gap-x-4 gap-y-1.5 border-t border-border pt-3 text-xs text-text-muted">
                {result.session_duration_seconds != null && (
                  <span>{t("Thời gian trên trang:")} <span className="mono text-text">{Math.round(result.session_duration_seconds)}s</span></span>
                )}
                {result.avg_dwell_seconds != null && (
                  <span>{t("Dừng trung bình/bước:")} <span className="mono text-text">{Math.round(result.avg_dwell_seconds)}s</span></span>
                )}
                {result.cart_abandoned != null && (
                  <span>
                    Bỏ giỏ hàng:{" "}
                    <span className={cn("mono", result.cart_abandoned ? "text-danger" : "text-success")}>
                      {result.cart_abandoned ? "có" : t("không")}
                    </span>
                  </span>
                )}
                {result.time_to_purchase_seconds != null && (
                  <span>{t("Thời gian đến khi mua:")} <span className="mono text-text">{Math.round(result.time_to_purchase_seconds)}s</span></span>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {result && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader><CardTitle>{t("Khả năng mua")}</CardTitle></CardHeader>
            <CardContent>
              <div className={cn("text-2xl font-semibold", result.will_purchase ? "text-success" : "text-danger")}>
                {result.will_purchase ? "Khả năng cao" : t("Khả năng thấp")}
              </div>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-surface-2">
                <div
                  className={cn("h-full rounded-full", result.will_purchase ? "bg-success" : "bg-danger")}
                  style={{ width: `${Math.round(result.purchase_probability * 100)}%` }}
                />
              </div>
              <div className="mono mt-1 text-xs text-text-muted">
                {Math.round(result.purchase_probability * 100)}% xác suất mua
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>{t("Danh mục quan tâm")}</CardTitle></CardHeader>
            <CardContent>
              <div className="text-xl font-semibold text-text">{result.top_category ?? t("Chưa rõ")}</div>
              <div className="mt-3 space-y-1.5">
                {Object.entries(result.category_breakdown).map(([cat, n]) => (
                  <div key={cat} className="flex items-center gap-2 text-xs">
                    <span className="w-20 truncate text-text-muted">{t(cat)}</span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-2">
                      <div className="h-full rounded-full bg-accent" style={{ width: `${Math.min(100, n * 20)}%` }} />
                    </div>
                    <span className="mono text-text-dim">{n}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>{t("Lý do")}</CardTitle></CardHeader>
            <CardContent>
              <p className="text-sm text-text-muted">{result.reasoning}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {result && result.recommended_products.length > 0 && (
        <Card>
          <CardHeader><CardTitle>{t("Sản phẩm phù hợp")}</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {result.recommended_products.map((p) => (
                <ProductCard key={p.id} product={p} similarity={p.similarity} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

    </div>
  );
}
