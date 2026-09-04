"use client";

import { useState } from "react";
import { Loader2, Swords } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { analyzeMarketIntelligence, type MarketIntelligenceResult, type Category } from "@/lib/features";
import { CompetitorWatch } from "@/components/features/competitor-watch";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

const CATEGORIES: Category[] = ["Thời trang", "Mỹ phẩm", "Phụ kiện"];

const POSITION: Record<string, { label: string; cls: string }> = {
  cheaper: { label: "Rẻ hơn đối thủ", cls: "text-success" },
  parity: { label: "Ngang giá", cls: "text-warning" },
  pricier: { label: "Đắt hơn đối thủ", cls: "text-danger" },
};

const ACTION: Record<string, string> = {
  hold: "Giữ nguyên giá",
  match_price: "Bám sát giá đối thủ",
  undercut: "Hạ giá thấp hơn",
  differentiate: "Khác biệt hoá, không đua giá",
  protect_margin: "Tăng về giá sàn để bảo vệ lợi nhuận",
};

function vnd(n: number) {
  return n.toLocaleString("vi-VN") + "₫";
}

export function MarketIntelligencePanel() {
  const t = useT();
  const [ourProduct, setOurProduct] = useState("Kem chống nắng SPF50 50ml");
  const [category, setCategory] = useState<Category>("Mỹ phẩm");
  const [ourPrice, setOurPrice] = useState(189000);
  const [ourCost, setOurCost] = useState(90000);
  const [competitorName, setCompetitorName] = useState("Shop Beauty Zone");
  const [competitorPrice, setCompetitorPrice] = useState(210000);
  const [competitorDiscount, setCompetitorDiscount] = useState(15);
  const [minMargin, setMinMargin] = useState(20);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<MarketIntelligenceResult | null>(null);
  const [error, setError] = useState(false);

  async function run() {
    if (busy) return;
    setBusy(true);
    setError(false);
    const r = await analyzeMarketIntelligence({
      our_product: ourProduct,
      category,
      our_price_vnd: ourPrice,
      our_cost_vnd: ourCost,
      competitor_name: competitorName,
      competitor_price_vnd: competitorPrice,
      competitor_discount_pct: competitorDiscount,
      min_margin_pct: minMargin,
    });
    setError(r === null);
    setResult(r);
    setBusy(false);
  }

  const pos = result ? POSITION[result.position] : null;

  return (
    <div className="space-y-6">
      {/* Ongoing competitor tracking from a pasted shop URL. */}
      <CompetitorWatch />

      {/* One-shot pricing response calculator (the original feature). */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <Card className="lg:col-span-7">
        <CardHeader>
          <div>
            <CardTitle>{t("Sản phẩm của bạn & đối thủ")}</CardTitle>
            <p className="mt-1 text-xs text-text-muted">{t("So sánh giá với đối thủ và đề xuất mức giá tối ưu, không phá sàn lợi nhuận.")}</p>
          </div>
          <Badge variant="muted">competitive pricing</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-xs font-medium text-text-dim">{t("Sản phẩm của bạn")}</label>
            <Input value={ourProduct} onChange={(e) => setOurProduct(e.target.value)} className="mt-1.5 h-10" />
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
              <label className="text-xs font-medium text-text-dim">{t("Giá bán của bạn (₫)")}</label>
              <Input type="number" min={0} value={ourPrice} onChange={(e) => setOurPrice(Math.max(0, Number(e.target.value)))} className="mt-1.5 h-10" />
            </div>
            <div>
              <label className="text-xs font-medium text-text-dim">{t("Giá vốn (₫)")}</label>
              <Input type="number" min={0} value={ourCost} onChange={(e) => setOurCost(Math.max(0, Number(e.target.value)))} className="mt-1.5 h-10" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-text-dim">{t("Tên đối thủ")}</label>
            <Input value={competitorName} onChange={(e) => setCompetitorName(e.target.value)} className="mt-1.5 h-10" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-text-dim">{t("Giá đối thủ (₫)")}</label>
              <Input type="number" min={0} value={competitorPrice} onChange={(e) => setCompetitorPrice(Math.max(0, Number(e.target.value)))} className="mt-1.5 h-10" />
            </div>
            <div>
              <label className="text-xs font-medium text-text-dim">{t("Giảm giá (%)")}</label>
              <Input type="number" min={0} value={competitorDiscount} onChange={(e) => setCompetitorDiscount(Math.max(0, Number(e.target.value)))} className="mt-1.5 h-10" />
            </div>
            <div>
              <label className="text-xs font-medium text-text-dim">{t("Biên tối thiểu (%)")}</label>
              <Input type="number" min={0} value={minMargin} onChange={(e) => setMinMargin(Math.max(0, Number(e.target.value)))} className="mt-1.5 h-10" />
            </div>
          </div>
          <Button onClick={run} disabled={busy} className="w-full">
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Swords className="h-3.5 w-3.5" />}
            Phân tích đối thủ
          </Button>
        </CardContent>
      </Card>

      <Card className="lg:col-span-5">
        <CardHeader><CardTitle>{t("Đề xuất")}</CardTitle></CardHeader>
        <CardContent>
          {error ? (
            <p className="text-sm text-danger">{t("Không lấy được kết quả. Kiểm tra kết nối backend rồi thử lại.")}</p>
          ) : !result ? (
            <p className="text-sm text-text-muted">{t("Bấm Phân tích để so sánh giá với đối thủ.")}</p>
          ) : (
            <div className="space-y-4">
              <div className={cn("text-xl font-semibold tracking-tight", pos?.cls)}>{pos?.label}</div>
              <div className="rounded-md border border-accent/40 bg-accent/10 px-3 py-3">
                <div className="text-xs font-medium text-text-dim">{t("Hành động đề xuất")}</div>
                <div className="mt-1 text-sm font-medium text-text">{ACTION[result.recommended_action] ?? result.recommended_action}</div>
                <div className="mono mt-2 text-2xl font-semibold text-accent">{vnd(result.recommended_price_vnd)}</div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="rounded-md border border-border bg-bg-alt px-3 py-2">
                  <div className="text-xs font-medium text-text-dim">{t("Giá sàn")}</div>
                  <div className="mono mt-1 text-text">{vnd(result.price_floor_vnd)}</div>
                </div>
                <div className="rounded-md border border-border bg-bg-alt px-3 py-2">
                  <div className="text-xs font-medium text-text-dim">{t("Biên tại giá đề xuất")}</div>
                  <div className="mono mt-1 text-text">{result.margin_pct_at_recommended}%</div>
                </div>
                <div className="col-span-2 rounded-md border border-border bg-bg-alt px-3 py-2">
                  <div className="text-xs font-medium text-text-dim">{t("Giá thực tế của đối thủ")}</div>
                  <div className="mono mt-1 text-text">{vnd(result.competitor_effective_price_vnd)}</div>
                </div>
              </div>
              <p className="text-sm text-text-muted">{result.reasoning}</p>
            </div>
          )}
        </CardContent>
      </Card>
      </div>
    </div>
  );
}
