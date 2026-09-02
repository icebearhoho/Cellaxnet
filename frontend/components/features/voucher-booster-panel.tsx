"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight, BadgePercent, Check, CircleAlert, ExternalLink,
  Loader2, ShieldCheck, Store, X,
} from "lucide-react";
import { api, ApiClientError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type CheckRule = { code: string; passed: boolean; message: string };
type Recommendation = {
  id: string; why: string;
  plan: {
    name: string; platform: "shopee" | "tiktok_shop";
    promotion_type: string; objective: string; discount_value: number;
    quantity: number; budget_vnd: number; starts_at: string; ends_at: string;
  };
  baseline: Record<string, string | number>;
  simulation: Record<string, number>;
  guardrails: { passed: boolean; checks: CheckRule[]; violations: string[] };
};
type Campaign = {
  id: number; name: string; platform: "shopee" | "tiktok_shop";
  promotion_type: string; status: string; objective: string;
  discount_value: number; quantity: number; budget_vnd: number;
  baseline: Record<string, string | number>; simulation: Record<string, number>;
  guardrails: { passed: boolean; checks: CheckRule[]; violations: string[] };
  execution: { mode: string; can_publish: boolean; message: string; seller_center_url: string };
};

const money = (value: number) => `${new Intl.NumberFormat("vi-VN").format(value)}₫`;
const platformName = (platform: string) => platform === "shopee" ? "Shopee" : "TikTok Shop";
const statusText: Record<string, string> = {
  simulated: "Đã mô phỏng", ready_to_publish: "Sẵn sàng kết nối",
  needs_connection: "Cần kết nối shop", needs_manual_action: "Cần xác nhận trên sàn",
  rejected: "Đã từ chối", stopped: "Đã dừng", published: "Đang chạy",
};

export function VoucherBoosterPanel() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [recs, rows] = await Promise.all([
        api.get<Recommendation[]>("/voucher-booster/recommendations"),
        api.get<Campaign[]>("/voucher-booster/campaigns"),
      ]);
      setRecommendations(recs.data ?? []);
      setCampaigns(rows.data ?? []);
    } catch (cause) {
      setError(cause instanceof ApiClientError
        ? cause.message : "Không thể tải Voucher Booster. Hãy kiểm tra workspace và backend.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { void load(); }, []);

  const create = async (id: string) => {
    setBusy(`create:${id}`); setError(null);
    try {
      const response = await api.post<Campaign>("/voucher-booster/campaigns/from-recommendation", {
        recommendation_id: id,
      });
      if (response.data) setCampaigns((current) => current.some((row) => row.id === response.data!.id)
        ? current : [response.data!, ...current]);
    } catch (cause) {
      setError(cause instanceof ApiClientError ? cause.message : "Không thể lập campaign.");
    } finally { setBusy(null); }
  };

  const decide = async (campaign: Campaign, decision: "approve" | "reject") => {
    setBusy(`${decision}:${campaign.id}`); setError(null);
    try {
      const response = await api.post<Campaign>(
        `/voucher-booster/campaigns/${campaign.id}/decision`, { decision },
      );
      if (response.data) setCampaigns((rows) => rows.map((row) =>
        row.id === campaign.id ? response.data! : row));
    } catch (cause) {
      setError(cause instanceof ApiClientError ? cause.message : "Không thể duyệt campaign.");
    } finally { setBusy(null); }
  };

  const top = recommendations.find((item) => item.guardrails.passed) ?? recommendations[0];

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden border-accent/30">
        <CardContent className="grid gap-5 p-5 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-accent-deep">
              <BadgePercent className="h-4 w-4" /> Voucher Booster
            </div>
            <h2 className="mt-2 text-2xl">Một quyết định, có rule trước khi lên sàn</h2>
            <p className="mt-2 max-w-2xl text-sm text-text-muted">
              Dữ liệu tồn kho và biên lợi nhuận tạo kịch bản. Seller duyệt ngân sách, sau đó hệ thống mới chuyển sang bước kết nối hoặc xác nhận trên Seller Center.
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <span className="rounded-md border px-2.5 py-2">1 · Mô phỏng</span>
            <ArrowRight className="h-3.5 w-3.5" />
            <span className="rounded-md border px-2.5 py-2">2 · Duyệt rule</span>
            <ArrowRight className="h-3.5 w-3.5" />
            <span className="rounded-md border px-2.5 py-2">3 · Lên sàn</span>
          </div>
        </CardContent>
      </Card>

      {error && <div className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger">{error}</div>}

      {loading && !top && (
        <Card>
          <CardContent className="flex items-center gap-3 p-6 text-sm text-text-muted">
            <Loader2 className="h-4 w-4 animate-spin" />
            Đang đọc tồn kho, biên lợi nhuận và chuẩn bị kịch bản an toàn…
          </CardContent>
        </Card>
      )}

      {!loading && !error && !top && (
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-sm font-medium">Chưa tạo được kịch bản từ snapshot hiện tại.</p>
            <p className="mt-1 text-xs text-text-muted">Hãy cập nhật dữ liệu vận hành rồi thử phân tích lại.</p>
            <Button className="mt-4" variant="secondary" onClick={() => void load()}>
              Phân tích lại
            </Button>
          </CardContent>
        </Card>
      )}

      {top && (
        <Card className="border-accent/40 shadow-[5px_6px_0_hsl(var(--accent)/.14)]">
          <CardHeader className="border-b border-border">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-accent-deep">Kịch bản nên chạy</div>
                <CardTitle className="mt-1">{top.plan.name}</CardTitle>
                <p className="mt-2 max-w-3xl text-sm text-text-muted">{top.why}</p>
              </div>
              <Badge variant={top.guardrails.passed ? "success" : "danger"}>
                {top.guardrails.passed ? "Qua toàn bộ rule" : "Chưa an toàn"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-5">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Metric label="Mức giảm" value={`${top.simulation.discount_pct}%`} />
              <Metric label="Đơn dự kiến" value={`${top.simulation.expected_orders}`} />
              <Metric label="Doanh thu dự kiến" value={money(top.simulation.expected_revenue_vnd)} />
              <Metric label="Lợi nhuận tăng thêm" value={money(top.simulation.incremental_profit_vnd)}
                good={top.simulation.incremental_profit_vnd >= 0} />
            </div>
            <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
              <div>
                <div className="mb-2 text-xs font-semibold text-text-dim">BUSINESS RULE</div>
                <div className="grid gap-2 sm:grid-cols-2">
                  {top.guardrails.checks.map((rule) => (
                    <div key={rule.code} className="flex items-start gap-2 text-xs text-text-muted">
                      {rule.passed
                        ? <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                        : <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-danger" />}
                      {rule.message}
                    </div>
                  ))}
                </div>
              </div>
              <Button disabled={busy !== null || !top.guardrails.passed} onClick={() => create(top.id)}>
                {busy === `create:${top.id}` ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                Lập campaign để duyệt
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <section>
        <div className="mb-3 flex items-end justify-between">
          <div><h2 className="text-xl">Hàng đợi thực thi</h2><p className="text-sm text-text-muted">Chỉ campaign đã qua rule mới được duyệt.</p></div>
          <span className="mono text-xs text-text-dim">{campaigns.length} campaign</span>
        </div>
        {!campaigns.length ? (
          <Card><CardContent className="p-8 text-center text-sm text-text-muted">Chưa có campaign. Chọn kịch bản phía trên để tạo một bản mô phỏng có thể kiểm chứng.</CardContent></Card>
        ) : (
          <div className="space-y-3">
            {campaigns.map((campaign) => {
              const terminal = ["rejected", "stopped", "published"].includes(campaign.status);
              return (
                <Card key={campaign.id}>
                  <CardContent className="grid gap-4 p-5 lg:grid-cols-[1fr_auto] lg:items-center">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Store className="h-4 w-4 text-accent" /><span className="font-semibold">{campaign.name}</span>
                        <Badge variant="muted">{platformName(campaign.platform)}</Badge>
                        <Badge variant={campaign.guardrails.passed ? "success" : "danger"}>{statusText[campaign.status] ?? campaign.status}</Badge>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-sm text-text-muted">
                        <span>Giảm <b className="text-text">{campaign.simulation.discount_pct}%</b></span>
                        <span>Ngân sách <b className="text-text">{money(campaign.budget_vnd)}</b></span>
                        <span>Lợi nhuận tăng thêm <b className="text-text">{money(campaign.simulation.incremental_profit_vnd)}</b></span>
                      </div>
                      <p className="mt-2 text-xs text-text-dim">{campaign.execution.message}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {campaign.status === "simulated" && <>
                        <Button size="sm" disabled={busy !== null} onClick={() => decide(campaign, "approve")}><Check className="h-3.5 w-3.5" /> Duyệt</Button>
                        <Button size="sm" variant="ghost" disabled={busy !== null} onClick={() => decide(campaign, "reject")}><X className="h-3.5 w-3.5" /> Bỏ</Button>
                      </>}
                      {!terminal && campaign.status !== "simulated" && (
                        <Button asChild size="sm" variant="secondary">
                          <Link href={campaign.execution.seller_center_url} target="_blank" rel="noreferrer">Mở Seller Center <ExternalLink className="h-3.5 w-3.5" /></Link>
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </section>

      {recommendations.length > 1 && (
        <details className="rounded-lg border border-border bg-surface p-4">
          <summary className="cursor-pointer text-sm font-semibold">Xem {recommendations.length - 1} kịch bản thay thế</summary>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {recommendations.filter((item) => item.id !== top?.id).map((item) => (
              <div key={item.id} className="rounded-md border border-border p-4">
                <div className="flex justify-between gap-2"><b>{item.plan.name}</b><span>{item.simulation.discount_pct}%</span></div>
                <p className="mt-2 text-xs text-text-muted">{item.why}</p>
                <Button className="mt-3" size="sm" variant="secondary" disabled={busy !== null || !item.guardrails.passed} onClick={() => create(item.id)}>Lập campaign</Button>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

function Metric({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return <div className="rounded-md border border-border bg-surface-2/60 p-3">
    <div className="text-xs text-text-dim">{label}</div>
    <div className={`mono mt-1 text-lg font-bold ${good === false ? "text-danger" : "text-text"}`}>{value}</div>
  </div>;
}
