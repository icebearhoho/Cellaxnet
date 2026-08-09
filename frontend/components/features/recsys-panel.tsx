"use client";

import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProductCard } from "@/components/genai/product-card";
import { cn } from "@/lib/utils";
import {
  RECSYS_TRADITIONAL,
  RECSYS_AI,
  type Recommendation,
} from "@/lib/mock-data";
import { recsysRecommend } from "@/lib/features";

type Mode = "traditional" | "ai";

/** Signals shown to shoppers — Vietnamese labels, not raw feature keys. */
const PROFILE_CHIPS = [
  { label: "Loại da", value: "Da khô" },
  { label: "Tone da", value: "Sáng" },
  { label: "Đã mua gần đây", value: "Serum BHA" },
  { label: "Hay xem", value: "Tote canvas, tone đất" },
  { label: "Review của bạn", value: "Tích cực" },
];

const SIGNAL_PAYLOAD = {
  skin_type: "dry",
  skin_tone: "light",
  bought_30d: "BHA serum",
  browse_14d: "earth-tone canvas",
  review_sentiment: "+0.71",
};

const VND = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});

export function RecsysPanel() {
  const [mode, setMode] = useState<Mode>("ai");
  const [aiItems, setAiItems] = useState<Recommendation[]>(RECSYS_AI);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
    recsysRecommend(SIGNAL_PAYLOAD, 8, RECSYS_AI)
      .then((r) => setAiItems(r.items))
      .catch(() => setError(true));
  }, []);

  const items: Recommendation[] = mode === "ai" ? aiItems : RECSYS_TRADITIONAL;

  const insights = useMemo(() => {
    if (!items.length) {
      return {
        matchPct: "—",
        count: "0",
        priceRange: "—",
        avgRating: "—",
      };
    }
    const avgSim =
      items.reduce((s, p) => s + (p.similarity ?? 0.7), 0) / items.length;
    const prices = items.map((p) => p.priceVnd);
    const minP = Math.min(...prices);
    const maxP = Math.max(...prices);
    const avgRating =
      items.reduce((s, p) => s + p.rating, 0) / items.length;
    return {
      matchPct: `${Math.round(avgSim * 100)}%`,
      count: String(items.length),
      priceRange:
        minP === maxP
          ? VND.format(minP).replace(/\s*₫/g, "") + "₫"
          : `${VND.format(minP).replace(/\s*₫/g, "")} – ${VND.format(maxP).replace(/\s*₫/g, "")}₫`,
      avgRating: avgRating.toFixed(1),
    };
  }, [items]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="inline-flex h-9 items-center rounded-md border border-border bg-surface p-0.5">
          <button
            type="button"
            onClick={() => setMode("traditional")}
            className={cn(
              "h-8 rounded-[6px] px-3 text-xs font-medium transition-colors",
              mode === "traditional"
                ? "bg-surface-3 text-text"
                : "text-text-muted hover:text-text",
            )}
          >
            Người mua tương tự
          </button>
          <button
            type="button"
            onClick={() => setMode("ai")}
            className={cn(
              "h-8 rounded-[6px] px-3 text-xs font-medium transition-colors",
              mode === "ai"
                ? "bg-accent/15 text-accent"
                : "text-text-muted hover:text-text",
            )}
          >
            Gợi ý theo bạn
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-2xs font-medium uppercase tracking-wider text-text-dim">
            Hồ sơ mua sắm
          </span>
          {PROFILE_CHIPS.map((s) => (
            <Badge key={s.label} variant="muted">
              <span className="normal-case tracking-normal">
                {s.label}: <span className="text-text">{s.value}</span>
              </span>
            </Badge>
          ))}
        </div>
      </div>

      {error && mode === "ai" && (
        <p className="text-sm text-danger">
          Không lấy được gợi ý. Kiểm tra kết nối backend rồi thử lại.
        </p>
      )}

      <Card>
        <CardHeader>
          <div>
            <CardTitle>
              {mode === "ai"
                ? "Gợi ý cá nhân hoá cho bạn"
                : "Được mua cùng bởi người giống bạn"}
            </CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              {mode === "ai"
                ? "Dựa trên loại da, đơn gần đây và sản phẩm bạn hay xem — kèm lý do từng món."
                : "Những món người mua có hành vi tương tự thường chọn thêm."}
            </p>
          </div>
          <Badge variant={mode === "ai" ? "live" : "muted"}>
            {mode === "ai" ? "Theo hồ sơ của bạn" : "Theo cộng đồng"}
          </Badge>
        </CardHeader>
      </Card>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((p, i) => (
          <div key={p.id} className="space-y-2">
            <ProductCard product={p} similarity={p.similarity ?? 0.5 + i * 0.05} />
            <div className="rounded-md border border-border bg-surface px-3 py-2 text-xs text-text-muted">
              <span className="text-2xs font-medium uppercase tracking-wider text-text-dim">
                Vì sao phù hợp
              </span>
              <p className="mt-1 leading-relaxed text-text">{p.reason}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <InsightCard
          label="Độ khớp TB"
          value={insights.matchPct}
          hint="Trung bình mức phù hợp với hồ sơ"
        />
        <InsightCard
          label="Số gợi ý"
          value={insights.count}
          hint="Sản phẩm trong danh sách dành cho bạn"
        />
        <InsightCard
          label="Khoảng giá"
          value={insights.priceRange}
          hint="Từ thấp nhất đến cao nhất"
        />
        <InsightCard
          label="Đánh giá TB"
          value={insights.avgRating}
          hint="Sao trung bình các món gợi ý"
        />
      </div>
    </div>
  );
}

function InsightCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <Card>
      <CardContent className="space-y-1 py-4">
        <div className="text-2xs font-medium uppercase tracking-wider text-text-dim">
          {label}
        </div>
        <div className="text-lg font-semibold leading-snug text-text" data-tnum>
          {value}
        </div>
        <div className="text-2xs text-text-muted">{hint}</div>
      </CardContent>
    </Card>
  );
}
