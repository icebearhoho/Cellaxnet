"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Loader2,
  RefreshCw,
  PackagePlus,
  TrendingDown,
  Tag,
  Search,
  Megaphone,
  type LucideIcon,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getBriefing, type BriefingResult, type BriefingAction } from "@/lib/features";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

function vnd(n: number) {
  return n.toLocaleString("vi-VN") + "₫";
}

const KIND: Record<BriefingAction["kind"], { label: string; icon: LucideIcon }> = {
  restock: { label: "Nhập thêm hàng", icon: PackagePlus },
  reduce: { label: "Giảm tồn kho", icon: TrendingDown },
  reprice: { label: "Điều chỉnh giá", icon: Tag },
  investigate: { label: "Điều tra nguyên nhân", icon: Search },
  promote: { label: "Đẩy khuyến mãi", icon: Megaphone },
};

const PRIORITY: Record<BriefingAction["priority"], { label: string; variant: "danger" | "warning" | "muted" }> = {
  high: { label: "Ưu tiên cao", variant: "danger" },
  medium: { label: "Trung bình", variant: "warning" },
  low: { label: "Thấp", variant: "muted" },
};

export function DailyBriefingPanel() {
  const t = useT();
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<BriefingResult | null>(null);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setError(false);
    const r = await getBriefing();
    setError(r === null);
    setResult(r);
    setBusy(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div>
            <CardTitle>{t("Hôm nay cần làm gì")}</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              {t("Việc ưu tiên theo tác động doanh thu, tổng hợp từ các tín hiệu của cửa hàng.")}
            </p>
          </div>
          <Button variant="secondary" size="sm" onClick={load} disabled={busy}>
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Làm mới
          </Button>
        </CardHeader>
        <CardContent>
          {error ? (
            <p className="text-sm text-danger">{t("Không lấy được briefing. Kiểm tra kết nối backend rồi thử lại.")}</p>
          ) : !result ? (
            <p className="text-sm text-text-muted">
              {busy ? "Đang tổng hợp briefing…" : t("Chưa có dữ liệu.")}
            </p>
          ) : (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="max-w-2xl text-sm leading-relaxed text-text">{result.summary}</p>
              <div className="shrink-0 rounded-md border border-accent/40 bg-accent/10 px-3 py-2 text-right">
                <div className="text-xs font-medium text-text-dim">{t("Tổng tác động ước tính")}</div>
                <div className="mono mt-1 text-xl font-semibold text-accent">{vnd(result.total_impact_vnd)}</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {result && result.actions.length > 0 && (
        <div className="space-y-3">
          {result.actions.map((a, i) => {
            const kind = KIND[a.kind];
            const pri = PRIORITY[a.priority];
            const KindIcon = kind?.icon ?? Search;
            return (
              <Card key={i}>
                <CardContent className="py-4">
                  <div className="flex items-start gap-3">
                    <span
                      className={cn(
                        "mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md border",
                        a.priority === "high"
                          ? "border-danger/40 bg-danger/10 text-danger"
                          : a.priority === "medium"
                            ? "border-warning/40 bg-warning/10 text-warning"
                            : "border-border bg-bg-alt text-text-muted",
                      )}
                    >
                      <KindIcon className="h-4 w-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={pri?.variant ?? "muted"}>{pri?.label ?? a.priority}</Badge>
                        <span className="text-xs font-medium text-text-dim">
                          {kind?.label ?? a.kind}
                        </span>
                      </div>
                      <div className="mt-1.5 text-sm font-medium text-text">{a.title}</div>
                      <div className="mono text-2xs text-text-dim">{a.product}</div>
                      <p className="mt-2 text-xs leading-relaxed text-text-muted">{a.detail}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="text-xs font-medium text-text-dim">{t("Tác động")}</div>
                      <div className="mono mt-1 text-lg font-semibold text-accent">{vnd(a.impact_vnd)}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {result && result.actions.length === 0 && !error && (
        <Card>
          <CardContent className="py-6">
            <p className="text-sm text-text-muted">{t("Hôm nay không có việc ưu tiên nào. Shop đang ổn định.")}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
