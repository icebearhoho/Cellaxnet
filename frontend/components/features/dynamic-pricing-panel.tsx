"use client";

import { type FormEvent, useEffect, useId, useState } from "react";
import {
  AlertCircle,
  BadgeDollarSign,
  BarChart3,
  Calculator,
  Check,
  ChevronsUpDown,
  CircleDollarSign,
  Database,
  Droplets,
  FlaskConical,
  Gem,
  Lightbulb,
  Loader2,
  MoveHorizontal,
  PackageSearch,
  RefreshCw,
  Search,
  ShieldCheck,
  Shirt,
  SlidersHorizontal,
  Wallet,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import {
  getStoreProducts,
  recommendPrice,
  type PriceSource,
  type PricingResult,
  type StoreProduct,
} from "@/lib/features";
import { cn } from "@/lib/utils";

const CATEGORIES = ["Thời trang", "Mỹ phẩm", "Phụ kiện"] as const;

/** Commission rates mirror backend/app/data/restock_market.json — the backend
 *  recomputes from that file, so these labels are display only. */
const CHANNELS = [
  { id: "shopee", label: "Shopee", fee: "5%" },
  { id: "lazada", label: "Lazada", fee: "4%" },
  { id: "tiktok", label: "TikTok Shop", fee: "5%" },
  { id: "own", label: "Cửa hàng riêng", fee: "2%" },
] as const;

/** Industry gross-margin references, by category.
 *
 *  Retail apparel runs a 50-70% gross margin (Inditex 57-60%, Nike 43-50%,
 *  ASOS 45-50%, Vietnamese labels 50-65%) precisely because rent, staffing and
 *  chain operations come out of it afterwards. Beauty sits lower on a single
 *  SKU but carries heavier marketing.
 *
 *  These are *references*, not defaults: the slider here measures margin after
 *  cost and marketplace fee but before ads, vouchers and operations, so a
 *  seller matching the industry number is not left with the industry's profit.
 *  `hint` says which end of that they are aiming at. */
const MARGIN_GUIDES: Record<string, { marks: number[]; hint: number; note: string }> = {
  "Thời trang": {
    marks: [30, 40, 50, 60],
    hint: 50,
    note: "Biên gộp ngành thời trang bán lẻ thường 50–65%",
  },
  "Mỹ phẩm": {
    marks: [25, 35, 45, 55],
    hint: 35,
    note: "Mỹ phẩm biên gộp cao nhưng chi phí marketing lớn",
  },
  "Phụ kiện": {
    marks: [25, 35, 45, 55],
    hint: 40,
    note: "Phụ kiện thường có biên gộp 40–55%",
  },
};

const DEFAULT_GUIDE = { marks: [10, 20, 30, 40], hint: 20, note: "" };

type Category = (typeof CATEGORIES)[number];

const CATEGORY_META = {
  "Thời trang": {
    icon: Shirt,
    active: "border-info bg-info/10 text-info",
    iconColor: "text-info",
  },
  "Mỹ phẩm": {
    icon: Droplets,
    active: "border-series-4 bg-series-4/10 text-series-4",
    iconColor: "text-series-4",
  },
  "Phụ kiện": {
    icon: Gem,
    active: "border-accent bg-accent/10 text-accent",
    iconColor: "text-accent",
  },
} as const;
type PricingQuery = {
  name: string;
  category: Category;
  currentPrice?: number;
  unitCost?: number;
  minMarginPct: number;
  channel: string;
  stockUnits?: number;
  dailySales?: number;
};

const VND = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});

