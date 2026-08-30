"use client";

import { useState } from "react";
import { Loader2, Truck, AlertTriangle, Newspaper, ExternalLink } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { checkSupplyChain, type SupplyChainResult } from "@/lib/features";
import { cn } from "@/lib/utils";

const REGIONS = ["Miền Bắc", "Miền Trung", "Miền Nam"] as const;
const CATEGORIES = ["Thời trang", "Mỹ phẩm", "Phụ kiện"] as const;

const SEVERITY: Record<string, { label: string; cls: string; badge: "success" | "warning" | "danger" }> = {
  low: { label: "Thấp", cls: "text-success", badge: "success" },
  medium: { label: "Trung bình", cls: "text-warning", badge: "warning" },
  high: { label: "Cao", cls: "text-danger", badge: "danger" },
};

export function SupplyChainPanel() {
  const [region, setRegion] = useState<(typeof REGIONS)[number]>("Miền Trung");
  const [category, setCategory] = useState<(typeof CATEGORIES)[number]>("Thời trang");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<SupplyChainResult | null>(null);
  const [error, setError] = useState(false);

  async function run() {
    if (busy) return;
    setBusy(true);
    setError(false);
    const r = await checkSupplyChain(region, category);
    setError(r === null);
    setResult(r);
    setBusy(false);
  }

  const overall = result ? SEVERITY[result.overall_risk] : null;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Khu vực &amp; danh mục</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              Cảnh báo sớm gián đoạn logistics + <span className="text-text">tin tức thật</span> (Google News) theo khu vực.
            </p>
          </div>
          <Badge variant="muted">scenario + optional news</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="text-xs font-medium text-text-dim">Khu vực kho/vận chuyển</label>
              <div className="mt-1.5 inline-flex overflow-hidden rounded-md border border-border">
                {REGIONS.map((r) => (
                  <button key={r} type="button" onClick={() => setRegion(r)}
                    className={cn("px-3 py-2 text-xs font-medium transition-colors",
                      region === r ? "bg-accent/15 text-accent" : "text-text-muted hover:text-text")}>
                    {r}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-text-dim">Danh mục hàng</label>
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
          </div>
          <Button onClick={run} disabled={busy}>
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Truck className="h-3.5 w-3.5" />}
            Kiểm tra cảnh báo
          </Button>
        </CardContent>
      </Card>

      {error && (
        <p className="text-sm text-danger">Không lấy được cảnh báo. Kiểm tra kết nối backend rồi thử lại.</p>
      )}

      {result && (
        <>
          <Card>
            <CardContent className="py-4">
              <div className={cn("text-xl font-semibold", overall?.cls)}>
                {result.scenario_mode ? "Mức rủi ro kịch bản" : "Nguy cơ tổng thể"}: {overall?.label}
              </div>
              <p className="mt-1 text-sm text-text-muted">{result.summary}</p>
            </CardContent>
          </Card>

          {result.alerts.length === 0 ? (
            <Card><CardContent className="py-6 text-center text-sm text-text-muted">Không có cảnh báo nào cho khu vực này.</CardContent></Card>
          ) : (
            <div className="space-y-3">
              {result.alerts.map((a, i) => (
                <Card key={i}>
                  <CardContent className="space-y-2 py-4">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className={cn("mt-0.5 h-4 w-4 shrink-0", SEVERITY[a.severity].cls)} />
                        <span className="text-sm font-medium text-text">{a.title}</span>
                      </div>
                      <Badge variant={SEVERITY[a.severity].badge}>{SEVERITY[a.severity].label}</Badge>
                    </div>
                    <div className="mono text-2xs text-text-dim">Dự kiến chậm thêm {a.estimated_delay_days} ngày</div>
                    <div className="rounded-md border border-border bg-bg-alt px-3 py-2 text-xs text-text-muted">
                      <span className="text-xs font-medium text-text-dim">Phương án dự phòng: </span>
                      {a.contingency}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {result.news.length > 0 && (
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Newspaper className="h-4 w-4 text-accent" />
                  <CardTitle>Tin tức liên quan</CardTitle>
                </div>
                <Badge variant={result.news_live ? "success" : "muted"}>
                  {result.news_live ? "Google News · trực tiếp" : "cache"}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-2">
                {result.news.map((n, i) => (
                  <a
                    key={i}
                    href={n.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block rounded-md border border-border bg-bg-alt px-3 py-2.5 transition-colors hover:border-accent/40"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-sm font-medium text-text">{n.title}</span>
                      <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-text-dim" />
                    </div>
                    {n.snippet && <p className="mt-1 line-clamp-2 text-xs text-text-muted">{n.snippet}</p>}
                    <div className="mono mt-1.5 text-2xs text-text-dim">
                      {n.source}{n.date ? ` · ${n.date}` : ""}
                    </div>
                  </a>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
