"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Loader2, PackagePlus, TrendingUp, TrendingDown, Minus, AlertTriangle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  planRestock, type RestockPlan, type RestockOutlook, type ChannelResult,
  type RestockFailure, type Category, type ChannelId, type CaseId,
} from "@/lib/features";
import { cn } from "@/lib/utils";
import { ChannelLinkPanel } from "./channel-link-panel";

const CATEGORIES: Category[] = ["Thời trang", "Mỹ phẩm", "Phụ kiện"];
const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1);

const CHANNEL_IDS: ChannelId[] = ["shopee", "lazada", "tiktok", "own"];
const CHANNEL_LABEL: Record<ChannelId, string> = {
  shopee: "Shopee", lazada: "Lazada", tiktok: "TikTok Shop", own: "Cửa hàng riêng",
};
/** The four demand archetypes the seller assigns per channel. */
const CASE_OPTIONS: { id: CaseId; short: string }[] = [
  { id: "hot", short: "Bán chạy" },
  { id: "slow", short: "Bán ít" },
  { id: "seasonal", short: "Theo mùa" },
  { id: "dead", short: "Không bán được" },
];
const DEFAULT_CASES: Record<ChannelId, CaseId> = {
  shopee: "hot", lazada: "slow", tiktok: "seasonal", own: "dead",
};

// Mirrors RestockPlanRequest.horizon_days (ge=7, le=120) in the backend schema.
// Validated here so an out-of-range value is caught before it becomes a 422.
const HORIZON_MIN = 7;
const HORIZON_MAX = 120;

/** Status encoding — colour is never the only cue: each ships an icon + label. */
const OUTLOOK = {
  expand: { label: "Mở rộng", cls: "text-success", Icon: TrendingUp },
  hold: { label: "Giữ nguyên", cls: "text-warning", Icon: Minus },
  contract: { label: "Thu hẹp", cls: "text-danger", Icon: TrendingDown },
} as const;

const PRESSURE = {
  low: { label: "Thấp", variant: "success" as const },
  medium: { label: "Vừa", variant: "warning" as const },
  high: { label: "Cao", variant: "danger" as const },
};

function vnd(n: number) {
  return n.toLocaleString("vi-VN") + "₫";
}
function compactVnd(n: number) {
  if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(1) + " tỷ";
  if (n >= 1_000_000) return Math.round(n / 1_000_000) + " tr";
  if (n >= 1_000) return Math.round(n / 1_000) + "k";
  return String(n);
}

/** Stat tile — a headline number needs no plot. */
function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface-2 px-3 py-2.5">
      <p className="text-2xs uppercase tracking-wider text-text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums">{value}</p>
      {sub ? <p className="mt-0.5 text-2xs text-text-dim">{sub}</p> : null}
    </div>
  );
}

/**
 * Seasonal index over the 12 calendar months for one category.
 *
 * One series, so no legend — the title names it. Single accent hue with a
 * baseline at 1.00 (the category's own normal); only the peak, the trough and
 * the planned month are labelled directly, and every bar carries a tooltip.
 */
