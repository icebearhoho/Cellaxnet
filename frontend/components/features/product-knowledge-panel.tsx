"use client";

import { useState } from "react";
import { Loader2, Brain, ArrowUp, ArrowDown, Minus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { analyzeProductKnowledge, type ProductKnowledgeResult, type Category } from "@/lib/features";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

const CATEGORIES: Category[] = ["Thời trang", "Mỹ phẩm", "Phụ kiện"];
const STOCKS = [
  { v: "ok", label: "Đủ hàng" },
  { v: "low", label: "Sắp hết" },
  { v: "out", label: "Hết hàng" },
] as const;

const DIRECTION: Record<string, { label: string; cls: string; icon: typeof ArrowUp }> = {
  up: { label: "Tăng", cls: "text-success", icon: ArrowUp },
  down: { label: "Giảm", cls: "text-danger", icon: ArrowDown },
  flat: { label: "Đi ngang", cls: "text-text-muted", icon: Minus },
};

const IMPACT: Record<string, string> = { low: "Thấp", medium: "Trung bình", high: "Cao" };

export function ProductKnowledgePanel() {
  const t = useT();
  const [product, setProduct] = useState("Áo thun cotton unisex form rộng");
  const [category, setCategory] = useState<Category>("Thời trang");
  const [salesPrev, setSalesPrev] = useState(1200);
  const [salesCurr, setSalesCurr] = useState(1800);
  const [priceChange, setPriceChange] = useState(-10);
  const [trafficChange, setTrafficChange] = useState(25);
  const [promoActive, setPromoActive] = useState(true);
  const [competitorPromo, setCompetitorPromo] = useState(false);
  const [stockStatus, setStockStatus] = useState<"ok" | "low" | "out">("ok");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ProductKnowledgeResult | null>(null);
  const [error, setError] = useState(false);

  async function run() {
    if (busy) return;
    setBusy(true);
    setError(false);
    const r = await analyzeProductKnowledge({
      product,
      category,
      sales_prev: salesPrev,
      sales_curr: salesCurr,
      price_change_pct: priceChange,
      promotion_active: promoActive,
      competitor_promo: competitorPromo,
      stock_status: stockStatus,
      traffic_change_pct: trafficChange,
    });
    setError(r === null);
    setResult(r);
    setBusy(false);
  }

  const dir = result ? DIRECTION[result.direction] : null;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <Card className="lg:col-span-7">
        <CardHeader>
          <div>
            <CardTitle>{t("Sản phẩm & tín hiệu doanh số")}</CardTitle>
            <p className="mt-1 text-xs text-text-muted">{t("Giải thích vì sao doanh số thay đổi giữa hai kỳ.")}</p>
          </div>
          <Badge variant="muted">{t("Phân tích nguyên nhân")}</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-xs font-medium text-text-dim">{t("Tên sản phẩm")}</label>
            <Input value={product} onChange={(e) => setProduct(e.target.value)} className="mt-1.5 h-10" />
          </div>
          <div>
            <label className="text-xs font-medium text-text-dim">{t("Danh mục")}</label>
            <div className="mt-1.5 inline-flex overflow-hidden rounded-md border border-border">
              {CATEGORIES.map((c) => (
                <button key={c} type="button" onClick={() => setCategory(c)}
                  className={cn("px-3 py-2 text-xs font-medium transition-colors",
                    category === c ? "bg-accent/15 text-accent" : "text-text-muted hover:text-text")}>
                  {c}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-text-dim">{t("Doanh số kỳ trước")}</label>
              <Input type="number" min={0} value={salesPrev} onChange={(e) => setSalesPrev(Math.max(0, Number(e.target.value)))} className="mt-1.5 h-10" />
            </div>
            <div>
              <label className="text-xs font-medium text-text-dim">{t("Doanh số kỳ này")}</label>
              <Input type="number" min={0} value={salesCurr} onChange={(e) => setSalesCurr(Math.max(0, Number(e.target.value)))} className="mt-1.5 h-10" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-text-dim">{t("Thay đổi giá (%)")}</label>
              <Input type="number" value={priceChange} onChange={(e) => setPriceChange(Number(e.target.value))} className="mt-1.5 h-10" />
            </div>
            <div>
              <label className="text-xs font-medium text-text-dim">{t("Thay đổi traffic (%)")}</label>
              <Input type="number" value={trafficChange} onChange={(e) => setTrafficChange(Number(e.target.value))} className="mt-1.5 h-10" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-text-dim">{t("Tồn kho")}</label>
            <div className="mt-1.5 inline-flex overflow-hidden rounded-md border border-border">
              {STOCKS.map((s) => (
                <button key={s.v} type="button" onClick={() => setStockStatus(s.v)}
                  className={cn("px-3 py-2 text-xs font-medium transition-colors",
                    stockStatus === s.v ? "bg-accent/15 text-accent" : "text-text-muted hover:text-text")}>
                  {s.label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => setPromoActive((v) => !v)}
              className={cn("rounded-md border px-3 py-2 text-xs font-medium transition-colors",
                promoActive ? "border-accent bg-accent/15 text-accent" : "border-border text-text-muted hover:text-text")}>
              {t("Đang có khuyến mãi")}
            </button>
            <button type="button" onClick={() => setCompetitorPromo((v) => !v)}
              className={cn("rounded-md border px-3 py-2 text-xs font-medium transition-colors",
                competitorPromo ? "border-accent bg-accent/15 text-accent" : "border-border text-text-muted hover:text-text")}>
              {t("Đối thủ đang khuyến mãi")}
            </button>
          </div>
          <Button onClick={run} disabled={busy} className="w-full">
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Brain className="h-3.5 w-3.5" />}
            Phân tích doanh số
          </Button>
        </CardContent>
      </Card>

      <Card className="lg:col-span-5">
        <CardHeader><CardTitle>{t("Kết quả")}</CardTitle></CardHeader>
        <CardContent>
          {error ? (
            <p className="text-sm text-danger">{t("Không lấy được kết quả. Kiểm tra kết nối backend rồi thử lại.")}</p>
          ) : !result ? (
            <p className="text-sm text-text-muted">{t("Bấm Phân tích để xem vì sao doanh số thay đổi.")}</p>
          ) : (
            <div className="space-y-4">
              <div className={cn("flex items-center gap-2 text-2xl font-semibold tracking-tight", dir?.cls)}>
                {dir && <dir.icon className="h-6 w-6" />}
                {dir?.label} {result.sales_change_pct > 0 ? "+" : ""}{result.sales_change_pct}%
              </div>
              <div>
                <div className="text-xs font-medium text-text-dim">{t("Yếu tố tác động")}</div>
                <div className="mt-2 space-y-2">
                  {result.drivers.map((d, i) => {
                    const dd = DIRECTION[d.direction];
                    return (
                      <div key={i} className="flex items-center justify-between gap-2 rounded-md border border-border bg-bg-alt px-3 py-2 text-xs">
                        <span className={cn("flex items-center gap-1.5", dd.cls)}>
                          <dd.icon className="h-3.5 w-3.5" />
                          <span className="text-text">{d.factor}</span>
                        </span>
                        <Badge variant={d.impact === "high" ? "danger" : d.impact === "medium" ? "warning" : "muted"}>
                          {IMPACT[d.impact]}
                        </Badge>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="rounded-md border border-border bg-bg-alt px-3 py-2 text-xs text-text-muted">
                <span className="text-xs font-medium text-text-dim">{t("Hiệu quả khuyến mãi:")} </span>
                {result.promotion_effectiveness}
              </div>
              <p className="text-sm text-text-muted">{result.explanation}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
