"use client";

import { useState } from "react";
import { Loader2, Lightbulb, Plus, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { analyzeDecisionIntelligence, type DecisionIntelligenceResult, type DecisionInput, type Category } from "@/lib/features";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

const CATEGORIES: Category[] = ["Thời trang", "Mỹ phẩm", "Phụ kiện"];
const KINDS: DecisionInput["kind"][] = ["price", "promo", "ad", "inventory"];
const KIND_LABEL: Record<string, string> = { price: "Giá", promo: "Khuyến mãi", ad: "Quảng cáo", inventory: "Tồn kho" };
const METRICS: DecisionInput["metric"][] = ["ROAS", "sales_lift_pct", "margin_pct", "sell_through_pct"];
const METRIC_LABEL: Record<string, string> = {
  ROAS: "ROAS",
  sales_lift_pct: "Tăng doanh số (%)",
  margin_pct: "Biên lợi nhuận (%)",
  sell_through_pct: "Tỷ lệ bán hết (%)",
};

export function DecisionIntelligencePanel() {
  const t = useT();
  const [situation, setSituation] = useState(t("Chuẩn bị chiến dịch cho mùa cao điểm quý 4"));
  const [category, setCategory] = useState<Category>("Thời trang");
  const [decisions, setDecisions] = useState<DecisionInput[]>([
    { kind: "ad", description: t("Chạy ads TikTok tháng 11"), metric: "ROAS", value: 4.2, month: 11 },
    { kind: "promo", description: "Flash sale 12.12", metric: "sales_lift_pct", value: 65, month: 12 },
    { kind: "price", description: t("Giảm giá 10% dòng bán chậm"), metric: "sell_through_pct", value: 48, month: null },
  ]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<DecisionIntelligenceResult | null>(null);
  const [error, setError] = useState(false);

  function update(i: number, patch: Partial<DecisionInput>) {
    setDecisions((prev) => prev.map((d, idx) => (idx === i ? { ...d, ...patch } : d)));
    setResult(null);
    setError(false);
  }
  function addRow() {
    setDecisions((prev) => [...prev, { kind: "price", description: "", metric: "ROAS", value: 0, month: null }]);
    setResult(null);
    setError(false);
  }
  function removeRow(i: number) {
    setDecisions((prev) => prev.filter((_, idx) => idx !== i));
    setResult(null);
    setError(false);
  }

  async function run() {
    if (busy || !decisions.length) return;
    setBusy(true);
    setError(false);
    const r = await analyzeDecisionIntelligence({ situation, category, decisions });
    setError(r === null);
    setResult(r);
    setBusy(false);
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div>
            <CardTitle>{t("Học từ quyết định quá khứ")}</CardTitle>
            <p className="mt-1 text-xs text-text-muted">{t("Đối chiếu các quyết định đã thực hiện để rút ra hành động nên lặp lại.")}</p>
          </div>
          <Badge variant="muted">decision log</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-xs font-medium text-text-dim">{t("Bối cảnh")}</label>
            <Input value={situation} onChange={(e) => setSituation(e.target.value)} className="mt-1.5 h-10" />
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

          <div className="space-y-3">
            {decisions.map((d, i) => (
              <div key={i} className="rounded-md border border-border bg-bg-alt p-3">
                <div className="flex items-center gap-2">
                  <div className="inline-flex overflow-hidden rounded-md border border-border">
                    {KINDS.map((k) => (
                      <button key={k} type="button" onClick={() => update(i, { kind: k })}
                        className={cn("px-2.5 py-1.5 text-2xs font-medium transition-colors",
                          d.kind === k ? "bg-accent/15 text-accent" : "text-text-muted hover:text-text")}>
                        {KIND_LABEL[k]}
                      </button>
                    ))}
                  </div>
                  <button type="button" onClick={() => removeRow(i)} className="ml-auto text-text-dim hover:text-danger">
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <Input value={d.description} onChange={(e) => update(i, { description: e.target.value })}
                  placeholder={t("Mô tả quyết định")} className="mt-2 h-9" />
                <div className="mt-2 grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-xs font-medium text-text-dim">{t("Chỉ số")}</label>
                    <select value={d.metric} onChange={(e) => update(i, { metric: e.target.value as DecisionInput["metric"] })}
                      className="mt-1 h-9 w-full rounded-md border border-border bg-surface px-2 text-xs text-text">
                      {METRICS.map((m) => <option key={m} value={m}>{METRIC_LABEL[m]}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-text-dim">{t("Giá trị")}</label>
                    <Input type="number" min={0} value={d.value} onChange={(e) => update(i, { value: Math.max(0, Number(e.target.value)) })} className="mt-1 h-9" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-text-dim">{t("Tháng (nếu ads)")}</label>
                    <Input type="number" min={0} value={d.month ?? ""} placeholder="—"
                      onChange={(e) => update(i, { month: e.target.value === "" ? null : Math.max(0, Number(e.target.value)) })}
                      className="mt-1 h-9" />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" size="sm" onClick={addRow}>
              <Plus className="h-3.5 w-3.5" /> {t("Thêm quyết định")}
            </Button>
            <Button onClick={run} disabled={busy || !decisions.length}>
              {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Lightbulb className="h-3.5 w-3.5" />}
              Rút bài học
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <p className="text-sm text-danger">{t("Không lấy được kết quả. Kiểm tra kết nối backend rồi thử lại.")}</p>
      )}

      {result && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader><CardTitle>{t("Quyết định tốt nhất")}</CardTitle></CardHeader>
            <CardContent>
              <Badge variant="live">{KIND_LABEL[result.best_decision.kind] ?? result.best_decision.kind}</Badge>
              <div className="mt-2 text-sm font-medium text-text">{result.best_decision.description}</div>
              <div className="mono mt-2 text-lg font-semibold text-accent">
                {METRIC_LABEL[result.best_decision.metric] ?? result.best_decision.metric}: {result.best_decision.value}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>{t("Tháng chạy ads tốt nhất")}</CardTitle></CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold text-text">
                {result.best_ad_month != null ? `Tháng ${result.best_ad_month}` : t("Chưa xác định")}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>{t("Hành động đề xuất")}</CardTitle></CardHeader>
            <CardContent>
              <p className="text-sm font-medium text-text">{result.recommended_action}</p>
            </CardContent>
          </Card>
          <Card className="lg:col-span-3">
            <CardHeader><CardTitle>{t("Lý giải")}</CardTitle></CardHeader>
            <CardContent>
              <p className="text-sm text-text-muted">{result.reasoning}</p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