function SeasonChart({ row, month }: { row: RestockOutlook; month: number }) {
  const [hover, setHover] = useState<number | null>(null);
  const values = row.monthly_index;
  if (!values?.length) return null;

  const max = Math.max(...values, 1.2);
  const baselinePct = (1 / max) * 100;

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <p className="text-xs font-medium">{row.category}</p>
        <p className="text-2xs text-text-dim">
          đỉnh T{row.peak_month} · đáy T{row.low_month}
        </p>
      </div>

      <div className="relative mt-2 h-24">
        {/* 1.00 = the category's ordinary month; bars above it are peak season. */}
        <div
          className="absolute inset-x-0 border-t border-dashed border-border-strong"
          style={{ bottom: `${baselinePct}%` }}
          aria-hidden
        />
        <div className="flex h-full items-end gap-[2px]">
          {values.map((v, i) => {
            const m = i + 1;
            const isPlanned = m === month;
            const isPeak = m === row.peak_month;
            const isLow = m === row.low_month;
            const label = isPeak || isLow || isPlanned;
            return (
              <div
                key={m}
                className="group relative flex h-full flex-1 items-end"
                onMouseEnter={() => setHover(m)}
                onMouseLeave={() => setHover(null)}
              >
                <div
                  className={cn(
                    "w-full rounded-t bg-accent transition-opacity",
                    isPlanned ? "opacity-100 ring-2 ring-accent/40" : "opacity-45",
                    hover === m && "opacity-100",
                  )}
                  style={{ height: `${Math.max(3, (v / max) * 100)}%` }}
                />
                {label ? (
                  <span className="pointer-events-none absolute -top-0.5 left-1/2 -translate-x-1/2 text-[9px] tabular-nums text-text-muted">
                    {v.toFixed(2)}
                  </span>
                ) : null}
                {hover === m ? (
                  <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 -translate-x-1/2 whitespace-nowrap rounded border border-border bg-surface px-1.5 py-1 text-2xs shadow-lg">
                    Tháng {m}: <span className="tabular-nums">{v.toFixed(2)}</span>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-1 flex gap-[2px]">
        {MONTHS.map((m) => (
          <span
            key={m}
            className={cn(
              "flex-1 text-center text-[9px] tabular-nums",
              m === month ? "font-semibold text-text" : "text-text-dim",
            )}
          >
            {m}
          </span>
        ))}
      </div>
    </div>
  );
}

/** One channel's outcome: what it was told to expect, and what it got. */
function ChannelCard({ row }: { row: ChannelResult }) {
  const dead = row.volume_factor <= 0;
  const funded = row.spend_vnd > 0;
  return (
    <div
      className={cn(
        "rounded-lg border p-3",
        funded ? "border-accent/40 bg-accent/5" : "border-border bg-surface-2",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium">{row.name}</p>
          <p className="text-2xs text-text-dim">
            {row.kind === "own" ? "Cửa hàng của mình" : "Sàn TMĐT"} · phí {row.commission_pct}%
          </p>
        </div>
        {/* Once orders are synced the case no longer decides anything, so the
            badge must stop implying it does. */}
        <Badge
          variant={
            row.volume_from_orders ? "success" : dead ? "danger" : funded ? "live" : "muted"
          }
        >
          {row.volume_from_orders ? "Từ đơn hàng thật" : row.case_label}
        </Badge>
      </div>

      <div className="mt-2.5 grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="text-2xs text-text-muted">Hệ số cầu</p>
          <p className="text-sm font-semibold tabular-nums">×{row.demand_factor.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-2xs text-text-muted">Nhập</p>
          <p className="text-sm font-semibold tabular-nums">{row.order_qty}</p>
        </div>
        <div>
          <p className="text-2xs text-text-muted">% vốn</p>
          <p className="text-sm font-semibold tabular-nums">{row.budget_share_pct}%</p>
        </div>
      </div>

      {/* Bar makes the split readable at a glance without another chart. */}
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-3">
        <div
          className="h-full rounded-full bg-accent"
          style={{ width: `${Math.min(100, row.budget_share_pct)}%` }}
        />
      </div>

      <p className="mt-2 text-2xs leading-relaxed text-text-muted">{row.verdict}</p>

      {funded ? (
        <p className="mt-1.5 text-2xs text-text-dim">
          Chi {compactVnd(row.spend_vnd)} · lãi {compactVnd(row.expected_profit_vnd)} ·
          phí sàn {compactVnd(row.commission_cost_vnd)}
        </p>
      ) : null}

      {/* Measured presence — say plainly when a platform cannot be measured. */}
      <div className="mt-2 border-t border-border pt-2">
        {row.measurable ? (
          <p className="text-2xs text-text-dim">
            Đo thật trên Google Shopping:{" "}
            {row.measured
              .filter((m) => m.listings > 0)
              .map((m) => `${m.category} ${m.share_pct}%`)
              .join(" · ") || "chưa có listing"}
          </p>
        ) : (
          <p className="text-2xs text-text-dim">
            {row.kind === "own"
              ? "Cửa hàng riêng — không có mặt trên Google Shopping (đúng bản chất)."
              : "Không đo được thị phần: sàn này không đẩy hàng lên Google Shopping."}
          </p>
        )}
      </div>
    </div>
  );
}

export function RestockPlannerPanel() {
  const now = new Date().getMonth() + 1;
  // Numeric fields are held as strings so the box can legitimately be empty
  // mid-edit. Holding them as numbers meant clearing the field produced 0,
  // which then rendered a stray "0" the user had to delete, and — because 0 is
  // falsy — a `value || default` guard silently substituted the default
  // instead of the value actually typed.
  const [budgetText, setBudgetText] = useState("50000000");
  const [month, setMonth] = useState(now);
  const [horizonText, setHorizonText] = useState("30");
  const [cats, setCats] = useState<Category[]>([]);
  const [scenario, setScenario] = useState(false);
  const [channelCases, setChannelCases] =
    useState<Record<ChannelId, CaseId>>(DEFAULT_CASES);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<RestockFailure | null>(null);
  const [result, setResult] = useState<RestockPlan | null>(null);

  const budget = Number(budgetText);
  const horizonRaw = Number(horizonText);
  const budgetValid = budgetText.trim() !== "" && Number.isFinite(budget) && budget > 0;
  const horizonValid =
    horizonText.trim() !== "" && Number.isFinite(horizonRaw)
    && horizonRaw >= HORIZON_MIN && horizonRaw <= HORIZON_MAX;
  const canRun = budgetValid && horizonValid && !busy;

  const run = useCallback(async () => {
    if (!budgetValid || !horizonValid) return;
    setBusy(true);
    setFailure(null);
    const r = await planRestock({
      budget_vnd: budget,
      month,
      horizon_days: horizonRaw,
      categories: cats.length ? cats : undefined,
      // 0.30 ≈ a heavy 11.11-style campaign. Only sent when the seller asks for
      // the what-if; otherwise the measured pressure is used.
      scenario_pressure: scenario ? 0.3 : undefined,
      channel_cases: channelCases,
    });
    if (r.ok) {
      setResult(r.plan);
      setFailure(null);
    } else {
      setFailure(r.failure);
      // Keep the previous plan on screen: a rate-limit blip should not wipe
      // the numbers someone is presenting from.
    }
    setBusy(false);
  }, [budget, budgetValid, month, horizonRaw, horizonValid, cats, scenario,
      channelCases]);

  // Show a real plan straight away instead of an empty panel.
  useEffect(() => {
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function toggleCat(c: Category) {
    setCats((prev) => (prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]));
  }

  return (
    <div className="space-y-4">
      {/* Sits first: once a channel is linked its real order history replaces
          the hand-entered case below it. */}
      <ChannelLinkPanel />

      {/* --- controls ------------------------------------------------------ */}
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Kế hoạch nhập hàng</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              Chia vốn theo mùa vụ (Google Trends 5 năm) và mức sale hiện tại của
              big brand (Google Shopping).
            </p>
          </div>
          <Badge variant="live">budget allocation</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <label className="block">
              <span className="text-2xs uppercase tracking-wider text-text-muted">
                Vốn nhập hàng
              </span>
              <Input
                type="number"
                inputMode="numeric"
                value={budgetText}
                min={100_000}
                step={1_000_000}
                onChange={(e) => setBudgetText(e.target.value)}
                className="mt-1"
                aria-invalid={!budgetValid}
              />
              <span
                className={cn(
                  "mt-1 block text-2xs",
                  budgetValid ? "text-text-dim" : "text-danger",
                )}
              >
                {budgetValid ? vnd(budget) : "Nhập số vốn lớn hơn 0"}
              </span>
            </label>

            <label className="block">
              <span className="text-2xs uppercase tracking-wider text-text-muted">
                Tháng lập kế hoạch
              </span>
              <select
                value={month}
                onChange={(e) => setMonth(Number(e.target.value))}
                className="mt-1 h-9 w-full rounded-md border border-border bg-surface-2 px-3 text-sm"
              >
                {MONTHS.map((m) => (
                  <option key={m} value={m}>
                    Tháng {m}
                    {m === now ? " (hiện tại)" : ""}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-2xs uppercase tracking-wider text-text-muted">
                Phủ tồn kho (ngày)
              </span>
              <Input
                type="number"
                inputMode="numeric"
                value={horizonText}
                min={HORIZON_MIN}
                max={HORIZON_MAX}
                onChange={(e) => setHorizonText(e.target.value)}
                className="mt-1"
                aria-invalid={!horizonValid}
              />
              <span
                className={cn(
                  "mt-1 block text-2xs",
                  horizonValid ? "text-text-dim" : "text-danger",
                )}
              >
                {horizonValid
                  ? `Lập kế hoạch đủ hàng bán ${horizonRaw} ngày`
                  : `Chỉ nhận từ ${HORIZON_MIN} đến ${HORIZON_MAX} ngày`}
              </span>
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-2xs uppercase tracking-wider text-text-muted">
              Ngành
            </span>
            {CATEGORIES.map((c) => (
              <button
                key={c}
                onClick={() => toggleCat(c)}
                className={cn(
                  "rounded-md border px-2.5 py-1 text-xs transition-colors",
                  cats.includes(c)
                    ? "border-accent bg-accent/10 text-accent"
                    : "border-border text-text-muted hover:text-text",
                )}
              >
                {c}
              </button>
            ))}
            {cats.length ? (
              <button
                onClick={() => setCats([])}
                className="text-2xs text-text-dim underline"
              >
                bỏ lọc
              </button>
            ) : (
              <span className="text-2xs text-text-dim">(trống = tất cả)</span>
            )}
          </div>

          {/* --- per-channel sales case ---------------------------------- */}
          <div className="border-t border-border pt-3">
            <div className="flex items-baseline justify-between">
              <span className="text-2xs uppercase tracking-wider text-text-muted">
                Tình hình bán của từng kênh
              </span>
              <span className="text-2xs text-text-dim">
                bạn tự khai — không sàn nào cho lấy số đơn qua API công khai
              </span>
            </div>
            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {CHANNEL_IDS.map((cid) => (
                <div key={cid} className="rounded-md border border-border bg-surface-2 p-2">
                  <p className="text-xs font-medium">{CHANNEL_LABEL[cid]}</p>
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {CASE_OPTIONS.map((opt) => (
                      <button
                        key={opt.id}
                        onClick={() =>
                          setChannelCases((prev) => ({ ...prev, [cid]: opt.id }))
                        }
                        className={cn(
                          "rounded px-1.5 py-0.5 text-[10px] transition-colors",
                          channelCases[cid] === opt.id
                            ? "bg-accent text-bg"
                            : "border border-border text-text-muted hover:text-text",
                        )}
                      >
                        {opt.short}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-3">
            <label className="flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={scenario}
                onChange={(e) => setScenario(e.target.checked)}
                className="h-3.5 w-3.5 accent-accent"
              />
              <span>
                Kịch bản: big brand sale mạnh (11.11)
                <span className="ml-1 text-text-dim">— giả định, không phải số đo</span>
              </span>
            </label>
            <Button onClick={run} disabled={!canRun}>
              {busy ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Đang tính…
                </>
              ) : (
                <>
                  <PackagePlus className="h-4 w-4" /> Lập kế hoạch
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {failure ? (
        <Card>
          <CardContent
            className={cn(
              "flex items-start gap-2 py-4 text-sm",
              // A rate limit is a "wait a moment", not a breakage — saying it
              // in the same red as a dead backend is what sends people
              // restarting a healthy stack.
              failure.kind === "rate_limited" ? "text-warning" : "text-danger",
            )}
          >
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              {failure.message}
              {result ? (
                <span className="mt-1 block text-2xs text-text-dim">
                  Kết quả bên dưới là của lần chạy trước, vẫn dùng để xem được.
                </span>
              ) : null}
            </span>
          </CardContent>
        </Card>
      ) : null}

      {result ? (
        <>
          {/* --- headline ------------------------------------------------- */}
          <Card>
            <CardHeader>
              <CardTitle>Kết quả</CardTitle>
              <div className="flex flex-wrap gap-1.5">
                {result.scenario ? <Badge variant="warning">kịch bản giả định</Badge> : null}
                {result.live_refresh ? <Badge variant="live">live</Badge> : null}
                <Badge variant="muted">{result.weeks_of_history} tuần lịch sử</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm leading-relaxed">{result.summary}</p>

              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <Stat
                  label="Nhập"
                  value={`${result.total_units} cái`}
                  sub={`${result.item_count} mã hàng`}
                />
                <Stat
                  label="Dùng vốn"
                  value={`${result.budget_used_pct}%`}
                  sub={`còn ${compactVnd(result.remaining_vnd)}`}
                />
                <Stat
                  label="Lãi dự kiến"
                  value={compactVnd(result.expected_profit_vnd)}
                  sub={`biên ${result.expected_margin_pct}%`}
                />
                <Stat
                  label="ROI"
                  value={`${result.roi_pct}%`}
                  sub={`trên ${compactVnd(result.spent_vnd)} vốn`}
                />
              </div>
            </CardContent>
          </Card>

          {/* --- per-channel outcome -------------------------------------- */}
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Vốn chia cho 4 kênh thế nào</CardTitle>
                <p className="mt-1 text-xs text-text-muted">
                  Hàng gửi vào kho sàn nào là gắn với sàn đó, nên hệ thống xếp
                  hạng theo từng cặp (kênh × mã) và đổ vốn vào nơi hàng thực sự
                  quay được — đã trừ phí sàn.
                </p>
              </div>
              <Badge variant="muted">{result.channels.length} kênh</Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {result.channels.map((c) => (
                  <ChannelCard key={c.channel} row={c} />
                ))}
              </div>
              <p className="border-t border-border pt-2 text-2xs text-text-dim">
                Thị phần từng sàn đo thật từ Google Shopping
                {result.channel_market_fetched_at
                  ? ` (lấy lúc ${result.channel_market_fetched_at})`
                  : ""}
                . Riêng số đơn của shop bạn trên mỗi kênh là do bạn khai — Shopee,
                Lazada và TikTok Shop đều khoá dữ liệu đó sau đăng nhập seller.
              </p>
            </CardContent>
          </Card>

          {/* --- season + outlook ----------------------------------------- */}
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Mùa vụ theo ngành</CardTitle>
                <p className="mt-1 text-xs text-text-muted">
                  Chỉ số 1.00 = tháng bình thường của ngành đó. Cột đậm là tháng
                  đang lập kế hoạch.
                </p>
              </div>
              <Badge variant="muted">google trends · {result.trends_window}</Badge>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
                {result.outlook.map((row) => (
                  <SeasonChart key={row.category} row={row} month={result.month} />
                ))}
              </div>

              <div className="space-y-1.5 border-t border-border pt-3">
                {result.outlook.map((row) => {
                  const o = OUTLOOK[row.outlook];
                  return (
                    <div
                      key={row.category}
                      className="flex flex-wrap items-center justify-between gap-2 text-xs"
                    >
                      <span className={cn("flex items-center gap-1.5", o.cls)}>
                        <o.Icon className="h-3.5 w-3.5" />
                        <span className="font-medium">{o.label}</span>
                        <span className="text-text">· {row.category}</span>
                      </span>
                      <span className="text-text-muted">
                        mùa {row.season_index.toFixed(2)} × cạnh tranh{" "}
                        {row.competition_multiplier.toFixed(2)} ={" "}
                        <span className="tabular-nums text-text">
                          {row.combined_factor.toFixed(2)}
                        </span>
                      </span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* --- big brand sale ------------------------------------------- */}
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Big brand đang sale</CardTitle>
                <p className="mt-1 text-xs text-text-muted">
                  Đo từ giá đang bán so với giá gạch trên Google Shopping.
                </p>
              </div>
              <Badge variant="muted">{result.brands.length} brand</Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {result.competition.map((c) => {
                  const p = PRESSURE[c.level];
                  return (
                    <div
                      key={c.category}
                      className="flex items-center gap-2 rounded-md border border-border bg-surface-2 px-2.5 py-1.5 text-xs"
                    >
                      <span className="font-medium">{c.category}</span>
                      <Badge variant={p.variant}>áp lực {p.label}</Badge>
                      <span className="text-text-muted">
                        cầu ×{c.demand_multiplier.toFixed(2)}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="text-text-muted">
                    <tr className="border-b border-border text-left">
                      <th className="py-1.5 pr-3 font-medium">Brand</th>
                      <th className="py-1.5 pr-3 font-medium">Ngành</th>
                      <th className="py-1.5 pr-3 text-right font-medium">SP đang sale</th>
                      <th className="py-1.5 pr-3 text-right font-medium">Giảm TB</th>
                      <th className="py-1.5 text-right font-medium">Áp lực</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.brands.map((b) => (
                      <tr key={b.brand + b.category} className="border-b border-border/50">
                        <td className="py-1.5 pr-3 font-medium">{b.brand}</td>
                        <td className="py-1.5 pr-3 text-text-muted">{b.category}</td>
                        <td className="py-1.5 pr-3 text-right tabular-nums">
                          {b.offers_on_sale}/{b.offers_seen}
                        </td>
                        <td className="py-1.5 pr-3 text-right tabular-nums">
                          {b.avg_discount > 0 ? `-${Math.round(b.avg_discount * 100)}%` : "—"}
                        </td>
                        <td className="py-1.5 text-right tabular-nums">
                          {b.pressure.toFixed(3)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* --- the plan -------------------------------------------------- */}
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Nhập mã nào, bao nhiêu</CardTitle>
                <p className="mt-1 text-xs text-text-muted">
                  Xếp theo ROI × độ gấp × mùa vụ × áp lực cạnh tranh. Trần 25% vốn
                  mỗi mã để không dồn hết tiền vào một chỗ.
                </p>
              </div>
              <Badge variant="muted">{result.item_count} mã</Badge>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="text-text-muted">
                    <tr className="border-b border-border text-left">
                      <th className="py-1.5 pr-3 font-medium">Sản phẩm / kênh</th>
                      <th className="py-1.5 pr-3 text-right font-medium">Tồn</th>
                      <th className="py-1.5 pr-3 text-right font-medium">Cần</th>
                      <th className="py-1.5 pr-3 text-right font-medium">Nhập</th>
                      <th className="py-1.5 pr-3 text-right font-medium">Chi</th>
                      <th className="py-1.5 pr-3 text-right font-medium">Lãi</th>
                      <th className="py-1.5 font-medium">Lý do</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.items.map((i) => (
                      <tr key={i.sku} className="border-b border-border/50 align-top">
                        <td className="py-2 pr-3">
                          <p className="font-medium">{i.name}</p>
                          <p className="text-text-dim">
                            {i.brand} · {i.category}
                          </p>
                          <Badge variant="muted" className="mt-1">
                            {i.channel_name}
                          </Badge>
                        </td>
                        <td className="py-2 pr-3 text-right tabular-nums">
                          {i.stock}
                          <p className="text-text-dim">{i.days_of_stock_left}ng</p>
                        </td>
                        <td className="py-2 pr-3 text-right tabular-nums text-text-muted">
                          {i.need_qty}
                        </td>
                        <td className="py-2 pr-3 text-right">
                          <span className="font-semibold tabular-nums">{i.order_qty}</span>
                          {i.partial ? (
                            <p className="text-2xs text-warning">thiếu vốn</p>
                          ) : null}
                        </td>
                        <td className="py-2 pr-3 text-right tabular-nums">
                          {compactVnd(i.spend_vnd)}
                        </td>
                        <td className="py-2 pr-3 text-right tabular-nums text-success">
                          {compactVnd(i.expected_profit_vnd)}
                        </td>
                        <td className="py-2 text-text-muted">{i.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {result.skipped.length ? (
                <div className="mt-4 border-t border-border pt-3">
                  {/* Counted per (channel, SKU) line: the same product can be
                      funded on one channel and skipped on another. */}
                  <p className="text-xs font-medium text-warning">
                    Hết vốn — {result.skipped.length} dòng (kênh × mã) phải bỏ qua
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {result.skipped.slice(0, 12).map((s) => (
                      <span
                        key={s.sku}
                        className="rounded border border-border bg-surface-2 px-2 py-0.5 text-2xs text-text-muted"
                        title={`Cần ${s.need_qty} · giá vốn ${vnd(s.cost_vnd)}`}
                      >
                        {s.name} <span className="text-text-dim">×{s.need_qty}</span>
                      </span>
                    ))}
                    {result.skipped.length > 12 ? (
                      <span className="text-2xs text-text-dim">
                        +{result.skipped.length - 12} mã nữa
                      </span>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <p className="text-2xs text-text-dim">
            Nguồn: {result.data_source}. Trends kéo lúc {result.trends_fetched_at ?? "—"},
            sale brand lúc {result.brand_sale_fetched_at ?? "—"}. Hệ số nhạy cạnh
            tranh {result.competition_sensitivity} là giả định chính sách, không
            phải số đo.
          </p>
        </>
      ) : null}
    </div>
  );
}
