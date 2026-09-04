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
import { useT } from "@/lib/i18n";

type Mode = "traditional" | "ai";

/** Signals shown to shoppers — Vietnamese labels, not raw feature keys. */
const PROFILE_CHIPS = [
  { label: "Khách mẫu", value: "C001" },
  { label: "Kênh ưa thích", value: "Shopee" },
  { label: "Đã mua", value: "lịch sử đơn Mây House" },
  { label: "Quan tâm", value: "serum, dưỡng ẩm" },
];

// Gửi lên API, không hiển thị: giữ tiếng Việt. Backend khớp ý định người mua
// trên chuỗi này, dịch sang tiếng Anh là mất khớp.
const SIGNAL_PAYLOAD = {
  intent: "serum dưỡng ẩm",
  preferred_channel: "Shopee",
};

const VND = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});

export function RecsysPanel() {
  const t = useT();
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
            {t("Người mua tương tự")}
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
            {t("Gợi ý theo bạn")}
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-2xs font-medium uppercase tracking-wider text-text-dim">
            Hồ sơ mẫu
          </span>
          {PROFILE_CHIPS.map((s) => (
            <Badge key={s.label} variant="muted">
              <span className="normal-case tracking-normal">
                {t(s.label)}: <span className="text-text">{t(s.value)}</span>
              </span>
            </Badge>
          ))}
        </div>
      </div>

      {error && mode === "ai" && (
        <p className="text-sm text-danger">
          {t("Không lấy được gợi ý. Kiểm tra kết nối backend rồi thử lại.")}
        </p>
      )}

      <Card>
        <CardHeader>
          <div>
            <CardTitle>
              {mode === "ai"
                ? t("Gợi ý theo hồ sơ minh hoạ")
                : t("Sản phẩm mua cùng minh hoạ")}
            </CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              {mode === "ai"
                ? t("Dữ liệu mẫu để minh hoạ luồng cá nhân hoá; chưa lấy lịch sử thật của tài khoản.")
                : t("Dữ liệu mẫu; chưa có ma trận đồng mua thật từ cửa hàng.")}
            </p>
          </div>
          <Badge variant={mode === "ai" ? "live" : "muted"}>
            {mode === "ai" ? t("Hồ sơ demo") : t("Dữ liệu demo")}
          </Badge>
        </CardHeader>
      </Card>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((p, i) => (
          <div key={p.id} className="space-y-2">
            <ProductCard product={p} similarity={p.similarity ?? 0.5 + i * 0.05} />
            <div className="rounded-md border border-border bg-surface px-3 py-2 text-xs text-text-muted">
              <span className="text-2xs font-medium uppercase tracking-wider text-text-dim">
                {t("Vì sao phù hợp")}
              </span>
              <p className="mt-1 leading-relaxed text-text">{p.reason}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <InsightCard
          label={t("Độ khớp TB")}
          value={insights.matchPct}
          hint={t("Trung bình mức phù hợp với hồ sơ")}
        />
        <InsightCard
          label={t("Số gợi ý")}
          value={insights.count}
          hint={t("Sản phẩm trong danh sách dành cho bạn")}
        />
        <InsightCard
          label={t("Khoảng giá")}
          value={insights.priceRange}
          hint={t("Từ thấp nhất đến cao nhất")}
        />
        <InsightCard
          label={t("Đánh giá TB")}
          value={insights.avgRating}
          hint={t("Sao trung bình các món gợi ý")}
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
