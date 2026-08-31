"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCw, UserMinus, Search, MessageCircle, Ruler } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  getRiskPortfolio,
  type RiskPortfolio,
  type RiskRow,
  type RiskBand,
} from "@/lib/features";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/* Phần 1 — Bảng điều phối: ai cần cứu trước, vì lý do gì              */
/* ------------------------------------------------------------------ */

/** Ba loại rủi ro, kèm việc cần làm khi loại đó ở mức cao.
 *
 *  Mỗi loại có một màu riêng (violet / xanh / hổ phách) để ba cột trong bảng
 *  phân biệt được ngay từ cái liếc đầu tiên. Đậm nhạt trong cùng một màu mới
 *  là mức độ: cao thì đặc và có chữ đậm, thấp thì mờ hẳn đi. Tách vai trò như
 *  vậy để "cột nào" và "gấp đến đâu" không tranh nhau cùng một tín hiệu. */

/** Mức rủi ro của một khách = mức *nặng nhất* trong ba loại họ đang dính.
 *  Nhờ vậy mỗi khách thuộc đúng một nhóm, ba nhóm cộng lại bằng tổng số khách. */
type RiskLevel = "high" | "medium" | "low";

function levelOf(row: RiskRow): RiskLevel {
  // The leading risk decides the row. Taking the worst of all three let regret
  // — which flags most of the customer base — mark 62% of it as urgent.
  return row.lead_band === "high" ? "high" : row.lead_band === "medium" ? "medium" : "low";
}

/** Phân bố toàn bộ khách hàng theo mức rủi ro nặng nhất họ đang dính.
 *  Thanh xếp chồng cho thấy tỉ lệ, ba ô bên dưới ghi phần trăm từng nhóm.
 *  Số khách tuyệt đối nằm ở tổng góc phải và trên các nút lọc bên dưới. */
/** Compact currency: a queue of twenty rows has no room for full VND figures,
 *  and the exact đồng is never the decision — the order of magnitude is. */
const VND = new Intl.NumberFormat("vi-VN", {
  style: "currency", currency: "VND", notation: "compact", maximumFractionDigits: 1,
});

const SPREAD_LEVELS = [
  { key: "high" as const, label: "Rủi ro cao", bar: "bg-danger", dot: "bg-danger", text: "text-danger", chip: "bg-danger/10 text-danger", cell: "border-danger/20 bg-danger/[0.05]" },
  { key: "medium" as const, label: "Trung bình", bar: "bg-warning", dot: "bg-warning", text: "text-warning", chip: "bg-warning/10 text-warning", cell: "border-warning/20 bg-warning/[0.05]" },
  { key: "low" as const, label: "An toàn", bar: "bg-success", dot: "bg-success", text: "text-success", chip: "bg-success/10 text-success", cell: "border-success/20 bg-success/[0.05]" },
];

