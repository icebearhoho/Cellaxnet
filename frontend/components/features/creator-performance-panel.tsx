"use client";

import { useState } from "react";
import { Loader2, Users, Plus, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { analyzeCreatorPerformance, type CreatorPerformanceResult, type CreatorItemInput, type Category } from "@/lib/features";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

const CATEGORIES: Category[] = ["Thời trang", "Mỹ phẩm", "Phụ kiện"];
const CONTENT_TYPES: CreatorItemInput["content_type"][] = ["video", "livestream", "post"];
const CONTENT_LABEL: Record<string, string> = { video: "Video", livestream: "Livestream", post: "Bài đăng" };

function vnd(n: number) {
  return n.toLocaleString("vi-VN") + "₫";
}

export function CreatorPerformancePanel() {
  const t = useT();
  const [category, setCategory] = useState<Category>("Thời trang");
  const [items, setItems] = useState<CreatorItemInput[]>([
    { creator: "Hà Linh Official", content_type: "livestream", views: 120000, engagements: 9800, attributed_sales_vnd: 45000000 },
    { creator: "Chan Review", content_type: "video", views: 85000, engagements: 6200, attributed_sales_vnd: 22000000 },
    { creator: "Mai Beauty", content_type: "post", views: 30000, engagements: 2100, attributed_sales_vnd: 7000000 },
  ]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<CreatorPerformanceResult | null>(null);
  const [error, setError] = useState(false);

  function update(i: number, patch: Partial<CreatorItemInput>) {
    setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, ...patch } : it)));
    setResult(null);
    setError(false);
  }
  function addRow() {
    setItems((prev) => [...prev, { creator: "", content_type: "video", views: 0, engagements: 0, attributed_sales_vnd: 0 }]);
    setResult(null);
    setError(false);
  }
  function removeRow(i: number) {
    setItems((prev) => prev.filter((_, idx) => idx !== i));
    setResult(null);
    setError(false);
  }

  async function run() {
    if (busy || !items.length) return;
    setBusy(true);
    setError(false);
    const r = await analyzeCreatorPerformance({ campaign_category: category, items });
    setError(r === null);
    setResult(r);
    setBusy(false);
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div>
            <CardTitle>{t("Hiệu quả KOL/KOC theo chiến dịch")}</CardTitle>
            <p className="mt-1 text-xs text-text-muted">{t("So sánh creator theo doanh số quy đổi, doanh số / 1k view và tỷ lệ tương tác.")}</p>
          </div>
          <Badge variant="muted">creator analytics</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-xs font-medium text-text-dim">{t("Danh mục chiến dịch")}</label>
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
            {items.map((it, i) => (
              <div key={i} className="rounded-md border border-border bg-bg-alt p-3">
                <div className="flex items-center gap-2">
                  <Input value={it.creator} onChange={(e) => update(i, { creator: e.target.value })}
                    placeholder={t("Tên creator")} className="h-9 flex-1" />
                  <div className="inline-flex overflow-hidden rounded-md border border-border">
                    {CONTENT_TYPES.map((t) => (
                      <button key={t} type="button" onClick={() => update(i, { content_type: t })}
                        className={cn("px-2.5 py-1.5 text-2xs font-medium transition-colors",
                          it.content_type === t ? "bg-accent/15 text-accent" : "text-text-muted hover:text-text")}>
                        {CONTENT_LABEL[t]}
                      </button>
                    ))}
                  </div>
                  <button type="button" onClick={() => removeRow(i)} className="text-text-dim hover:text-danger">
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-xs font-medium text-text-dim">Views</label>
                    <Input type="number" min={0} value={it.views} onChange={(e) => update(i, { views: Math.max(0, Number(e.target.value)) })} className="mt-1 h-9" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-text-dim">{t("Tương tác")}</label>
                    <Input type="number" min={0} value={it.engagements} onChange={(e) => update(i, { engagements: Math.max(0, Number(e.target.value)) })} className="mt-1 h-9" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-text-dim">{t("Doanh số (₫)")}</label>
                    <Input type="number" min={0} value={it.attributed_sales_vnd} onChange={(e) => update(i, { attributed_sales_vnd: Math.max(0, Number(e.target.value)) })} className="mt-1 h-9" />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" size="sm" onClick={addRow}>
              <Plus className="h-3.5 w-3.5" /> {t("Thêm creator")}
            </Button>
            <Button onClick={run} disabled={busy || !items.length}>
              {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Users className="h-3.5 w-3.5" />}
              Phân tích hiệu quả
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <p className="text-sm text-danger">{t("Không lấy được kết quả. Kiểm tra kết nối backend rồi thử lại.")}</p>
      )}

      {result && (
        <>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card>
              <CardHeader><CardTitle>{t("Định dạng tốt nhất")}</CardTitle></CardHeader>
              <CardContent>
                <div className="text-xl font-semibold text-accent">{CONTENT_LABEL[result.best_content_type] ?? result.best_content_type}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>{t("Creator nên hợp tác")}</CardTitle></CardHeader>
              <CardContent>
                <div className="text-xl font-semibold text-text">{result.recommended_creator}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>{t("Nhận định")}</CardTitle></CardHeader>
              <CardContent>
                <p className="text-sm text-text-muted">{result.insight}</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle>{t("Xếp hạng creator")}</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-2">
                {result.top_creators.map((c, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-md border border-border bg-bg-alt px-3 py-2">
                    <span className="mono flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent/15 text-2xs text-accent">{i + 1}</span>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium text-text">{c.creator}</div>
                      <div className="mono text-2xs text-text-dim">{CONTENT_LABEL[c.content_type] ?? c.content_type}</div>
                    </div>
                    <div className="text-right text-xs">
                      <div className="mono text-text">{vnd(c.total_sales_vnd)}</div>
                      <div className="mono text-2xs text-text-dim">{c.sales_per_1k_views.toLocaleString("vi-VN")}₫/1k view · {c.engagement_rate_pct}% eng</div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
