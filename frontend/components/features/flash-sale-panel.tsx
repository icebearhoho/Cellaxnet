"use client";

import { useState } from "react";
import { Loader2, Heart, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { analyzeHesitation, type FlashSaleResult } from "@/lib/features";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

export function FlashSalePanel() {
  const t = useT();
  const [dwell, setDwell] = useState(150);
  const [scroll, setScroll] = useState(85);
  const [revisits, setRevisits] = useState(2);
  const [cartAbandoned, setCartAbandoned] = useState(true);
  const [price, setPrice] = useState(650000);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<FlashSaleResult | null>(null);
  const [error, setError] = useState(false);

  async function run() {
    if (busy) return;
    setBusy(true);
    setError(false);
    const r = await analyzeHesitation({
      dwellTimeSeconds: dwell, scrollDepthPct: scroll, revisitCount: revisits,
      cartOpenedNoPurchase: cartAbandoned, priceVnd: price,
    });
    setError(r === null);
    setResult(r);
    setBusy(false);
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <Card className="lg:col-span-7">
        <CardHeader>
          <div>
            <CardTitle>Hành vi trên trang sản phẩm</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              {t("Mô phỏng tín hiệu hành vi (thời gian dừng, tốc độ scroll, số lần quay lại) để phát hiện khách “thích nhưng do dự”.")}
            </p>
          </div>
          <Badge variant="muted">behaviour simulator</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-text-dim">Thời gian dừng trên trang (giây)</label>
              <span className="mono text-xs text-text">{dwell}s</span>
            </div>
            <input type="range" min={0} max={600} value={dwell}
              onChange={(e) => setDwell(Number(e.target.value))} className="mt-1.5 w-full accent-accent" />
          </div>
          <div>
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-text-dim">Độ sâu scroll (%)</label>
              <span className="mono text-xs text-text">{scroll}%</span>
            </div>
            <input type="range" min={0} max={100} value={scroll}
              onChange={(e) => setScroll(Number(e.target.value))} className="mt-1.5 w-full accent-accent" />
          </div>
          <div>
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-text-dim">Số lần quay lại xem</label>
              <span className="mono text-xs text-text">{revisits}</span>
            </div>
            <input type="range" min={0} max={10} value={revisits}
              onChange={(e) => setRevisits(Number(e.target.value))} className="mt-1.5 w-full accent-accent" />
          </div>
          <label className="flex items-center gap-2 text-xs text-text-muted">
            <input type="checkbox" checked={cartAbandoned} onChange={(e) => setCartAbandoned(e.target.checked)} />
            Đã thêm vào giỏ nhưng chưa mua
          </label>
          <Button onClick={run} disabled={busy} className="w-full">
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Heart className="h-3.5 w-3.5" />}
            Phân tích hành vi
          </Button>
        </CardContent>
      </Card>

      <Card className="lg:col-span-5">
        <CardHeader><CardTitle>{t("Kết quả")}</CardTitle></CardHeader>
        <CardContent>
          {error ? (
            <p className="text-sm text-danger">{t("Không lấy được kết quả. Kiểm tra kết nối backend rồi thử lại.")}</p>
          ) : !result ? (
            <p className="text-sm text-text-muted">Bấm Phân tích để xem đề xuất.</p>
          ) : (
            <div className="space-y-4">
              <div className={cn("flex items-center gap-2 text-xl font-semibold",
                result.trigger_now ? "text-accent" : result.hesitating ? "text-warning" : "text-text-muted")}>
                {result.trigger_now && <Zap className="h-5 w-5" />}
                {result.trigger_now ? "Kích hoạt ưu đãi ngay" : result.hesitating ? "Khách đang do dự" : t("Bình thường")}
              </div>
              <div className="mono text-xs text-text-muted">Điểm do dự: {result.hesitation_score}</div>
              {result.suggested_discount_pct > 0 && (
                <div className="rounded-md border border-border bg-bg-alt px-3 py-2 text-xs text-text">
                  Giảm giá đề xuất: <span className="mono font-semibold text-accent">{result.suggested_discount_pct}%</span>
                </div>
              )}
              <div className="rounded-md border border-accent/30 bg-accent/10 px-3 py-2 text-sm text-text">
                {result.message}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
