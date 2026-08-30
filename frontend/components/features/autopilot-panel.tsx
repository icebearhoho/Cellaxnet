"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight, Bot, Check, CircleAlert, FlaskConical,
  RefreshCw, ShieldCheck, Target, X,
} from "lucide-react";
import { api, ApiClientError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Option = { id: string; label: string; risk: string; impact: Record<string, number> };
type Opportunity = {
  id: number; kind: string; severity: string; status: string; title: string;
  explanation: string; evidence: Record<string, string | number>; options: Option[];
  model: string | null; llm_used: boolean; selected_option_id: string | null;
};

const money = (value: number) => `${new Intl.NumberFormat("vi-VN").format(value)}₫`;
const labelMap: Record<string, string> = {
  inventory: "Tồn kho", reviews: "Trải nghiệm khách hàng", customer_risk: "Giữ chân khách",
  detected: "Cần xem", simulated: "Đã mô phỏng", applied: "Đã duyệt", rejected: "Đã bỏ",
};
const evidenceLabels: Record<string, string> = {
  product_name: "Sản phẩm", runway_days: "Số ngày còn hàng", revenue_at_risk_vnd: "Doanh thu có rủi ro",
  negative_reviews_30d: "Review thấp / 30 ngày", customers_at_risk: "Khách cần giữ chân",
  ltv_at_risk_vnd: "LTV có rủi ro", stock: "Tồn hiện tại", daily_sales: "Bán/ngày",
};
const impactLabels: Record<string, string> = {
  revenue_protected_vnd: "Doanh thu được bảo vệ",
  wasted_spend_avoided_vnd: "Chi phí lãng phí tránh được",
  runway_days: "Số ngày tồn kho sau xử lý",
  campaigns_to_review: "Campaign cần rà soát",
  reviews_prioritized: "Review được ưu tiên",
  response_sla_hours: "SLA phản hồi (giờ)",
  customers_targeted: "Khách được nhắm tới",
  expected_reactivation_pct: "Tỷ lệ tái kích hoạt dự kiến (%)",
};
const riskLabels: Record<string, string> = { low: "thấp", medium: "vừa", high: "cao" };
const showValue = (key: string, value: string | number) =>
  key.endsWith("_vnd") && typeof value === "number" ? money(value) : String(value);

export function AutopilotPanel() {
  const [items, setItems] = useState<Opportunity[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      const response = await api.get<Opportunity[]>("/autopilot/opportunities");
      setItems(response.data ?? []);
    } catch (cause) {
      setError(cause instanceof ApiClientError ? cause.message : "Hãy chọn workspace đang hoạt động.");
    }
  };
  useEffect(() => { void load(); }, []);

  const refresh = async () => {
    setBusy("refresh"); setError(null);
    try {
      const response = await api.post<Opportunity[]>("/autopilot/refresh", {});
      setItems(response.data ?? []);
    } catch (cause) {
      setError(cause instanceof ApiClientError ? cause.message : "Không thể phân tích dữ liệu vận hành.");
    } finally { setBusy(null); }
  };

  const act = async (item: Opportunity, option: Option, decision?: "approve" | "reject") => {
    const key = `${item.id}:${option.id}:${decision ?? "simulate"}`;
    setBusy(key); setError(null);
    try {
      const path = decision ? "decision" : "simulate";
      const body = decision ? { option_id: option.id, decision } : { option_id: option.id };
      const response = await api.post<{ opportunity: Opportunity }>(
        `/autopilot/opportunities/${item.id}/${path}`, body,
      );
      if (response.data) setItems((rows) => rows.map((row) =>
        row.id === item.id ? response.data!.opportunity : row));
    } catch (cause) {
      setError(cause instanceof ApiClientError ? cause.message : "Hành động không hợp lệ.");
    } finally { setBusy(null); }
  };

  const active = items.filter((item) => !["applied", "rejected"].includes(item.status));
  const completed = items.length - active.length;

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden border-accent/30">
        <CardContent className="grid gap-5 p-5 lg:grid-cols-[1fr_auto] lg:items-center">
          <div className="flex gap-3">
            <span className="doodle-sticker h-11 w-11 shrink-0"><Bot className="h-5 w-5" /></span>
            <div>
              <div className="text-sm font-semibold text-accent-deep">Commerce Digital Twin</div>
              <h2 className="mt-1 text-2xl">Từ tín hiệu thành một quyết định có thể thực thi</h2>
              <p className="mt-2 max-w-2xl text-sm text-text-muted">
                Các module phân tích chạy phía sau để cung cấp bằng chứng. Màn hình này chỉ giữ lại vấn đề cần quyết định, tác động và hành động tiếp theo.
              </p>
            </div>
          </div>
          <Button onClick={refresh} disabled={busy !== null}>
            <RefreshCw className={`h-4 w-4 ${busy === "refresh" ? "animate-spin" : ""}`} />
            {busy === "refresh" ? "Đang dựng snapshot…" : "Cập nhật Digital Twin"}
          </Button>
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-3">
        <Stage icon={Target} number="01" title="Phát hiện" detail={`${active.length} việc cần quyết định`} active />
        <Stage icon={FlaskConical} number="02" title="Mô phỏng" detail="So sánh tác động trước khi duyệt" />
        <Stage icon={ShieldCheck} number="03" title="Thực thi" detail={`${completed} quyết định đã ghi nhận`} />
      </div>

      {error && <div className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger">{error}</div>}
      {!items.length && !error && (
        <Card><CardContent className="p-10 text-center">
          <Target className="mx-auto h-8 w-8 text-accent" />
          <h3 className="mt-3 text-lg">Chưa có snapshot quyết định</h3>
          <p className="mt-1 text-sm text-text-muted">Cập nhật Digital Twin để đọc tồn kho, khách hàng và review từ cùng một snapshot.</p>
        </CardContent></Card>
      )}

      <div className="space-y-4">
        {active.map((item) => {
          const selected = item.options.find((option) => option.id === item.selected_option_id) ?? item.options[0];
          const terminal = ["applied", "rejected"].includes(item.status);
          const evidence = Object.entries(item.evidence).filter(([key]) => evidenceLabels[key]).slice(0, 4);
          return (
            <Card key={item.id} className={item.severity === "critical" ? "border-danger/40" : ""}>
              <CardHeader className="border-b border-border">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={item.severity === "critical" ? "danger" : "warning"}>{labelMap[item.kind] ?? item.kind}</Badge>
                      <Badge variant="muted">{labelMap[item.status] ?? item.status}</Badge>
                    </div>
                    <CardTitle className="mt-3">{item.title}</CardTitle>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-text-muted">{item.explanation}</p>
                  </div>
                  {item.llm_used && <span className="text-xs text-text-dim">Ollama giải thích · số liệu do rule tính</span>}
                </div>
              </CardHeader>
              <CardContent className="grid gap-5 p-5 lg:grid-cols-[.8fr_1.2fr]">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-text-dim">Bằng chứng đủ để quyết định</div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
                    {evidence.map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between gap-4 border-b border-dashed border-border pb-2 text-sm">
                        <span className="text-text-muted">{evidenceLabels[key]}</span>
                        <b>{showValue(key, value)}</b>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded-md border-2 border-text/70 bg-surface p-4 shadow-[3px_4px_0_hsl(var(--text)/.1)]">
                  <div className="flex items-start justify-between gap-3">
                    <div><div className="text-xs font-semibold text-accent-deep">HÀNH ĐỘNG ĐỀ XUẤT</div><div className="mt-1 font-semibold">{selected.label}</div></div>
                    <Badge variant={selected.risk === "low" ? "success" : "warning"}>Rủi ro {riskLabels[selected.risk] ?? selected.risk}</Badge>
                  </div>
                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    {Object.entries(selected.impact).slice(0, 4).map(([key, value]) => (
                      <div key={key} className="rounded-md bg-surface-2 p-2.5 text-xs text-text-muted">
                        {impactLabels[key] ?? key.replaceAll("_", " ")}<div className="mono mt-1 font-bold text-text">{showValue(key, value)}</div>
                      </div>
                    ))}
                  </div>
                  {!terminal && <div className="mt-4 flex flex-wrap gap-2">
                    {item.status !== "simulated" ? (
                      <Button size="sm" variant="secondary" disabled={busy !== null} onClick={() => act(item, selected)}>
                        <FlaskConical className="h-3.5 w-3.5" /> Mô phỏng tác động
                      </Button>
                    ) : (
                      <Button size="sm" disabled={busy !== null} onClick={() => act(item, selected, "approve")}>
                        <Check className="h-3.5 w-3.5" /> Duyệt hành động
                      </Button>
                    )}
                    <Button size="sm" variant="ghost" disabled={busy !== null} onClick={() => act(item, selected, "reject")}>
                      <X className="h-3.5 w-3.5" /> Bỏ qua
                    </Button>
                    {item.kind === "customer_risk" && (
                      <Button asChild size="sm" variant="ghost"><Link href="/seller/voucher-booster">Mở Voucher Booster <ArrowRight className="h-3.5 w-3.5" /></Link></Button>
                    )}
                  </div>}
                  {item.options.length > 1 && !terminal && (
                    <details className="mt-4 border-t border-border pt-3 text-xs text-text-muted">
                      <summary className="cursor-pointer">Xem {item.options.length - 1} phương án khác</summary>
                      <div className="mt-2 space-y-1">
                        {item.options.filter((option) => option.id !== selected.id).map((option) => (
                          <button key={option.id} type="button" onClick={() => act(item, option)}
                            className="block w-full rounded-md border border-border px-3 py-2 text-left hover:border-accent hover:text-text">
                            {option.label}
                          </button>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {completed > 0 && (
        <details className="rounded-lg border border-border bg-surface p-4">
          <summary className="cursor-pointer text-sm font-semibold">
            Lịch sử quyết định ({completed})
          </summary>
          <div className="mt-3 divide-y divide-border">
            {items.filter((item) => ["applied", "rejected"].includes(item.status)).map((item) => (
              <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
                <span>{item.title}</span>
                <Badge variant={item.status === "applied" ? "success" : "muted"}>
                  {labelMap[item.status] ?? item.status}
                </Badge>
              </div>
            ))}
          </div>
        </details>
      )}

      <div className="flex items-start gap-2 rounded-md border border-warning/30 bg-warning/10 p-3 text-xs text-text-muted">
        <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
        Digital Twin chỉ dùng dữ liệu có nguồn trong snapshot. LLM được phép giải thích, không được tự tạo chỉ số hoặc vượt qua bước seller duyệt.
      </div>
    </div>
  );
}

function Stage({ icon: Icon, number, title, detail, active = false }: {
  icon: typeof Target; number: string; title: string; detail: string; active?: boolean;
}) {
  return <div className={`rounded-lg border p-4 ${active ? "border-accent/40 bg-accent/10" : "border-border bg-surface"}`}>
    <div className="flex items-center gap-2"><Icon className="h-4 w-4 text-accent" /><span className="mono text-xs text-text-dim">{number}</span><b>{title}</b></div>
    <p className="mt-2 text-xs text-text-muted">{detail}</p>
  </div>;
}
