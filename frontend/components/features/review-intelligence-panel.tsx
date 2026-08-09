"use client";

import { useEffect, useState } from "react";
import { Loader2, Sparkles, ShieldAlert, ShieldCheck, Check, X, Inbox } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  analyzeSentiment, detectFake, getReviewQueue, approveReview, rejectReview,
  type Sentiment, type FakeVerdict, type ReviewQueueItem,
} from "@/lib/features";
import { cn } from "@/lib/utils";

const SAMPLES = [
  { text: "Áo đẹp, vải mát, form chuẩn, giao hàng nhanh, rất hài lòng!", tag: "tích cực" },
  { text: "Color is nice but it fades quickly, okay for the price.", tag: "trung tính" },
  { text: "Poor quality, looks nothing like the photo, thin material. Disappointed.", tag: "tiêu cực" },
  { text: "Amazing! Love it! Best product ever! Highly recommend to everyone!", tag: "nghi giả" },
  { text: "Fits true to size, the linen is breathable and the stitching held up after three washes.", tag: "chi tiết thật" },
  { text: "Shop bán hàng uy tín, giao nhanh, đóng gói đẹp", tag: "chung chung" },
];

const TONE: Record<string, { label: string; cls: string }> = {
  positive: { label: "Tích cực", cls: "text-success" },
  neutral: { label: "Trung tính", cls: "text-warning" },
  negative: { label: "Tiêu cực", cls: "text-danger" },
};

