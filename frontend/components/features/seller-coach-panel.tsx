"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertTriangle } from "lucide-react";
import { ScoreGauge, AuditRadar } from "@/components/genai/score-gauge";
import {
  SELLER_AUDIT,
  SELLER_ROADMAP,
  type AuditStep,
  type RoadmapWeek,
} from "@/lib/mock-data";
import { sellerCoach } from "@/lib/features";
import { cn } from "@/lib/utils";

function scoreBand(score: number): "good" | "warn" | "bad" {
  if (score >= 75) return "good";
  if (score >= 55) return "warn";
  return "bad";
}

function AuditRow({ step, index }: { step: AuditStep; index: number }) {
  const band = scoreBand(step.score);
  return (
    <div className="flex items-start gap-3 rounded-md border border-border bg-surface px-3 py-2.5">
      <div className="mono flex h-6 w-6 shrink-0 items-center justify-center rounded border border-border bg-bg-alt text-2xs text-text-muted">
        {String(index + 1).padStart(2, "0")}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-text">{step.label}</span>
          <span
            className={cn(
              "mono text-sm",
              band === "good" && "text-success",
              band === "warn" && "text-warning",
              band === "bad" && "text-danger",
            )}
            data-tnum
          >
            {step.score}
          </span>
        </div>
        <p className="mt-1 text-xs leading-relaxed text-text-muted">{step.tip}</p>
      </div>
    </div>
  );
}

export function SellerCoachPanel() {
  const [audit, setAudit] = useState<AuditStep[]>(SELLER_AUDIT);
  const [roadmap, setRoadmap] = useState<RoadmapWeek[]>(SELLER_ROADMAP);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
    sellerCoach({ overall: 0, audit: SELLER_AUDIT, roadmap: SELLER_ROADMAP })
      .then((r) => {
        setAudit(r.audit);
        setRoadmap(r.roadmap);
      })
      .catch(() => setError(true));
  }, []);

  const overall = Math.round(
    audit.reduce((sum, s) => sum + s.score, 0) / audit.length,
  );

  const radarData = audit.map((s) => ({
    axis: s.label,
    score: s.score,
  }));

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      {error && (
        <p className="col-span-full text-sm text-danger">Không lấy được dữ liệu. Kiểm tra kết nối backend rồi thử lại.</p>
      )}

      {/* Audit summary */}
      <Card className="lg:col-span-4">
        <CardHeader>
          <div>
            <CardTitle>Điểm sức khỏe cửa hàng</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              Tính từ cùng snapshot 60 SKU, đơn hàng, đánh giá và tồn kho của Mây House demo.
            </p>
          </div>
          <Badge variant="muted">shop demo thống nhất</Badge>
        </CardHeader>
        <CardContent className="flex justify-center pb-6">
          <ScoreGauge score={overall} label="Điểm tổng" />
        </CardContent>
      </Card>

      {/* Radar chart */}
      <Card className="lg:col-span-8">
        <CardHeader>
          <div>
            <CardTitle>5 nhóm đánh giá</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              So sánh các điểm còn yếu để chọn việc cần làm trước.
            </p>
          </div>
          <Badge variant="muted">5 tiêu chí</Badge>
        </CardHeader>
        <CardContent>
          <AuditRadar data={radarData} />
        </CardContent>
      </Card>

      {/* 5-step audit list */}
      <Card className="lg:col-span-7">
        <CardHeader>
          <div>
            <CardTitle>Chi tiết đánh giá</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              Điểm từng trục + gợi ý cụ thể.
            </p>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          {audit.map((s, i) => (
            <AuditRow key={s.id} step={s} index={i} />
          ))}
        </CardContent>
      </Card>

      {/* 4-week roadmap */}
      <Card className="lg:col-span-5">
        <CardHeader>
          <div>
            <CardTitle>Kế hoạch 4 tuần</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              Các việc nên ưu tiên dựa trên tình trạng hiện tại.
            </p>
          </div>
          <Badge variant="live">Sẵn sàng thực hiện</Badge>
        </CardHeader>
        <CardContent>
          <ol className="relative space-y-4 border-l border-border-strong pl-5">
            {roadmap.map((w) => (
              <li key={w.week} className="relative">
                <span className="mono absolute -left-[27px] top-0 flex h-5 w-5 items-center justify-center rounded-full border border-accent bg-bg text-2xs text-accent">
                  W{w.week}
                </span>
                <div className="text-sm font-medium text-text">{w.title}</div>
                <ul className="mt-2 space-y-1.5 text-xs text-text-muted">
                  {w.bullets.map((b, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-accent" />
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>

          <div className="mt-4 flex items-start gap-2 rounded-md border border-warning/30 bg-warning/5 p-3 text-2xs text-text-muted">
            <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-warning" />
            <span>
              Ưu tiên tuần 1–2 trước khi chạy promotion. Nếu điểm Inventory &lt; 50,
              hoãn flash sale.
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
