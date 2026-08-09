"use client";

import { useState } from "react";
import { Loader2, MessageSquare, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { checkInventoryAlert, type InventoryAlertResult } from "@/lib/features";
import { cn } from "@/lib/utils";

const LEVEL: Record<string, { label: string; cls: string }> = {
  none: { label: "Bình thường", cls: "text-success" },
  watch: { label: "Theo dõi", cls: "text-warning" },
  urgent: { label: "Khẩn cấp", cls: "text-danger" },
};

export function InventoryAlertPanel() {
  const [name, setName] = useState("Son tint lì Bourjois Velvet 21");
  const [mentions, setMentions] = useState(5000);
  const [sentiment, setSentiment] = useState(70);
  const [stock, setStock] = useState(50);
  const [dailySales, setDailySales] = useState(10);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<InventoryAlertResult | null>(null);
  const [error, setError] = useState(false);

  async function run() {
    if (busy) return;
    setBusy(true);
    setError(false);
    const r = await checkInventoryAlert({
      productName: name, socialMentions7d: mentions, socialSentiment: sentiment / 100,
      currentStock: stock, avgDailySales: dailySales,
    });
    setError(r === null);
    setResult(r);
    setBusy(false);
  }

  const level = result ? LEVEL[result.alert_level] : null;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <Card className="lg:col-span-7">
        <CardHeader>
          <div>
            <CardTitle>Sản phẩm + tín hiệu mạng xã hội</CardTitle>
            <p className="mt-1 text-xs text-text-muted">Kết hợp buzz mạng xã hội với tồn kho để cảnh báo sớm.</p>
          </div>
          <Badge variant="muted">social + stock</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="mono text-2xs uppercase tracking-wider text-text-dim">Tên sản phẩm</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} className="mt-1.5 h-10" />
          </div>
          <div>
            <div className="flex items-center justify-between">
              <label className="mono text-2xs uppercase tracking-wider text-text-dim">Lượt nhắc đến MXH (7 ngày)</label>
              <span className="mono text-xs text-text">{mentions.toLocaleString("vi-VN")}</span>
            </div>
            <input type="range" min={0} max={50000} step={100} value={mentions}
              onChange={(e) => setMentions(Number(e.target.value))} className="mt-1.5 w-full accent-accent" />
          </div>
          <div>
            <div className="flex items-center justify-between">
              <label className="mono text-2xs uppercase tracking-wider text-text-dim">Sentiment trung bình</label>
              <span className="mono text-xs text-text">{sentiment}%</span>
            </div>
            <input type="range" min={-100} max={100} value={sentiment}
              onChange={(e) => setSentiment(Number(e.target.value))} className="mt-1.5 w-full accent-accent" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mono text-2xs uppercase tracking-wider text-text-dim">Tồn kho hiện tại</label>
              <Input type="number" min={0} value={stock} onChange={(e) => setStock(Math.max(0, Number(e.target.value)))} className="mt-1.5 h-10" />
            </div>
            <div>
              <label className="mono text-2xs uppercase tracking-wider text-text-dim">Bán TB / ngày</label>
              <Input type="number" min={0} value={dailySales} onChange={(e) => setDailySales(Math.max(0, Number(e.target.value)))} className="mt-1.5 h-10" />
            </div>
          </div>
          <Button onClick={run} disabled={busy} className="w-full">
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <MessageSquare className="h-3.5 w-3.5" />}
            Kiểm tra cảnh báo
          </Button>
        </CardContent>
      </Card>

      <Card className="lg:col-span-5">
        <CardHeader><CardTitle>Cảnh báo</CardTitle></CardHeader>
        <CardContent>
          {error ? (
            <p className="text-sm text-danger">Không lấy được cảnh báo. Kiểm tra kết nối backend rồi thử lại.</p>
          ) : !result ? (
            <p className="text-sm text-text-muted">Bấm Kiểm tra để xem cảnh báo tồn kho.</p>
          ) : (
            <div className="space-y-4">
              <div className={cn("flex items-center gap-2 text-2xl font-semibold tracking-tight", level?.cls)}>
                {result.is_trending && <TrendingUp className="h-6 w-6" />}
                {level?.label}
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="rounded-md border border-border bg-bg-alt px-3 py-2">
                  <div className="mono text-2xs uppercase tracking-wider text-text-dim">Mức độ quan tâm</div>
                  <div className="mono mt-1 text-text">{result.trend_score}</div>
                </div>
                <div className="rounded-md border border-border bg-bg-alt px-3 py-2">
                  <div className="mono text-2xs uppercase tracking-wider text-text-dim">Còn đủ hàng</div>
                  <div className="mono mt-1 text-text">{result.days_of_stock_left} ngày</div>
                </div>
              </div>
              {result.recommended_restock_qty > 0 && (
                <div className="rounded-md border border-border bg-bg-alt px-3 py-2 text-xs text-text">
                  Đề xuất nhập thêm: <span className="mono font-semibold">{result.recommended_restock_qty}</span> sản phẩm
                </div>
              )}
              <p className="text-sm text-text-muted">{result.reason}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
