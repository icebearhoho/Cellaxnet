"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Loader2,
  Minus,
  PackagePlus,
  RefreshCw,
  WalletCards,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  planRestock,
  type RestockPlan,
  type RestockFailure,
  type Category,
} from "@/lib/features";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

const CATEGORIES: Category[] = ["Thời trang", "Mỹ phẩm", "Phụ kiện"];
const MONTHS = Array.from({ length: 12 }, (_, index) => index + 1);
const HORIZON_MIN = 7;
const HORIZON_MAX = 120;

const OUTLOOK: Record<string, { label: string; Icon: typeof ArrowUpRight; className: string }> = {
  expand: { label: "Nên tăng nhập", Icon: ArrowUpRight, className: "text-success" },
  hold: { label: "Giữ mức hiện tại", Icon: Minus, className: "text-warning" },
  contract: { label: "Nhập thận trọng", Icon: ArrowDownRight, className: "text-danger" },
};

function vnd(value: number) {
  return `${value.toLocaleString("vi-VN")}₫`;
}

function compactVnd(value: number) {
  const compact = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 });
  if (value >= 1_000_000_000) return `${compact.format(value / 1_000_000_000)} tỷ`;
  if (value >= 1_000_000) return `${compact.format(value / 1_000_000)} tr`;
  if (value >= 1_000) return `${Math.round(value / 1_000)}k`;
  return vnd(value);
}

function Stat({ label, value, helper, tone = "text-text" }: { label: string; value: string; helper: string; tone?: string }) {
  const t = useT();
  return (
    <div className="rounded-xl border border-border bg-surface-2/55 p-4">
      <p className="text-2xs font-medium uppercase tracking-wider text-text-muted">{label}</p>
      <p className={cn("tnum mt-2 text-xl font-bold", tone)}>{value}</p>
      <p className="mt-1 text-2xs leading-4 text-text-dim">{helper}</p>
    </div>
  );
}

function PlanningGuide() {
  const t = useT();
  return (
    <div className="grid gap-2 text-xs text-text-muted sm:grid-cols-3">
      <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2.5"><WalletCards className="h-4 w-4 shrink-0 text-accent" /><span><b className="text-text">{t("Chọn vốn")}</b> {t("bạn có thể dùng")}</span></div>
      <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2.5"><PackagePlus className="h-4 w-4 shrink-0 text-accent" /><span><b className="text-text">{t("Xem nên nhập gì")}</b> {t("và bao nhiêu")}</span></div>
      <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2.5"><CheckCircle2 className="h-4 w-4 shrink-0 text-accent" /><span><b className="text-text">{t("Kiểm tra hiệu quả")}</b> {t("trước khi nhập")}</span></div>
    </div>
  );
}

function OutlookCard({ row }: { row: RestockPlan["outlook"][number] }) {
  const outlook = OUTLOOK[row.outlook] ?? OUTLOOK.hold;
  const Icon = outlook.Icon;
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-text">{row.category}</p>
        <span className={cn("flex items-center gap-1 text-xs font-semibold", outlook.className)}><Icon className="h-4 w-4" />{outlook.label}</span>
      </div>
      <p className="mt-2 line-clamp-2 text-xs leading-5 text-text-muted">{row.advice}</p>
      {row.peak_month ? <p className="mt-3 text-2xs text-text-dim">Cao điểm dự kiến: tháng {row.peak_month}</p> : null}
    </div>
  );
}

function PriorityRow({ item }: { item: RestockPlan["items"][number] }) {
  const t = useT();
  const reason = item.partial
    ? t("Ưu tiên nhưng ngân sách chưa đủ để nhập đủ nhu cầu")
    : item.days_of_stock_left <= 7
      ? t("Sắp hết hàng")
      : t("Nhu cầu dự kiến cao");
  return (
    <div className="grid gap-3 border-b border-border/70 px-4 py-3.5 last:border-0 sm:grid-cols-[minmax(0,1fr)_5rem_6.5rem_minmax(10rem,0.9fr)] sm:items-center sm:px-5">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-text">{item.name}</p>
        <p className="mt-0.5 truncate text-2xs text-text-muted">{item.brand} · {item.category} · {item.channel_name}</p>
      </div>
      <div className="sm:text-right"><p className="text-2xs text-text-dim sm:hidden">{t("Số lượng")}</p><p className="tnum text-sm font-bold text-text">{item.order_qty} cái</p></div>
      <div className="sm:text-right"><p className="text-2xs text-text-dim sm:hidden">{t("Vốn cần")}</p><p className="tnum text-sm font-semibold text-text">{compactVnd(item.spend_vnd)}</p></div>
      <p className="line-clamp-2 text-xs leading-5 text-text-muted">{reason}</p>
    </div>
  );
}