export function ReviewIntelligencePanel() {
  const [text, setText] = useState(SAMPLES[0].text);
  const [rating, setRating] = useState<number>(5);
  const [busy, setBusy] = useState(false);
  const [sentiment, setSentiment] = useState<Sentiment | null>(null);
  const [verdict, setVerdict] = useState<FakeVerdict | null>(null);
  const [error, setError] = useState(false);

  async function run() {
    if (!text.trim() || busy) return;
    setBusy(true);
    setError(false);
    const [s, v] = await Promise.all([analyzeSentiment(text, rating), detectFake(text, rating)]);
    setError(s === null && v === null);
    setSentiment(s);
    setVerdict(v);
    setBusy(false);
  }

  const tone = sentiment ? TONE[sentiment.sentiment] : null;
  const fake = verdict?.is_fake;
  const hasResult = sentiment || verdict;

  return (
    <div className="space-y-4">
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <Card className="lg:col-span-7">
        <CardHeader>
          <div>
            <CardTitle>Đánh giá của khách</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              Dán review của khách — hệ thống phân loại cảm xúc và phát hiện review giả cùng lúc.
            </p>
          </div>
          <Badge variant="muted">VN + EN</Badge>
        </CardHeader>
        <CardContent className="space-y-3">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={5}
            className="w-full resize-none rounded-md border border-border bg-bg-alt px-3 py-2 text-sm text-text outline-none focus:border-accent"
            placeholder="Nhập nội dung review…"
          />
          <div className="flex flex-wrap items-center gap-3">
            <label className="mono text-2xs uppercase tracking-wider text-text-dim">Số sao</label>
            <div className="inline-flex overflow-hidden rounded-md border border-border">
              {[1, 2, 3, 4, 5].map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setRating(r)}
                  className={cn(
                    "mono h-8 w-8 text-xs transition-colors",
                    rating === r ? "bg-accent/15 text-accent" : "text-text-muted hover:text-text",
                  )}
                >
                  {r}
                </button>
              ))}
            </div>
            <Button onClick={run} disabled={busy} className="ml-auto">
              {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
              Phân tích
            </Button>
          </div>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {SAMPLES.map((s, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setText(s.text)}
                title={s.text}
                className="rounded-full border border-border bg-surface px-2.5 py-1 text-2xs text-text-muted hover:border-accent hover:text-text"
              >
                Mẫu {i + 1} · {s.tag}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="lg:col-span-5">
        <CardHeader>
          <CardTitle>Kết quả</CardTitle>
        </CardHeader>
        <CardContent>
          {error ? (
            <p className="text-sm text-danger">Không lấy được kết quả. Kiểm tra kết nối backend rồi thử lại.</p>
          ) : !hasResult ? (
            <p className="text-sm text-text-muted">Bấm Phân tích để xem cảm xúc và mức độ đáng tin của đánh giá.</p>
          ) : (
            <div className="space-y-5">
              {sentiment && (
                <div className="space-y-2 border-b border-border pb-4">
                  <div className="flex items-center justify-between">
                    <span className="mono text-2xs uppercase tracking-wider text-text-dim">Cảm xúc</span>
                    <Badge variant="muted">Tin cậy {Math.round(sentiment.confidence * 100)}%</Badge>
                  </div>
                  <div className={cn("text-2xl font-semibold tracking-tight", tone?.cls)}>{tone?.label}</div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                    <div
                      className="h-full rounded-full bg-accent transition-all"
                      style={{ width: `${Math.round(sentiment.confidence * 100)}%` }}
                    />
                  </div>
                  <p className="text-sm text-text-muted">{sentiment.reason}</p>
                </div>
              )}

              {verdict && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="mono text-2xs uppercase tracking-wider text-text-dim">Độ đáng tin</span>
                    <Badge variant="muted">Tin cậy {Math.round(verdict.confidence * 100)}%</Badge>
                  </div>
                  <div className={cn("flex items-center gap-2 text-2xl font-semibold tracking-tight",
                    fake ? "text-danger" : "text-success")}>
                    {fake ? <ShieldAlert className="h-5 w-5" /> : <ShieldCheck className="h-5 w-5" />}
                    {fake ? "Có dấu hiệu giả" : "Có vẻ đáng tin"}
                  </div>
                  <p className="text-sm text-text-muted">{verdict.reason}</p>
                  {verdict.signals.length > 0 && (
                    <div>
                      <div className="mono text-2xs uppercase tracking-wider text-text-dim">Dấu hiệu</div>
                      <ul className="mt-2 space-y-1">
                        {verdict.signals.map((s, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-text-muted">
                            <span className={cn("mt-1 h-1.5 w-1.5 shrink-0 rounded-full",
                              fake ? "bg-danger" : "bg-text-dim")} />
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
    <ReviewQueuePanel />
    </div>
  );
}

function ReviewQueuePanel() {
  const [items, setItems] = useState<ReviewQueueItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    setItems(await getReviewQueue());
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  async function decide(id: number, action: "approve" | "reject") {
    setBusyId(id);
    const res = action === "approve" ? await approveReview(id) : await rejectReview(id);
    if (res) setItems((prev) => (prev ?? []).filter((r) => r.id !== id));
    setBusyId(null);
  }

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Đánh giá thật — chờ duyệt</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            Đánh giá do khách gửi bị hệ thống gắn cờ nghi ngờ, cần seller duyệt trước khi hiển thị.
          </p>
        </div>
        <Badge variant="muted">{items?.length ?? 0} chờ duyệt</Badge>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-text-muted">Đang tải…</p>
        ) : !items || items.length === 0 ? (
          <p className="flex items-center gap-2 text-sm text-text-muted">
            <Inbox className="h-4 w-4" /> Không có đánh giá nào cần duyệt.
          </p>
        ) : (
          <div className="space-y-3">
            {items.map((r) => (
              <div key={r.id} className="rounded-md border border-warning/40 bg-warning/5 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-text">{r.author_name} · {r.product_name}</span>
                  <span className="mono text-2xs text-text-dim">{r.rating}★</span>
                </div>
                <p className="mt-1 text-sm text-text-muted">{r.text}</p>
                {r.moderation_reason && (
                  <p className="mt-1 text-xs text-warning">{r.moderation_reason}</p>
                )}
                <div className="mt-2 flex gap-2">
                  <Button size="sm" onClick={() => decide(r.id, "approve")} disabled={busyId === r.id}>
                    <Check className="h-3.5 w-3.5" /> Duyệt
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => decide(r.id, "reject")} disabled={busyId === r.id}>
                    <X className="h-3.5 w-3.5" /> Từ chối
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
