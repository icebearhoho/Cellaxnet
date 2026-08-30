"use client";

import { useEffect, useState } from "react";
import { Bot, Check, RefreshCw, ShieldCheck, X } from "lucide-react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Option = { id: string; label: string; risk: string; impact: Record<string, number> };
type Opportunity = {
  id: number; kind: string; severity: string; status: string; title: string;
  explanation: string; evidence: Record<string, string | number>; options: Option[];
  model: string | null; llm_used: boolean; provider: string; selected_option_id: string | null;
};

const money = (value: number) => `${new Intl.NumberFormat("vi-VN").format(value)}₫`;
const showValue = (key: string, value: string | number) =>
  key.endsWith("_vnd") && typeof value === "number" ? money(value) : String(value);

export function AutopilotPanel() {
  const [items, setItems] = useState<Opportunity[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const response = await api.get<Opportunity[]>("/autopilot/opportunities");
      setItems(response.data ?? []);
    } catch { setError("Hãy chọn workspace đang hoạt động trước khi mở Autopilot."); }
  };
  useEffect(() => { void load(); }, []);

  const refresh = async () => {
    setBusy("refresh"); setError(null);
    try {
      const response = await api.post<Opportunity[]>("/autopilot/refresh", {});
      setItems(response.data ?? []);
    } catch { setError("Không thể phân tích. Kiểm tra workspace, Ollama và backend."); }
    finally { setBusy(null); }
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
    } catch { setError("Action không hợp lệ hoặc m không có quyền manager/owner."); }
    finally { setBusy(null); }
  };

  return (
    <div className="space-y-5">
      <Card className="overflow-hidden border-accent/25 bg-gradient-to-br from-accent/10 via-surface to-surface">
        <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex gap-3">
            <div className="rounded-xl bg-accent/15 p-3"><Bot className="h-5 w-5 text-accent" /></div>
            <div>
              <div className="font-semibold text-text">Seller Autopilot</div>
              <p className="mt-1 max-w-2xl text-sm text-text-muted">
                Ollama đọc evidence của shop và viết explanation ngắn. Mọi con số do backend tính; action chỉ chạy sau khi seller duyệt.
              </p>
            </div>
          </div>
          <Button onClick={refresh} disabled={busy !== null} variant="primary">
            <RefreshCw className={`h-4 w-4 ${busy === "refresh" ? "animate-spin" : ""}`} />
            {busy === "refresh" ? "Ollama Cloud đang phân tích…" : "Quét cơ hội"}
          </Button>
        </CardContent>
      </Card>

      {error && <div className="rounded-xl border border-danger/30 bg-danger/10 p-3 text-sm text-danger">{error}</div>}
      {!items.length && !error && <Card><CardContent className="p-8 text-center text-sm text-text-muted">Chưa có opportunity. Bấm “Quét cơ hội” để model phân tích shop.</CardContent></Card>}

      {items.map((item) => (
        <Card key={item.id} className="overflow-hidden">
          <CardHeader className="border-b border-border">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle>{item.title}</CardTitle>
              <div className="flex gap-2">
                <Badge variant={item.severity === "critical" ? "danger" : "muted"}>{item.severity}</Badge>
                <Badge variant="muted">{item.status}</Badge>
              </div>
            </div>
            <p className="mt-2 text-sm leading-6 text-text-muted">{item.explanation}</p>
            <div className="mt-2 flex items-center gap-2 text-xs text-text-dim">
              <ShieldCheck className="h-3.5 w-3.5" />
              {item.llm_used ? `Ollama Cloud · ${item.model}` : `Fallback định lượng · API chưa khả dụng`}
            </div>
          </CardHeader>
          <CardContent className="space-y-4 p-5">
            <div className="flex flex-wrap gap-2">
              {Object.entries(item.evidence).map(([key, value]) => (
                <span key={key} className="rounded-lg bg-surface-2 px-2.5 py-1.5 text-xs text-text-muted">
                  {key.replaceAll("_", " ")}: <b className="text-text">{showValue(key, value)}</b>
                </span>
              ))}
            </div>
            <div className="grid gap-3 lg:grid-cols-3">
              {item.options.map((option) => {
                const terminal = item.status === "applied" || item.status === "rejected";
                return (
                  <div key={option.id} className={`rounded-xl border p-4 ${item.selected_option_id === option.id ? "border-accent/50 bg-accent/5" : "border-border bg-surface-2/40"}`}>
                    <div className="font-medium text-text">{option.label}</div>
                    <div className="mt-1 text-xs text-text-dim">risk: {option.risk}</div>
                    <div className="mt-3 space-y-1 text-xs text-text-muted">
                      {Object.entries(option.impact).map(([key, value]) => <div key={key}>{key.replaceAll("_", " ")}: <b>{showValue(key, value)}</b></div>)}
                    </div>
                    {!terminal && <div className="mt-4 flex flex-wrap gap-2">
                      <Button size="sm" variant="secondary" disabled={busy !== null} onClick={() => act(item, option)}>Mô phỏng</Button>
                      <Button size="sm" variant="primary" disabled={busy !== null} onClick={() => act(item, option, "approve")}><Check className="h-3.5 w-3.5" />Duyệt</Button>
                      <Button size="sm" variant="ghost" disabled={busy !== null} onClick={() => act(item, option, "reject")}><X className="h-3.5 w-3.5" /></Button>
                    </div>}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