function parsePrice(value: string): number | undefined {
  if (!value.trim()) return undefined;
  const parsed = Number(value.replace(/\D/g, ""));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

/** Names the data behind the median.
 *
 *  The organisers' dataset covers cosmetics but no fashion or accessories, so
 *  the panel mixes observed and simulated figures. Saying which is which is
 *  the honest option — and a few observed shops are a reference, not the
 *  Shopee-wide market price, so the badge reports the shop count too.
 */
function SourceBadge(
  { source, shopCount, marketLabel }:
  { source: PriceSource; shopCount: number | null; marketLabel: string | null },
) {
  if (source === "demo") {
    return (
      <span className="mt-1.5 flex w-fit items-center gap-1 rounded-md bg-surface-2 px-1.5 py-0.5 text-[11px] text-text-dim">
        <FlaskConical className="h-3 w-3" aria-hidden="true" />
        Dữ liệu mô phỏng
      </span>
    );
  }
  const shops = shopCount ? ` · ${shopCount} nhà bán` : "";
  return (
    <span className="mt-1.5 flex w-fit items-center gap-1 rounded-md bg-success/10 px-1.5 py-0.5 text-[11px] font-medium text-success">
      <Database className="h-3 w-3" aria-hidden="true" />
      {marketLabel ?? "Shopee"} · T7/2026{shops}
    </span>
  );
}

function markerPosition(value: number, low: number, high: number): number {
  const width = Math.max(high - low, 1);
  return Math.min(100, Math.max(0, ((value - low) / width) * 100));
}

export function DynamicPricingPanel() {
  const [name, setName] = useState("Serum Vitamin C 15%");
  const [category, setCategory] = useState<Category>("Mỹ phẩm");
  // Empty, not pre-filled: a seeded price is submitted as if the seller typed
  // it, and the whole point of the field is their own number.
  const [price, setPrice] = useState("");
  const [cost, setCost] = useState("");
  const [margin, setMargin] = useState(20);
  const [marginTouched, setMarginTouched] = useState(false);
  const [channel, setChannel] = useState<string>("shopee");
  const [stockUnits, setStockUnits] = useState("");
  const [dailySales, setDailySales] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<PricingResult | null>(null);
  const [submitted, setSubmitted] = useState<PricingQuery | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [products, setProducts] = useState<StoreProduct[]>([]);
  const [productsLoading, setProductsLoading] = useState(true);
  const [productPickerOpen, setProductPickerOpen] = useState(false);
  const nameId = useId();
  const priceId = useId();
  const costId = useId();
  const marginId = useId();
  const stockId = useId();
  const salesId = useId();

  useEffect(() => {
    let active = true;
    setProductsLoading(true);

    void getStoreProducts(undefined, category).then((response) => {
      if (!active) return;
      setProducts(response?.products ?? []);
      setProductsLoading(false);
    });

    return () => {
      active = false;
    };
  }, [category]);

  function selectCategory(nextCategory: Category) {
    if (nextCategory === category) return;
    setCategory(nextCategory);
    setName("");
    setPrice("");
    setProductPickerOpen(false);
    setError(null);
  }

  function selectProduct(product: StoreProduct) {
    setName(product.name);
    setPrice(String(product.price_vnd));
    setProductPickerOpen(false);
    setError(null);
  }

  // Industry reference for whichever category is selected. Switching category
  // moves the suggested mark with it, but only until the seller sets a margin
  // themselves — after that their number stands.
  const guide = MARGIN_GUIDES[category] ?? DEFAULT_GUIDE;

  useEffect(() => {
    if (!marginTouched) setMargin(guide.hint);
  }, [guide.hint, marginTouched]);

  const currentPrice = parsePrice(price);
  const unitCost = parsePrice(cost);
  const stockCount = parsePrice(stockUnits);
  const salesRate = dailySales ? Number(dailySales) : undefined;
  const runwayDays =
    stockCount !== undefined && salesRate ? stockCount / salesRate : null;
  const isDirty = Boolean(
    result && submitted && (
      submitted.name !== name.trim()
      || submitted.category !== category
      || submitted.currentPrice !== currentPrice
      // The cost side changes the floor, so it has to mark the result stale too.
      || submitted.unitCost !== unitCost
      || submitted.minMarginPct !== margin
      || submitted.channel !== channel
      || submitted.stockUnits !== stockCount
      || submitted.dailySales !== salesRate
    ),
  );

  async function run(event?: FormEvent) {
    event?.preventDefault();
    if (busy) return;

    const productName = name.trim();
    if (!productName) {
      setError("Nhập tên sản phẩm để bắt đầu định giá.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const response = await recommendPrice(productName, category, currentPrice, {
        unitCost, minMarginPct: margin, channel,
        stockUnits: stockCount, dailySales: salesRate,
      });
      if (response.ok) {
        setResult(response.data);
        setSubmitted({
          name: productName, category, currentPrice,
          unitCost, minMarginPct: margin, channel,
          stockUnits: stockCount, dailySales: salesRate,
        });
        return;
      }

      setResult(null);
      setSubmitted(null);
      setError(
        response.status === 403
          ? "Tài khoản chưa có quyền định giá. Hãy dùng tài khoản người bán hoặc quản trị viên."
          : response.message,
      );
    } finally {
      setBusy(false);
    }
  }

  const priceDelta = result && submitted?.currentPrice
    ? Math.round(
        ((result.recommended_price - submitted.currentPrice) / submitted.currentPrice) * 100,
      )
    : null;
  const recommendedPosition = result
    ? markerPosition(result.recommended_price, result.low, result.high)
    : 0;
  const medianPosition = result
    ? markerPosition(result.category_median, result.low, result.high)
    : 0;

  return (
    <Card
      className="overflow-hidden rounded-xl border-t-2 border-t-accent hover:border-border hover:border-t-accent"
      aria-labelledby="pricing-workspace-title"
    >
      <div className="grid min-h-[520px] lg:grid-cols-[minmax(320px,0.78fr)_minmax(0,1.22fr)]">
        <section className="border-b border-border lg:border-b-0 lg:border-r" aria-labelledby="pricing-workspace-title">
          {/* Cùng chiều cao và cùng nền với header cột phải, để đường kẻ ngang
              giữa hai cột nối thẳng thành một mạch. */}
          <div className="flex h-[69px] items-center gap-3 border-b border-border bg-surface-2/60 px-5 sm:px-6">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-accent/10 text-accent">
              <SlidersHorizontal className="h-4.5 w-4.5" aria-hidden="true" />
            </span>
            <h2 id="pricing-workspace-title" className="text-base font-semibold text-text">
              Thiết lập định giá
            </h2>
          </div>

          <form onSubmit={run} className="space-y-6 px-5 py-6 sm:px-6" noValidate>
            <fieldset>
              <legend className="text-sm font-medium text-text">Danh mục</legend>
              <div className="mt-2 grid grid-cols-3 gap-2">
                {CATEGORIES.map((item) => {
                  const meta = CATEGORY_META[item];
                  const CategoryIcon = meta.icon;
                  return (
                    <button
                      key={item}
                      type="button"
                      onClick={() => selectCategory(item)}
                      aria-pressed={category === item}
                      className={cn(
                        "flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-lg border px-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/30",
                        category === item
                          ? meta.active
                          : "border-border bg-surface text-text-muted hover:border-border-strong hover:bg-surface-2 hover:text-text",
                      )}
                    >
                      <CategoryIcon className={cn("h-4 w-4 shrink-0", category === item ? "" : meta.iconColor)} aria-hidden="true" />
                      <span>{item}</span>
                    </button>
                  );
                })}
              </div>
            </fieldset>

            <div>
              <label htmlFor={nameId} className="text-sm font-medium text-text">
                Tên sản phẩm <span className="text-danger" aria-hidden="true">*</span>
              </label>
              <div className="mt-2 flex gap-2">
                <div className="relative min-w-0 flex-1">
                  <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-dim" aria-hidden="true" />
                  <Input
                    id={nameId}
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="rounded-lg pl-10"
                    aria-required="true"
                    aria-invalid={Boolean(error && !name.trim())}
                    placeholder="Nhập tên hoặc chọn từ danh sách"
                  />
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="h-11 w-11 shrink-0 rounded-lg border-accent/30 text-accent hover:bg-accent/10"
                  onClick={() => setProductPickerOpen(true)}
                  aria-label={`Tìm sản phẩm trong danh mục ${category}`}
                  aria-haspopup="dialog"
                >
                  <ChevronsUpDown className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
              <p className="mt-2 text-xs leading-5 text-text-muted">
                Có thể nhập sản phẩm mới hoặc chọn nhanh từ catalog của cửa hàng.
              </p>
            </div>

            <div>
              <label htmlFor={priceId} className="flex items-center gap-2 text-sm font-medium text-text">
                <CircleDollarSign className="h-4 w-4 text-success" aria-hidden="true" />
                <span>Giá bán hiện tại <span className="font-normal text-text-muted">(không bắt buộc)</span></span>
              </label>
              <div className="relative mt-2">
                <Input
                  id={priceId}
                  value={price}
                  onChange={(event) => setPrice(event.target.value.replace(/\D/g, ""))}
                  placeholder="450000"
                  inputMode="numeric"
                  className="rounded-lg pr-14 tnum"
                  aria-describedby={`${priceId}-hint`}
                />
                <span className="pointer-events-none absolute inset-y-0 right-4 flex items-center text-sm text-text-dim">
                  VND
                </span>
              </div>
              <p id={`${priceId}-hint`} className="mt-2 text-xs leading-5 text-text-muted">
                Dùng để tính mức tăng hoặc giảm so với giá đang bán.
              </p>
            </div>

            <div className="rounded-lg border border-border bg-surface-2/40 p-4">
              <label htmlFor={costId} className="flex items-center gap-2 text-sm font-medium text-text">
                <Wallet className="h-4 w-4 text-warning" aria-hidden="true" />
                <span>Giá vốn <span className="font-normal text-text-muted">(không bắt buộc)</span></span>
              </label>
              <div className="relative mt-2">
                <Input
                  id={costId}
                  value={cost}
                  onChange={(event) => setCost(event.target.value.replace(/\D/g, ""))}
                  placeholder="80000"
                  inputMode="numeric"
                  className="rounded-lg pr-14 tnum"
                  aria-describedby={`${costId}-hint`}
                />
                <span className="pointer-events-none absolute inset-y-0 right-4 flex items-center text-sm text-text-dim">
                  VND
                </span>
              </div>
              <p id={`${costId}-hint`} className="mt-2 text-xs leading-5 text-text-muted">
                Nhập giá vốn để hệ thống không đề xuất mức giá làm bạn lỗ.
              </p>

              {cost && (
                <div className="mt-4 space-y-4 border-t border-border pt-4">
                  <div>
                    <label htmlFor={marginId} className="flex items-center justify-between text-sm font-medium text-text">
                      <span>Biên lợi nhuận mong muốn</span>
                      <span className="tnum text-warning">{margin}%</span>
                    </label>
                    <input
                      id={marginId}
                      type="range"
                      min={5}
                      max={70}
                      step={1}
                      value={margin}
                      onChange={(event) => {
                        setMargin(Number(event.target.value));
                        setMarginTouched(true);
                      }}
                      className="mt-2 w-full accent-warning"
                    />
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      {guide.marks.map((mark) => (
                        <button
                          key={mark}
                          type="button"
                          onClick={() => { setMargin(mark); setMarginTouched(true); }}
                          className={cn(
                            "rounded-md border px-2 py-0.5 text-xs tnum transition-colors",
                            margin === mark
                              ? "border-warning bg-warning/10 text-warning"
                              : "border-border text-text-muted hover:bg-surface-2",
                          )}
                        >
                          {mark}%
                          {mark === guide.hint && (
                            <span className="ml-1 text-2xs opacity-70">ngành</span>
                          )}
                        </button>
                      ))}
                    </div>
                    {guide.note && (
                      <p className="mt-2 text-xs leading-5 text-text-dim">{guide.note}</p>
                    )}
                    {/* Naming what is *not* deducted matters more than what is:
                        a seller reading "you keep 20%" will plan around it, and
                        ads, vouchers, shipping support and returns come out of
                        that 20% without ever appearing here. */}
                    <p className="mt-1.5 text-xs leading-5 text-text-muted">
                      Lợi nhuận sau giá vốn và phí sàn, tính trên giá bán. Chưa trừ quảng cáo,
                      voucher, phí đóng gói, vận chuyển shop hỗ trợ hay hoàn hàng — hãy để biên
                      cao hơn mức tối thiểu bạn cần.
                    </p>
                  </div>

                  <div>
                    <span className="text-sm font-medium text-text">Kênh bán</span>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {CHANNELS.map((option) => (
                        <button
                          key={option.id}
                          type="button"
                          onClick={() => setChannel(option.id)}
                          className={cn(
                            "rounded-lg border px-3 py-1.5 text-xs transition-colors",
                            channel === option.id
                              ? "border-warning bg-warning/10 text-warning"
                              : "border-border text-text-muted hover:bg-surface-2",
                          )}
                        >
                          {option.label}
                          <span className="ml-1 text-text-dim">{option.fee}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Stock only matters as a rate: 500 units is a fortnight for
                      one product and half a year for another, and only the
                      second is worth discounting. */}
                  <div>
                    <span className="text-sm font-medium text-text">
                      Tồn kho <span className="font-normal text-text-muted">(không bắt buộc)</span>
                    </span>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      <div>
                        <label htmlFor={stockId} className="text-xs text-text-muted">
                          Số lượng còn
                        </label>
                        <Input
                          id={stockId}
                          value={stockUnits}
                          onChange={(e) => setStockUnits(e.target.value.replace(/\D/g, ""))}
                          placeholder="120"
                          inputMode="numeric"
                          className="mt-1 h-9 rounded-lg text-xs tnum"
                        />
                      </div>
                      <div>
                        <label htmlFor={salesId} className="text-xs text-text-muted">
                          Bán mỗi ngày
                        </label>
                        <Input
                          id={salesId}
                          value={dailySales}
                          onChange={(e) => setDailySales(e.target.value.replace(/[^\d.]/g, ""))}
                          placeholder="2"
                          inputMode="decimal"
                          className="mt-1 h-9 rounded-lg text-xs tnum"
                        />
                      </div>
                    </div>
                    {runwayDays !== null && (
                      <p className="mt-2 text-xs leading-5 text-text-muted">
                        Đủ bán khoảng <span className="tnum">{runwayDays.toFixed(0)}</span> ngày
                        {runwayDays >= 60 && " — hàng quay vòng chậm, hệ thống sẽ đề xuất giảm giá."}
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>

            {error && !name.trim() && (
              <p className="text-sm text-danger" role="alert">{error}</p>
            )}

            <Button
              type="submit"
              disabled={busy}
              size="lg"
              className="w-full rounded-lg"
            >
              {busy && <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />}
              {!busy && <Calculator className="h-4 w-4" aria-hidden="true" />}
              {busy ? "Đang lấy dữ liệu giá…" : result ? "Cập nhật đề xuất" : "Xem giá đề xuất"}
            </Button>

            <p className="text-center text-xs text-text-dim">
              Kết quả mang tính tham khảo, chưa tự động thay đổi giá bán.
            </p>
          </form>
        </section>

        <section className="min-w-0 bg-bg-alt/40" aria-labelledby="pricing-result-title" aria-busy={busy}>
          <div className="flex h-[69px] items-center justify-between gap-4 border-b border-border bg-surface-2/60 px-5 sm:px-6">
            <div className="flex min-w-0 items-center gap-3">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-success/10 text-success">
                <BarChart3 className="h-4.5 w-4.5" aria-hidden="true" />
              </span>
              <h2 id="pricing-result-title" className="text-base font-semibold text-text">Kết quả định giá</h2>
            </div>
            {result && (
              <span className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
                isDirty ? "bg-warning/10 text-warning" : "bg-success/10 text-success",
              )}>
                {isDirty ? <RefreshCw className="h-3 w-3" aria-hidden="true" /> : <Check className="h-3 w-3" aria-hidden="true" />}
                {isDirty ? "Cần cập nhật" : "Đã cập nhật"}
              </span>
            )}
          </div>

          <div className="p-5 sm:p-6">
            {busy ? (
              <div className="space-y-5" role="status" aria-live="polite">
                <p className="flex items-center gap-2 text-sm font-medium text-text">
                  <Loader2 className="h-4 w-4 animate-spin text-accent motion-reduce:animate-none" aria-hidden="true" />
                  Đang đối chiếu mặt bằng giá
                </p>
                <div className="h-24 animate-pulse rounded-lg bg-surface-2 motion-reduce:animate-none" />
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <div className="h-20 animate-pulse rounded-lg bg-surface-2 motion-reduce:animate-none" />
                  <div className="h-20 animate-pulse rounded-lg bg-surface-2 motion-reduce:animate-none" />
                  <div className="h-20 animate-pulse rounded-lg bg-surface-2 motion-reduce:animate-none" />
                </div>
              </div>
            ) : error && name.trim() ? (
              <div className="rounded-lg border border-danger/20 bg-surface p-5" role="alert">
                <div className="flex gap-3">
                  <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-danger" aria-hidden="true" />
                  <div>
                    <p className="font-medium text-text">Không thể lấy giá đề xuất</p>
                    <p className="mt-1 text-sm leading-6 text-text-muted">{error}</p>
                    <Button type="button" variant="secondary" size="sm" className="mt-4 rounded-lg" onClick={() => run()}>
                      <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" /> Thử lại
                    </Button>
                  </div>
                </div>
              </div>
            ) : !result ? (
              <div className="rounded-lg border border-border bg-surface">
                <div className="flex items-start gap-3 border-b border-border px-5 py-4">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-accent/10 text-accent">
                    <BarChart3 className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <div>
                    <p className="text-sm font-medium text-text">Chưa có kết quả</p>
                    <p className="mt-1 text-sm leading-6 text-text-muted">
                      Điền thông tin sản phẩm và chọn “Xem giá đề xuất”.
                    </p>
                  </div>
                </div>
                <dl className="divide-y divide-border px-5">
                  {["Giá đề xuất", "Khoảng giá tham khảo", "Trung vị danh mục"].map((label) => (
                    <div key={label} className="flex items-center justify-between gap-4 py-4">
                      <dt className="text-sm text-text-muted">{label}</dt>
                      <dd className="tnum text-sm font-medium text-text-dim">—</dd>
                    </div>
                  ))}
                </dl>
              </div>
            ) : (
              <div className="space-y-5" aria-live="polite">
                <div className="rounded-lg border border-accent/20 bg-accent/[0.025] p-5 sm:p-6">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="flex items-center gap-2 text-sm font-medium text-text-muted">
                        <BadgeDollarSign className="h-4 w-4 text-accent" aria-hidden="true" /> Giá bán đề xuất
                      </p>
                      <p className="tnum mt-2 text-3xl font-semibold tracking-tight text-accent-deep sm:text-4xl">
                        {VND.format(result.recommended_price)}
                      </p>
                    </div>
                    {priceDelta !== null && Number.isFinite(priceDelta) && (
                      <span className={cn(
                        "rounded-md px-2.5 py-1.5 text-sm font-semibold tnum",
                        priceDelta > 0
                          ? "bg-success/10 text-success"
                          : priceDelta < 0
                            ? "bg-warning/10 text-warning"
                            : "bg-surface-2 text-text-muted",
                      )}>
                        {priceDelta > 0 ? "+" : ""}{priceDelta}% so với giá hiện tại
                      </span>
                    )}
                  </div>

                  <div className="mt-7" aria-label={`Khoảng giá từ ${VND.format(result.low)} đến ${VND.format(result.high)}`}>
                    <div className="relative h-2 rounded-full bg-accent/15">
                      <span
                        className="absolute top-1/2 h-5 w-0.5 -translate-y-1/2 bg-warning"
                        style={{ left: `${medianPosition}%` }}
                        aria-hidden="true"
                      />
                      <span
                        className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface bg-accent shadow-sm"
                        style={{ left: `${recommendedPosition}%` }}
                        aria-hidden="true"
                      />
                    </div>
                    <div className="mt-3 grid grid-cols-3 text-xs text-text-muted">
                      <span className="tnum">{VND.format(result.low)}</span>
                      <span className="text-center">Trung vị</span>
                      <span className="tnum text-right">{VND.format(result.high)}</span>
                    </div>
                  </div>
                </div>

                <dl className="grid grid-cols-3 gap-3">
                  <div className="rounded-lg border border-info/20 bg-info/[0.035] p-4">
                    <dt className="flex flex-col gap-2 text-xs text-text-muted">
                      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-info/10 text-info">
                        <CircleDollarSign className="h-4 w-4" aria-hidden="true" />
                      </span>
                      Giá hiện tại
                    </dt>
                    <dd className="tnum mt-2 text-sm font-semibold text-text">
                      {submitted?.currentPrice ? VND.format(submitted.currentPrice) : "Chưa nhập"}
                    </dd>
                  </div>
                  <div className="rounded-lg border border-success/20 bg-success/[0.035] p-4">
                    <dt className="flex flex-col gap-2 text-xs text-text-muted">
                      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-success/10 text-success">
                        <BarChart3 className="h-4 w-4" aria-hidden="true" />
                      </span>
                      Trung vị danh mục
                    </dt>
                    <dd className="mt-2">
                      <span className="tnum text-sm font-semibold text-text">
                        {VND.format(result.category_median)}
                      </span>
                      <span className="tnum ml-1.5 text-xs text-text-dim">
                        /{result.sample_size} SP
                      </span>
                      <SourceBadge
                        source={result.data_source}
                        shopCount={result.shop_count}
                        marketLabel={result.market_label}
                      />
                    </dd>
                  </div>
                  <div className="rounded-lg border border-warning/20 bg-warning/[0.035] p-4">
                    <dt className="flex flex-col gap-2 text-xs text-text-muted">
                      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-warning/10 text-warning">
                        <MoveHorizontal className="h-4 w-4" aria-hidden="true" />
                      </span>
                      Biên giá tham khảo
                    </dt>
                    <dd className="tnum mt-2 text-sm font-semibold text-text">
                      {VND.format(result.low)} – {VND.format(result.high)}
                    </dd>
                  </div>
                </dl>

                {/* Pricing is a choice, and one number hides that. Three real
                    market positions make the trade visible: cheaper sells
                    faster, dearer earns more per unit. */}
                {result.strategies.length > 0 && (
                  <div>
                    <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
                      <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
                      Chọn hướng định giá
                    </p>
                    <div className="mt-3 grid gap-2 sm:grid-cols-3">
                      {result.strategies.map((s) => {
                        const chosen = s.price === result.recommended_price;
                        return (
                          <div
                            key={s.key}
                            className={cn(
                              "rounded-lg border p-4",
                              chosen
                                ? "border-accent bg-accent/[0.05]"
                                : "border-border bg-surface-2/40",
                            )}
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span className={cn(
                                "text-xs font-medium",
                                chosen ? "text-accent" : "text-text",
                              )}>
                                {s.label}
                              </span>
                              {chosen && (
                                <span className="rounded-md bg-accent/15 px-1.5 py-0.5 text-2xs font-medium text-accent">
                                  Đề xuất
                                </span>
                              )}
                            </div>
                            <p className="tnum mt-2 text-lg font-semibold text-text">
                              {VND.format(s.price)}
                            </p>
                            <p className="mt-1 text-2xs leading-4 text-text-muted">{s.goal}</p>
                            {s.margin_pct !== null && (
                              <p className="mt-2 text-2xs text-text-dim">
                                Lợi nhuận <span className="tnum text-success">{s.margin_pct}%</span>
                              </p>
                            )}
                            {s.lifted_by_floor && (
                              <p className="mt-1.5 text-2xs leading-4 text-warning">
                                Đã nâng lên giá sàn — không bán thấp hơn được.
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {result.market_p25 !== null && result.market_p75 !== null && (
                  <div className="rounded-lg border border-border bg-surface-2/40 px-5 py-4">
                    <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
                      <BarChart3 className="h-4 w-4" aria-hidden="true" />{" "}
                      Mặt bằng giá {result.market_label ?? "quan sát được"}
                    </p>

                    {/* A median alone cannot say whether a category is tight or
                        five-fold wide, which is exactly what decides how much
                        room a seller has to move. */}
                    <div className="mt-4 flex items-end justify-between gap-2 text-xs">
                      <div>
                        <div className="text-text-dim">Rẻ hơn 25%</div>
                        <div className="tnum mt-0.5 font-medium text-text">{VND.format(result.market_p25)}</div>
                      </div>
                      <div className="text-center">
                        <div className="text-text-dim">Trung vị</div>
                        <div className="tnum mt-0.5 font-semibold text-success">{VND.format(result.category_median)}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-text-dim">Đắt hơn 25%</div>
                        <div className="tnum mt-0.5 font-medium text-text">{VND.format(result.market_p75)}</div>
                      </div>
                    </div>

                    <div className="relative mt-3 h-1.5 rounded-full bg-surface-2">
                      <div className="absolute inset-y-0 left-1/4 right-1/4 rounded-full bg-success/30" />
                      {result.price_percentile !== null && (
                        <div
                          className="absolute -top-1 h-3.5 w-0.5 rounded bg-accent"
                          style={{ left: `${Math.min(98, Math.max(1, result.price_percentile))}%` }}
                          aria-hidden="true"
                        />
                      )}
                    </div>

                    {result.price_percentile !== null && (
                      <p className="mt-3 text-xs leading-5 text-text-muted">
                        Giá của bạn đắt hơn{" "}
                        <span className="tnum font-medium text-accent">{result.price_percentile}%</span>{" "}
                        trong {result.sample_size} sản phẩm quan sát được.
                      </p>
                    )}
                  </div>
                )}

                {/* Why the price moved off the market number. Without this the
                    suggestion just looks lower than the median for no reason. */}
                {result.price_action && (
                  <div
                    className={cn(
                      "flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg border px-4 py-3 text-xs",
                      result.price_action === "clearance"
                        ? "border-info/30 bg-info/[0.05] text-info"
                        : "border-warning/30 bg-warning/[0.05] text-warning",
                    )}
                  >
                    <PackageSearch className="h-4 w-4 shrink-0" aria-hidden="true" />
                    {result.price_action === "clearance" ? (
                      <span>
                        Đề xuất <strong>xả hàng</strong>: tồn kho đủ bán{" "}
                        <span className="tnum">{result.stock_runway_days?.toFixed(0)}</span> ngày.
                      </span>
                    ) : (
                      <span>
                        Hàng quay vòng chậm nhưng <strong>giá vốn không cho phép giảm</strong> —
                        giữ ở giá sàn để không lỗ.
                      </span>
                    )}
                  </div>
                )}

                {result.price_floor !== null && (
                  <div
                    className={cn(
                      "rounded-lg border px-5 py-4",
                      result.floor_above_market
                        ? "border-danger/30 bg-danger/[0.05]"
                        : "border-border bg-surface-2/40",
                    )}
                  >
                    <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
                      <ShieldCheck className="h-4 w-4" aria-hidden="true" /> Giá sàn an toàn
                    </p>
                    <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                      <span className="tnum text-lg font-semibold text-text">
                        {VND.format(result.price_floor)}
                      </span>
                      {result.margin_pct_at_recommended !== null && (
                        <span className="text-xs text-text-muted">
                          Lợi nhuận tại giá đề xuất:{" "}
                          <span className="tnum font-medium text-success">
                            {result.margin_pct_at_recommended}%
                          </span>
                        </span>
                      )}
                      {result.channel_name && (
                        <span className="text-xs text-text-dim">
                          sau giá vốn và phí {result.channel_name} {result.channel_commission_pct}%
                        </span>
                      )}
                    </div>
                    {result.floor_above_market && (
                      <p className="mt-2 flex items-start gap-1.5 text-xs leading-5 text-danger">
                        <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                        Trung vị thị trường thấp hơn giá vốn của bạn — bán theo thị trường sẽ lỗ.
                        Cân nhắc giảm giá nhập hoặc chọn sản phẩm khác thay vì hạ giá.
                      </p>
                    )}
                  </div>
                )}

                <div className="rounded-lg border border-warning/20 bg-warning/[0.035] px-5 py-4">
                  <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-warning">
                    <Lightbulb className="h-4 w-4" aria-hidden="true" /> Cơ sở đề xuất
                  </p>
                  <p className="mt-2 text-sm leading-6 text-text-muted">{result.rationale}</p>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>

      <CommandDialog open={productPickerOpen} onOpenChange={setProductPickerOpen}>
        <CommandInput placeholder={`Tìm sản phẩm trong ${category}…`} autoFocus />
        <CommandList>
          <CommandEmpty>
            {productsLoading ? "Đang tải danh sách sản phẩm…" : "Không tìm thấy sản phẩm phù hợp."}
          </CommandEmpty>
          {!productsLoading && products.length > 0 && (
            <CommandGroup heading={`${category} · ${products.length} sản phẩm`}>
              {products.map((product) => (
                <CommandItem
                  key={product.id}
                  value={`${product.name} ${product.brand}`}
                  onSelect={() => selectProduct(product)}
                  className="h-auto min-h-12 cursor-pointer py-2.5"
                >
                  <Check
                    className={cn(
                      "h-4 w-4 shrink-0 text-accent",
                      name === product.name ? "opacity-100" : "opacity-0",
                    )}
                    aria-hidden="true"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-text">{product.name}</p>
                    <p className="mt-0.5 truncate text-xs text-text-muted">{product.brand}</p>
                  </div>
                  <span className="tnum shrink-0 text-sm font-medium text-text">
                    {VND.format(product.price_vnd)}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
        </CommandList>
      </CommandDialog>
    </Card>
  );
}
