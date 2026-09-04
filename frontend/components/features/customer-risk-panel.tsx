"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCw, Search, Lightbulb } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  getRiskPortfolio,
  type RiskGroup,
  type RiskPortfolio,
} from "@/lib/features";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

/* ------------------------------------------------------------------ */
/* Nhóm khách theo việc cần làm, không theo mức độ nặng nhẹ            */
/* ------------------------------------------------------------------ */

/** Colour per tone. Kept here rather than on the server: the API says how
 *  urgent a group is, the panel decides what that looks like. */
const TONE = {
  danger: {
    dot: "bg-danger",
    text: "text-danger",
    tab: "border-danger/40 bg-danger/10 text-danger",
    panel: "border-danger/20 bg-danger/[0.04]",
  },
  warning: {
    dot: "bg-warning",
    text: "text-warning",
    tab: "border-warning/40 bg-warning/10 text-warning",
    panel: "border-warning/20 bg-warning/[0.04]",
  },
  success: {
    dot: "bg-success",
    text: "text-success",
    tab: "border-success/40 bg-success/10 text-success",
    panel: "border-success/20 bg-success/[0.04]",
  },
} as const;

const PAGE_SIZE = 12;

function RiskPortfolioTable() {
  const t = useT();
  const [portfolio, setPortfolio] = useState<RiskPortfolio | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [groupKey, setGroupKey] = useState<string | null>(null);
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

  const rows = useMemo(() => portfolio?.customers ?? [], [portfolio]);
  const groups = useMemo(() => portfolio?.groups ?? [], [portfolio]);

  // Open on the group that needs work, not on the largest one — the page
  // exists to answer "who first", and landing on 68 steady customers answers
  // nothing. Falls back to the first group when everything is calm.
  useEffect(() => {
    if (groupKey || groups.length === 0) return;
    const urgent = groups.find((g) => g.count > 0 && g.tone !== "success");
    setGroupKey((urgent ?? groups[0]).key);
  }, [groups, groupKey]);

  const active: RiskGroup | null = useMemo(
    () => groups.find((g) => g.key === groupKey) ?? groups[0] ?? null,
    [groups, groupKey],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = active ? rows.filter((r) => r.group_key === active.key) : rows;
    if (q) {
      list = list.filter(
        (r) =>
          r.customer.toLowerCase().includes(q) ||
          (r.last_product ?? "").toLowerCase().includes(q) ||
          (r.last_order_no ?? "").toLowerCase().includes(q),
      );
    }
    return list;
  }, [rows, active, query]);

  useEffect(() => { setPage(0); }, [query, groupKey]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pageCount - 1);
  const visible = filtered.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE);

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
        <div>
          <CardTitle>{t("Ai cần can thiệp trước")}</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            {t("Khách được chia theo việc cần làm — mỗi nhóm một hành động.")}
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
            {loading ? t("Đang phân tích khách hàng…") : t("Chưa có dữ liệu.")}
          </p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-text-muted">{t("Không có khách hàng nào.")}</p>
        ) : (
          <div className="space-y-5">
            {/* How the base splits across the three risk bands. The customer
                total sits on this header so the bar always carries its own
                denominator. */}
            <div className="rounded-2xl border border-border bg-bg-alt p-4 lg:p-5">
              <div className="min-w-0">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-text">{t("Phân bổ rủi ro")}</p>
                  <p className="tnum text-xs text-text-muted">{portfolio.total} khách hàng</p>
                </div>
                <div
                  className="mt-3 flex h-4 w-full overflow-hidden rounded-full bg-surface-3"
                  role="img"
                  aria-label={groups.map((g) => `${g.label}: ${g.count} khách`).join(", ")}
                >
                  {groups.map((g) =>
                    g.count > 0 ? (
                      <span
                        key={g.key}
                        className={cn("h-full border-r-2 border-bg-alt last:border-r-0", TONE[g.tone].dot)}
                        style={{ width: `${(g.count / portfolio.total) * 100}%` }}
                        aria-hidden="true"
                      />
                    ) : null,
                  )}
                </div>
                <ul className="mt-4 grid grid-cols-2 gap-x-5 gap-y-2 sm:grid-cols-4">
                  {groups.map((g) => (
                    <li key={g.key} className="flex min-w-0 items-center gap-2">
                      <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", TONE[g.tone].dot)} aria-hidden="true" />
                      <span className="min-w-0 truncate text-xs text-text-muted" title={g.label}>
                        {g.label}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Group tabs. Each carries its own count, since a group name
                without a size cannot be prioritised against the others. */}
            <div className="flex flex-wrap gap-2">
              {groups.map((g) => {
                const tone = TONE[g.tone];
                const on = active?.key === g.key;
                return (
                  <button
                    key={g.key}
                    type="button"
                    onClick={() => setGroupKey(g.key)}
                    aria-pressed={on}
                    disabled={g.count === 0}
                    className={cn(
                      "inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium",
                      "transition-colors focus-visible:outline-none focus-visible:ring-2",
                      "focus-visible:ring-accent focus-visible:ring-offset-1 focus-visible:ring-offset-bg",
                      "disabled:cursor-not-allowed disabled:opacity-40",
                      on ? tone.tab : "border-border bg-surface-2 text-text-muted hover:text-text",
                    )}
                  >
                    <span className={cn("h-2 w-2 shrink-0 rounded-full", tone.dot)} aria-hidden="true" />
                    {g.label}
                    <span className="tnum opacity-70">{g.count}</span>
                  </button>
                );
              })}
            </div>

            {active && (
              <>
                {/* One action for the whole group. This is why the groups are
                    cut by work rather than severity: a single line here is only
                    honest if it is right for every customer listed below it. */}
                <div className={cn("rounded-xl border px-5 py-4", TONE[active.tone].panel)}>
                  <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-text-muted">
                    <Lightbulb className={cn("h-3.5 w-3.5", TONE[active.tone].text)} aria-hidden="true" />
                    {t("Hành động đề xuất")}
                  </p>
                  <p className={cn("mt-2 text-sm leading-6", TONE[active.tone].text)}>
                    {active.action}
                  </p>
                </div>

                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-xs text-text-muted">
                    {t("Hiển thị")} <span className="tnum">{filtered.length}</span> trên{" "}
                    <span className="tnum">{active.count}</span> {t("khách hàng")}
                  </p>
                  <div className="relative sm:w-64">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-dim" />
                    <Input
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder={t("Tìm khách, sản phẩm, mã đơn…")}
                      className="h-9 pl-9 text-xs"
                      aria-label={t("Tìm khách hàng")}
                    />
                  </div>
                </div>

                {filtered.length === 0 ? (
                  <p className="py-8 text-center text-sm text-text-muted">
                    {t("Không có khách nào khớp từ khoá này.")}
                  </p>
                ) : (
                  <>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <thead>
                          <tr className="border-b border-border text-2xs uppercase tracking-wider text-text-dim">
                            <th className="py-2 pr-3 font-medium">{t("Khách hàng")}</th>
                            <th className="px-3 py-2 font-medium">{t("Sản phẩm gần nhất")}</th>
                            <th className="px-3 py-2 font-medium">{t("Kênh")}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {visible.map((c) => (
                            <tr
                              key={c.id}
                              className="border-b border-border/50 transition-colors last:border-0 hover:bg-bg-alt"
                            >
                              <td className="py-3 pr-3">
                                <div className="flex items-center gap-2.5">
                                  <span
                                    className={cn("h-8 w-1 shrink-0 rounded-full", TONE[active.tone].dot)}
                                    aria-hidden="true"
                                  />
                                  <div className="min-w-0">
                                    <div className="truncate font-medium text-text">{c.customer}</div>
                                    {c.last_order_no && (
                                      <div className="truncate text-2xs text-text-dim">
                                        {c.last_order_no}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </td>
                              <td className="px-3 py-3 text-xs text-text-muted">
                                <span className="line-clamp-1">{c.last_product ?? "—"}</span>
                              </td>
                              <td className="px-3 py-3 text-xs text-text-muted">
                                {c.preferred_channel ?? "—"}
                              </td>
                            </tr>
                          ))}
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
                            {t("Trước")}
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