export function RestockPlannerPanel() {
  const t = useT();
  const now = new Date().getMonth() + 1;
  const [budgetText, setBudgetText] = useState("50000000");
  const [month, setMonth] = useState(now);
  const [horizonText, setHorizonText] = useState("30");
  const [categories, setCategories] = useState<Category[]>([]);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<RestockFailure | null>(null);
  const [result, setResult] = useState<RestockPlan | null>(null);

  const budget = Number(budgetText);
  const horizon = Number(horizonText);
  const budgetValid = budgetText.trim() !== "" && Number.isFinite(budget) && budget > 0;
  const horizonValid = horizonText.trim() !== "" && Number.isFinite(horizon) && horizon >= HORIZON_MIN && horizon <= HORIZON_MAX;
  const canRun = budgetValid && horizonValid && !busy;

  const run = useCallback(async () => {
    if (!budgetValid || !horizonValid) return;
    setBusy(true);
    setFailure(null);
    const response = await planRestock({
      budget_vnd: budget,
      month,
      horizon_days: horizon,
      categories: categories.length ? categories : undefined,
    });
    if (response.ok) setResult(response.plan);
    else setFailure(response.failure);
    setBusy(false);
  }, [budget, budgetValid, categories, horizon, horizonValid, month]);

  useEffect(() => {
    void run();
    // The first plan is loaded once; later changes are submitted explicitly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function toggleCategory(category: Category) {
    setCategories((current) => current.includes(category) ? current.filter((item) => item !== category) : [...current, category]);
  }

  return (
    <div className="space-y-5">
      <Card className="overflow-hidden">
        <div className="bg-gradient-to-r from-accent/[0.08] via-surface to-info/[0.05] p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-accent/10 text-accent"><PackagePlus className="h-5 w-5" /></span>
            <div>
              <h2 className="text-lg font-bold text-text">{t("Kế hoạch nhập hàng")}</h2>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-text-muted">{t("Tính nhanh với số vốn hiện có: nên nhập nhóm hàng nào, bao nhiêu sản phẩm và dự kiến thu được gì.")}</p>
            </div>
          </div>
          <div className="mt-5"><PlanningGuide /></div>
        </div>
      </Card>

      <Card>
        <CardHeader className="border-b border-border">
          <div>
            <CardTitle>{t("Thông tin lập kế hoạch")}</CardTitle>
            <p className="mt-1 text-xs text-text-muted">{t("Chỉ cần nhập ba thông tin dưới đây. Bỏ trống ngành để xem toàn bộ cửa hàng.")}</p>
          </div>
          <Badge variant="muted">Tối đa {HORIZON_MAX} ngày</Badge>
        </CardHeader>
        <CardContent className="space-y-4 pt-5">
          <div className="grid gap-4 md:grid-cols-3">
            <label className="block"><span className="text-2xs font-medium uppercase tracking-wider text-text-muted">{t("Ngân sách nhập")}</span><Input type="number" inputMode="numeric" value={budgetText} min={100_000} step={1_000_000} onChange={(event) => setBudgetText(event.target.value)} className="mt-1" aria-invalid={!budgetValid} /><span className={cn("mt-1 block text-2xs", budgetValid ? "text-text-dim" : "text-danger")}>{budgetValid ? vnd(budget) : t("Nhập số vốn lớn hơn 0")}</span></label>
            <label className="block"><span className="text-2xs font-medium uppercase tracking-wider text-text-muted">{t("Tháng cần hàng")}</span><select value={month} onChange={(event) => setMonth(Number(event.target.value))} className="mt-1 h-9 w-full rounded-md border border-border bg-surface-2 px-3 text-sm">{MONTHS.map((item) => <option key={item} value={item}>Tháng {item}{item === now ? " (hiện tại)" : ""}</option>)}</select></label>
            <label className="block"><span className="text-2xs font-medium uppercase tracking-wider text-text-muted">{t("Số ngày muốn đủ hàng")}</span><Input type="number" inputMode="numeric" value={horizonText} min={HORIZON_MIN} max={HORIZON_MAX} onChange={(event) => setHorizonText(event.target.value)} className="mt-1" aria-invalid={!horizonValid} /><span className={cn("mt-1 block text-2xs", horizonValid ? "text-text-dim" : "text-danger")}>{horizonValid ? `Đủ bán trong ${horizon} ngày` : `Nhập từ ${HORIZON_MIN} đến ${HORIZON_MAX}`}</span></label>
          </div>

          <div className="flex flex-wrap items-center gap-2 border-t border-border pt-4"><span className="text-2xs font-medium uppercase tracking-wider text-text-muted">{t("Chỉ xem ngành")}</span>{CATEGORIES.map((category) => <button key={category} type="button" onClick={() => toggleCategory(category)} className={cn("rounded-md border px-2.5 py-1 text-xs transition-colors", categories.includes(category) ? "border-accent bg-accent/10 text-accent" : "border-border text-text-muted hover:text-text")}>{t(category)}</button>)}{categories.length > 0 ? <button type="button" onClick={() => setCategories([])} className="text-2xs text-text-dim underline">{t("Xoá lọc")}</button> : null}</div>
          <div className="flex justify-end border-t border-border pt-4"><Button onClick={run} disabled={!canRun}>{busy ? <><Loader2 className="h-4 w-4 animate-spin" /> {t("Đang tính…")}</> : <><RefreshCw className="h-4 w-4" /> {t("Cập nhật kế hoạch")}</>}</Button></div>
        </CardContent>
      </Card>

      {failure ? <Card><CardContent className={cn("flex items-start gap-2 py-4 text-sm", failure.kind === "rate_limited" ? "text-warning" : "text-danger")}><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /><span>{failure.message}{result ? <span className="mt-1 block text-2xs text-text-dim">{t("Đang giữ kết quả gần nhất để bạn vẫn xem được.")}</span> : null}</span></CardContent></Card> : null}

      {result ? <div className="space-y-5">
        <Card>
          <CardHeader className="border-b border-border"><div><CardTitle>{t("Kết quả cần nhớ")}</CardTitle><p className="mt-1 max-w-3xl text-xs leading-5 text-text-muted">{result.summary}</p></div><Badge variant="muted">{result.horizon_days} ngày</Badge></CardHeader>
          <CardContent className="grid gap-3 pt-5 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label={t("Vốn cần dùng")} value={compactVnd(result.spent_vnd)} helper={`để đủ hàng trong ${result.horizon_days} ngày`} />
            <Stat label={result.unfunded_vnd > 0 ? "Vốn còn thiếu" : t("Ngân sách còn lại")} value={compactVnd(result.unfunded_vnd > 0 ? result.unfunded_vnd : result.remaining_vnd)} helper={result.unfunded_vnd > 0 ? "để đáp ứng toàn bộ nhu cầu dự báo" : result.budget_status === "surplus" ? "không cần nhập dư để dùng hết vốn" : t("đã phân bổ đủ")} tone={result.unfunded_vnd > 0 ? "text-warning" : result.budget_status === "surplus" ? "text-success" : "text-text"} />
            <Stat label={t("Số sản phẩm nhập")} value={`${result.total_units} cái`} helper={`${result.item_count} mã được ưu tiên`} />
            <Stat label={t("Lãi gộp dự kiến")} value={compactVnd(result.expected_profit_vnd)} helper={t("trước phí sàn và chi phí vận hành")} tone="text-success" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b border-border"><div><CardTitle>{t("Ưu tiên theo ngành")}</CardTitle><p className="mt-1 text-xs text-text-muted">{t("Một dòng cho mỗi ngành để biết nên tăng, giữ hay nhập thận trọng.")}</p></div></CardHeader>
          <CardContent className="grid gap-3 pt-5 md:grid-cols-3">{result.outlook.map((row) => <OutlookCard key={row.category} row={row} />)}</CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b border-border"><div><CardTitle>{t("Sản phẩm nên nhập trước")}</CardTitle><p className="mt-1 text-xs text-text-muted">{t("Danh sách rút gọn theo mức ưu tiên. Mở rộng danh sách chỉ khi cần kiểm tra chi tiết.")}</p></div><Badge variant="muted">{result.item_count} mã</Badge></CardHeader>
          <CardContent className="p-0">
            <div className="hidden grid-cols-[minmax(0,1fr)_5rem_6.5rem_minmax(10rem,0.9fr)] gap-3 border-b border-border bg-surface-2/50 px-5 py-2.5 text-2xs font-medium uppercase tracking-wider text-text-muted sm:grid"><span>{t("Sản phẩm")}</span><span className="text-right">{t("Nhập")}</span><span className="text-right">{t("Vốn")}</span><span>{t("Lý do")}</span></div>
            {result.items.slice(0, 8).map((item) => <PriorityRow key={`${item.sku}-${item.channel}`} item={item} />)}
            {result.items.length > 8 ? <p className="border-t border-border bg-surface-2/35 px-5 py-3 text-xs text-text-muted">Còn {result.items.length - 8} mã ít ưu tiên hơn — không đưa lên màn hình chính.</p> : null}
            {result.items.length === 0 ? <div className="flex flex-col items-center py-10 text-center"><PackagePlus className="h-7 w-7 text-text-dim" /><p className="mt-2 text-sm font-semibold text-text">{t("Chưa có sản phẩm cần nhập")}</p><p className="mt-1 text-xs text-text-muted">{t("Với ngân sách và thời gian hiện tại, hàng đang có là đủ.")}</p></div> : null}
          </CardContent>
        </Card>

        {result.skipped_count > 0 ? <div className="flex items-center gap-2 rounded-xl border border-warning/20 bg-warning/[0.05] px-4 py-3 text-xs text-text-muted"><AlertTriangle className="h-4 w-4 shrink-0 text-warning" /><span><b className="text-text">{result.skipped_count} mã chưa được đưa vào kế hoạch</b> {t("vì ngân sách không đủ; hệ thống ưu tiên các mã có tác động cao hơn.")}</span></div> : null}

      </div> : null}
    </div>
  );
}