function RiskSpread({
  spread, total,
}: {
  spread: { high: number; medium: number; low: number };
  total: number;
}) {
  const pct = (n: number) => (total > 0 ? (n / total) * 100 : 0);

  // Rounding each share on its own let 61.7 / 15.8 / 22.5 print as 62 / 16 / 23,
  // which sums to 101 and undermines every other number on the page. Largest
  // remainder hands the leftover point to whoever lost the most to rounding.
  const wholePct = (() => {
    const raw = SPREAD_LEVELS.map((lv) => pct(spread[lv.key]));
    const floors = raw.map(Math.floor);
    let left = Math.round(raw.reduce((a, b) => a + b, 0)) - floors.reduce((a, b) => a + b, 0);
    const order = raw
      .map((v, i) => ({ i, frac: v - Math.floor(v) }))
      .sort((a, b) => b.frac - a.frac);
    const out = [...floors];
    for (const { i } of order) {
      if (left <= 0) break;
      out[i] += 1;
      left -= 1;
    }
    return out;
  })();

  return (
    <div className="rounded-xl border border-border bg-bg-alt/60 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-text-dim">
          Mức rủi ro toàn bộ khách hàng
        </h4>
        <span className="tnum text-xs text-text-muted">{total} khách</span>
      </div>

      {/* Thanh xếp chồng — tỉ lệ đọc được ngay, không cần so ba con số */}
      <div className="mt-3 flex h-2.5 w-full overflow-hidden rounded-full bg-surface-3">
        {SPREAD_LEVELS.map((lv) =>
          spread[lv.key] > 0 ? (
            <div
              key={lv.key}
              className={lv.bar}
              style={{ width: `${pct(spread[lv.key])}%` }}
              title={`${lv.label}: ${spread[lv.key]}`}
            />
          ) : null,
        )}
      </div>

      {/* Ba ô bằng nhau, mỗi ô nền nhạt theo màu nhóm — nhãn và số canh giữa
          nên ba cột thẳng hàng nhau theo cả chiều ngang lẫn dọc. */}
      <div className="mt-3 grid grid-cols-3 gap-2">
        {SPREAD_LEVELS.map((lv, i) => (
          <div
            key={lv.key}
            className={cn(
              "flex flex-col items-center gap-1.5 rounded-lg border px-2 py-3",
              lv.cell,
            )}
          >
            <div className="flex items-center gap-1.5">
              <span className={cn("h-2 w-2 shrink-0 rounded-full", lv.dot)} aria-hidden="true" />
              <span className="truncate text-2xs font-medium uppercase tracking-wider text-text-muted">
                {lv.label}
              </span>
            </div>
            <div className={cn("tnum text-2xl font-semibold leading-none tracking-tight", lv.text)}>
              {wholePct[i]}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const PAGE_SIZE = 12;

function RiskPortfolioTable() {
  const [portfolio, setPortfolio] = useState<RiskPortfolio | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [focus, setFocus] = useState<RiskLevel | "all">("all");
  const [page, setPage] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const response = await getRiskPortfolio();
      if (response.ok) {
        setPortfolio(response.data);
      } else {
        setPortfolio(null);
        setLoadError(response.status
          ? `${response.message} (HTTP ${response.status})`
          : response.message);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const rows = portfolio?.customers ?? [];

  /** Phân bố khách theo mức rủi ro — cũng chính là số đếm trên các nút lọc. */
  const spread = useMemo(() => {
    const c = { high: 0, medium: 0, low: 0 };
    for (const r of rows) c[levelOf(r)] += 1;
    return c;
  }, [rows]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = rows;
    if (focus !== "all") {
      list = list.filter((r) => levelOf(r) === focus);
    }
    if (q) {
      list = list.filter(
        (r) =>
          r.customer.toLowerCase().includes(q) ||
          (r.last_product ?? "").toLowerCase().includes(q) ||
          (r.last_order_no ?? "").toLowerCase().includes(q),
      );
    }
    // Urgency first, then money. A seller works down this list in order, so a
    // large sum on a calm customer must not outrank an urgent smaller one.
    const RANK: Record<RiskLevel, number> = { high: 0, medium: 1, low: 2 };
    return [...list].sort(
      (a, b) =>
        RANK[levelOf(a)] - RANK[levelOf(b)] ||
        b.value_at_stake_vnd - a.value_at_stake_vnd,
    );
  }, [rows, focus, query]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pageCount - 1);
  const visible = filtered.slice(current * PAGE_SIZE, current * PAGE_SIZE + PAGE_SIZE);

  useEffect(() => { setPage(0); }, [query, focus]);

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Ai cần can thiệp trước</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            Gộp nguy cơ rời bỏ, hoàn trả và hối hận trên cùng một khách — xếp theo mức độ khẩn.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={load} disabled={loading}>
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          Làm mới
        </Button>
      </CardHeader>

      <CardContent>
        {loadError ? (
          <p className="text-sm text-danger" role="alert">{loadError}</p>
        ) : !portfolio ? (
          <p className="text-sm text-text-muted">
            {loading ? "Đang phân tích khách hàng…" : "Chưa có dữ liệu."}
          </p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-text-muted">Không có khách hàng nào.</p>
        ) : (
          <div className="space-y-5">
            {/* Phân bố mức rủi ro trên toàn bộ khách hàng */}
            <RiskSpread spread={spread} total={portfolio.total} />

            {/* Bảng tra cứu — lọc theo mức rủi ro, cùng ba nhóm với dashboard */}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="inline-flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() => setFocus("all")}
                  className={cn(
                    "rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                    focus === "all" ? "bg-accent/15 text-accent" : "bg-surface-2 text-text-muted hover:text-text",
                  )}
                >
                  Tất cả {rows.length}
                </button>
                {SPREAD_LEVELS.map((lv) => (
                  <button
                    key={lv.key}
                    type="button"
                    onClick={() => setFocus(lv.key)}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                      focus === lv.key ? lv.chip : "bg-surface-2 text-text-muted hover:text-text",
                    )}
                  >
                    <span
                      className={cn(
                        "h-2 w-2 shrink-0 rounded-full",
                        focus === lv.key ? lv.dot : "bg-current opacity-40",
                      )}
                      aria-hidden="true"
                    />
                    {lv.label}
                    <span className="tnum opacity-70">{spread[lv.key]}</span>
                  </button>
                ))}
              </div>
              <div className="relative sm:w-64">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-dim" />
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Tìm khách, sản phẩm, mã đơn…"
                  className="h-9 pl-9 text-xs"
                  aria-label="Tìm khách hàng"
                />
              </div>
            </div>

            {filtered.length === 0 ? (
              <p className="py-8 text-center text-sm text-text-muted">
                Không có khách nào khớp bộ lọc này.
              </p>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-border text-2xs uppercase tracking-wider text-text-dim">
                        <th className="py-2 pr-3 font-medium">Khách hàng</th>
                        <th className="border-l border-border/60 px-3 py-2 font-medium">Vấn đề</th>
                        <th className="border-l border-border/60 px-3 py-2 font-medium">Nên làm</th>
                        <th className="border-l border-border/60 px-3 py-2 text-right font-medium">
                          Giá trị có nguy cơ
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {visible.map((c) => {
                        const level = levelOf(c);
                        return (
                        <tr
                          key={c.id}
                          className={cn(
                            "border-b border-border/50 last:border-0 transition-colors hover:bg-bg-alt",
                            level === "high" && "bg-danger/[0.04]",
                          )}
                        >
                          <td className="py-3 pr-3 align-top">
                            <div className="flex items-start gap-2.5">
                              <span
                                className={cn(
                                  "mt-0.5 h-8 w-1 shrink-0 rounded-full",
                                  level === "high" ? "bg-danger"
                                    : level === "medium" ? "bg-warning"
                                    : "bg-success/40",
                                )}
                                aria-hidden="true"
                              />
                              <div className="min-w-0">
                                <div className="truncate font-medium text-text">{c.customer}</div>
                                <div className="truncate text-2xs text-text-dim">
                                  {c.last_product ?? "—"}
                                  {c.preferred_channel ? ` · ${c.preferred_channel}` : ""}
                                </div>
                              </div>
                            </div>
                          </td>

                          {/* The risk, named, with the score as supporting detail
                              rather than the headline — a percentage cannot be
                              acted on, a reason can. */}
                          <td className="border-l border-border/60 px-3 py-3 align-top">
                            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                              <span
                                className={cn(
                                  "rounded-md px-1.5 py-0.5 text-2xs font-medium",
                                  level === "high" ? "bg-danger/10 text-danger"
                                    : level === "medium" ? "bg-warning/10 text-warning"
                                    : "bg-surface-3 text-text-dim",
                                )}
                              >
                                {c.lead_label ?? "—"}
                              </span>
                              {c.lead_risk !== null && (
                                <span className="tnum text-2xs text-text-dim">
                                  {Math.round(c.lead_risk * 100)}%
                                </span>
                              )}
                            </div>
                            {c.lead_reason && (
                              <div className="mt-1 text-2xs leading-4 text-text-muted">
                                {c.lead_reason}
                              </div>
                            )}
                          </td>

                          <td className="border-l border-border/60 px-3 py-3 align-top">
                            <span className="text-xs leading-5 text-text-muted">
                              {c.lead_action ?? "—"}
                            </span>
                          </td>

                          <td className="border-l border-border/60 px-3 py-3 text-right align-top">
                            <div className="tnum text-sm font-medium text-text">
                              {VND.format(c.value_at_stake_vnd)}
                            </div>
                            <div className="tnum text-2xs text-text-dim">
                              trên {VND.format(c.lifetime_value_vnd)}
                            </div>
                          </td>
                        </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {pageCount > 1 && (
                  <div className="flex items-center justify-between border-t border-border pt-3">
                    <span className="tnum text-xs text-text-muted">
                      {current * PAGE_SIZE + 1}–{Math.min((current + 1) * PAGE_SIZE, filtered.length)}
                      {" / "}{filtered.length} khách
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="secondary" size="sm"
                        onClick={() => setPage((p) => Math.max(0, p - 1))}
                        disabled={current === 0}
                      >
                        Trước
                      </Button>
                      <Button
                        variant="secondary" size="sm"
                        onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                        disabled={current >= pageCount - 1}
                      >
                        Sau
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}


export function CustomerRiskPanel() {
  return <RiskPortfolioTable />;
}
