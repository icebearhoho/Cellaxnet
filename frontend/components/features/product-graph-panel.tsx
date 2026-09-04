"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Boxes,
  Check,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Database,
  Info,
  Layers3,
  Loader2,
  Package,
  RefreshCw,
  ShoppingBag,
  Store,
  Trophy,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import {
  getProductGraphDetail,
  getProductGraphOverview,
  type GraphSource,
  type ProductGraphOverview,
  type ProductGraphResult,
  type ProductPerformance,
} from "@/lib/features";
import { cn } from "@/lib/utils";
import { useT, translate, useTf } from "@/lib/i18n";


const PERIOD_DAYS = 30;
const SHOPEE_PICKER_ID = -2;

function vnd(value: number | null) {
  if (value === null) return translate("Chưa có giá");
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);
}

function dateTime(value: string | null) {
  if (!value) return translate("Chưa đồng bộ");
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function shortDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "short" }).format(new Date(value));
}

function platformName(platform: string) {
  const names: Record<string, string> = {
    demo: translate("Cửa hàng"), lazada: "Lazada",
    tiktok: "TikTok Shop", shopee: "Shopee",
  };
  return names[platform] ?? platform;
}

function shopLabel(shop: { platform: string; shop_name: string }) {
  return shop.platform === "demo"
    ? translate("Dữ liệu cửa hàng")
    : platformName(shop.platform);
}

function Growth({ value }: { value: number | null }) {
  const t = useT();
  if (value === null) {
    return <span className="text-2xs text-text-dim">{t("Chưa có kỳ trước")}</span>;
  }
  const positive = value >= 0;
  const Icon = positive ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs font-semibold", positive ? "text-success" : "text-danger")}>
      <Icon className="h-3.5 w-3.5" />
      {positive ? "+" : ""}{value.toLocaleString("vi-VN")}%
    </span>
  );
}

function ProductThumb({ product, className }: { product: Pick<ProductPerformance, "image_url" | "name">; className?: string }) {
  const t = useT();
  return (
    <div className={cn("grid shrink-0 place-items-center overflow-hidden rounded-xl border border-border bg-surface-2", className)}>
      {product.image_url ? (
        // Marketplace image URL; no generated/fallback product photo is used.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={product.image_url} alt={product.name} className="h-full w-full object-cover" />
      ) : (
        <Package className="h-7 w-7 text-text-dim" aria-label={t("Sàn chưa trả ảnh sản phẩm")} />
      )}
    </div>
  );
}

function ProductCard({ product, onSelect }: { product: ProductPerformance; onSelect: () => void }) {
  const tf = useTf();
  const t = useT();
  return (
    <button
      type="button"
      onClick={onSelect}
      className="group flex w-full min-w-0 gap-3 rounded-xl border border-border bg-surface p-3 text-left transition-all hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-sm"
    >
      <ProductThumb product={product} className="h-24 w-24" />
      <div className="min-w-0 flex-1 py-0.5">
        <div className="flex items-center justify-between gap-2">
          <Badge variant="info">{tf("Top {hạng} danh mục {danh_mục}", { hạng: product.category_rank, danh_mục: t(product.category) })}</Badge>
          <div className="shrink-0 text-right">
            <p className="mb-0.5 text-2xs text-text-dim">{t("So kỳ trước")}</p>
            <Growth value={product.sales_change_pct} />
          </div>
        </div>
        <p className="mt-2 line-clamp-2 text-sm font-semibold leading-5 text-text group-hover:text-accent">{product.name}</p>
        <p className="tnum mt-2 text-sm font-bold text-text">{vnd(product.revenue_vnd)}</p>
        <p className="mt-1 text-2xs text-text-muted">{tf("{số_lượng} SP · {số_đơn} đơn · Xem so sánh", { số_lượng: product.units_sold, số_đơn: product.orders_count })} <ArrowRight className="inline h-3 w-3" /></p>
      </div>
    </button>
  );
}

function SourceStrip({ source }: { source: GraphSource }) {
  const tf = useTf();
  const t = useT();
  return (
    <Card className="overflow-hidden border-info/20 bg-info/[0.025]">
      <CardContent className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
        <div className="flex min-w-0 items-start gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-info/10 text-info">
            <Database className="h-4 w-4" />
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold text-text">
                {source.demo_data_used
                  ? t("Nguồn số liệu bán hàng")
                  : tf("Nguồn số liệu: {sàn} · {cửa_hàng}", {
                      sàn: platformName(source.platform),
                      cửa_hàng: source.shop_name,
                    })}
              </p>
              {!source.demo_data_used && <Badge variant="success">{t("Dữ liệu đồng bộ từ sàn")}</Badge>}
            </div>
            <p className="mt-1 text-xs leading-5 text-text-muted">
              {tf("Kỳ tính {từ_ngày}–{đến_ngày} · dữ liệu cập nhật đến {cập_nhật}.", {
                từ_ngày: shortDate(source.period_start),
                đến_ngày: shortDate(source.period_end),
                cập_nhật: dateTime(source.last_synced_at),
              })}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-lg border border-border bg-surface px-3 py-2"><b>{source.product_records}</b> {t("bản ghi sản phẩm")}</span>
          <span className="rounded-lg border border-border bg-surface px-3 py-2"><b>{source.order_records}</b> {t("đơn hàng")}</span>
          <span className="rounded-lg border border-border bg-surface px-3 py-2"><b>{source.order_item_records}</b> {t("dòng hàng")}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function EmptyData({ overview, reload }: { overview: ProductGraphOverview; reload: () => void }) {
  const t = useT();
  return (
    <div className="space-y-5">
      {overview.source && <SourceStrip source={overview.source} />}
      <Card className="overflow-hidden">
        <CardContent className="grid gap-8 p-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(26rem,1.1fr)] lg:p-8">
          <div className="flex flex-col justify-center">
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-warning/10 text-warning">
              <Database className="h-6 w-6" />
            </span>
            <h2 className="mt-4 text-xl font-bold text-text">{t("Chưa có dữ liệu thật để xếp hạng")}</h2>
            <p className="mt-2 text-sm leading-6 text-text-muted">{overview.missing_reason}</p>
            <div className="mt-4 flex items-start gap-2 rounded-xl border border-success/20 bg-success/[0.04] p-3 text-xs leading-5 text-text-muted">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
              {t("Khi có sản phẩm và đơn hàng, xếp hạng sẽ xuất hiện tự động theo công thức được ghi rõ trên trang.")}
            </div>
            <Button type="button" variant="outline" onClick={reload} className="mt-5 w-fit">
              <RefreshCw className="h-4 w-4" /> {t("Kiểm tra lại dữ liệu")}
            </Button>
          </div>

          <div className="rounded-2xl border border-border bg-surface-2/55 p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-text-dim">{t("Khi có dữ liệu, trang sẽ trả lời 3 câu hỏi")}</p>
            <div className="mt-4 space-y-3">
              {[
                { icon: Trophy, title: t("Danh mục nào đang tạo doanh thu?"), text: t("Xếp theo tổng thành tiền dòng hàng của các đơn hợp lệ.") },
                { icon: BarChart3, title: t("Sản phẩm nào thật sự nổi bật?"), text: t("Hiện hạng doanh thu, số bán, số đơn và so sánh với 30 ngày trước.") },
                { icon: Layers3, title: t("Khách còn lựa chọn tương tự nào?"), text: t("Tự ghép sản phẩm cùng shop, cùng danh mục theo thương hiệu, tên và mức giá.") },
              ].map((item, index) => (
                <div key={item.title} className="flex gap-3 rounded-xl border border-border bg-surface p-4">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-accent/10 text-accent"><item.icon className="h-4 w-4" /></span>
                  <div>
                    <p className="text-sm font-semibold text-text"><span className="mr-1 text-text-dim">0{index + 1}.</span>{item.title}</p>
                    <p className="mt-1 text-xs leading-5 text-text-muted">{item.text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function ProductGraphPanel() {
  const tf = useTf();
  const t = useT();
  const [overview, setOverview] = useState<ProductGraphOverview | null>(null);
  const [detail, setDetail] = useState<ProductGraphResult | null>(null);
  const [shopId, setShopId] = useState<number | undefined>();
  const [sourcePickerOpen, setSourcePickerOpen] = useState(false);
  const [sourceCommandValue, setSourceCommandValue] = useState("");
  const [category, setCategory] = useState("Tất cả");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadOverview(selectedShop = shopId) {
    setLoading(true);
    setError(null);
    setDetail(null);
    const response = await getProductGraphOverview(selectedShop, PERIOD_DAYS);
    if (!response) {
      setError(t("Không đọc được dữ liệu sản phẩm đã đồng bộ. Kiểm tra backend rồi thử lại."));
    } else {
      setOverview(response);
      setShopId(response.source?.shop_connection_id ?? selectedShop);
      setCategory("Tất cả");
    }
    setLoading(false);
  }

  useEffect(() => {
    void loadOverview();
    // Only run on first mount; shop changes are handled explicitly by the selector.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function selectProduct(productId: string) {
    if (detailLoading) return;
    setDetailLoading(true);
    setError(null);
    const response = await getProductGraphDetail(productId, shopId, PERIOD_DAYS);
    if (!response) setError(t("Không tải được bảng so sánh sản phẩm."));
    else setDetail(response);
    setDetailLoading(false);
  }

  const orderedProducts = useMemo(() => {
    if (!overview) return [];
    const orderedCategories = overview.categories
      .map((item) => item.category)
      .filter((item) => category === "Tất cả" || item === category);
    const grouped = new Map<string, ProductPerformance[]>();
    for (const product of overview.top_products) {
      if (!grouped.has(product.category)) grouped.set(product.category, []);
      grouped.get(product.category)?.push(product);
    }
    const categories = orderedCategories.map((name) => (
      (grouped.get(name) ?? []).sort((a, b) => (
        a.category_rank - b.category_rank || b.revenue_vnd - a.revenue_vnd
      ))
    ));
    if (category !== "Tất cả") return categories[0] ?? [];

    const products: Array<ProductPerformance | null> = [];
    const longestColumn = Math.max(0, ...categories.map((items) => items.length));
    for (let rankIndex = 0; rankIndex < longestColumn; rankIndex += 1) {
      for (const items of categories) {
        products.push(items[rankIndex] ?? null);
      }
    }
    return products;
  }, [overview, category]);

  const selectedShop = overview?.available_shops.find((shop) => shop.id === shopId);
  const hasShopee = overview?.available_shops.some((shop) => shop.platform === "shopee") ?? false;

  function openSourcePicker() {
    setSourceCommandValue(selectedShop ? shopLabel(selectedShop) : t("Dữ liệu cửa hàng"));
    setSourcePickerOpen(true);
  }

  function selectShop(shopConnectionId: number) {
    setSourcePickerOpen(false);
    void loadOverview(shopConnectionId);
  }

  if (loading && !overview) {
    return (
      <Card><CardContent className="flex min-h-72 flex-col items-center justify-center gap-3 text-sm text-text-muted">
        <Loader2 className="h-6 w-6 animate-spin text-accent" /> {t("Đang đọc dữ liệu sản phẩm và đơn hàng đã đồng bộ…")}
      </CardContent></Card>
    );
  }

  return (
    <div className="space-y-5">
      <Card className="overflow-hidden">
        <div className="grid gap-5 bg-gradient-to-r from-accent/[0.08] via-surface to-info/[0.06] p-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center lg:p-6">
          <div className="flex items-start gap-3">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-accent/10 text-accent"><Trophy className="h-5 w-5" /></span>
            <div>
              <h2 className="text-lg font-bold text-text">{t("Sản phẩm nổi bật của shop")}</h2>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-text-muted">
                {t("Không cần tìm kiếm. Hệ thống tự chỉ ra danh mục và sản phẩm tạo doanh thu, rồi so sánh ngay với các lựa chọn tương tự trong cùng shop.")}
              </p>
            </div>
          </div>
          {overview && overview.available_shops.length > 0 && (
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={openSourcePicker}
                className="h-11 min-w-64 justify-start gap-2 rounded-xl px-3 text-left"
                aria-haspopup="dialog"
              >
                <Store className="h-4 w-4 shrink-0 text-text-dim" />
                <span className="min-w-0 flex-1">
                  <span className="block text-2xs font-medium leading-3 text-text-muted">{t("Nguồn cửa hàng")}</span>
                  <span className="block truncate text-xs font-semibold text-text">{selectedShop ? shopLabel(selectedShop) : t("Dữ liệu cửa hàng")}</span>
                </span>
                <ChevronDown className="h-4 w-4 shrink-0 text-text-dim" />
              </Button>
              <Dialog open={sourcePickerOpen} onOpenChange={setSourcePickerOpen}>
                <DialogContent className="overflow-hidden p-0">
                  <Command value={sourceCommandValue} onValueChange={setSourceCommandValue} className="[&_[cmdk-group-heading]]:text-text-dim">
                    <CommandInput placeholder={t("Tìm cửa hàng…")} autoFocus />
                    <CommandList>
                      <CommandEmpty>{t("Không tìm thấy cửa hàng.")}</CommandEmpty>
                      <CommandGroup heading={t("Nguồn cửa hàng")}>
                        {overview.available_shops.map((shop) => (
                          <CommandItem
                            key={shop.id}
                            value={shopLabel(shop)}
                            keywords={[shop.platform]}
                            onSelect={() => selectShop(shop.id)}
                          >
                            <Store className="h-4 w-4 text-text-muted" />
                            <span className="min-w-0 flex-1 truncate">{shopLabel(shop)}</span>
                            {shop.id === shopId ? <Check className="ml-auto h-4 w-4 text-accent" /> : null}
                          </CommandItem>
                        ))}
                        {!hasShopee ? (
                          <CommandItem value="Shopee" onSelect={() => setSourcePickerOpen(false)}>
                            <Store className="h-4 w-4 text-text-muted" />
                            <span>Shopee</span>
                          </CommandItem>
                        ) : null}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </DialogContent>
              </Dialog>
            </>
          )}
        </div>
      </Card>

      {error && (
        <div className="flex items-start gap-2 rounded-xl border border-danger/20 bg-danger/5 p-4 text-sm text-danger" role="alert">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {error}
        </div>
      )}

      {overview && !overview.data_available ? (
        <EmptyData overview={overview} reload={() => void loadOverview()} />
      ) : overview?.source ? (
        <>
          <SourceStrip source={overview.source} />

          <Card>
            <CardHeader className="border-b border-border">
              <div>
                <CardTitle className="flex items-center gap-2"><Boxes className="h-4 w-4 text-accent" /> {t("Danh mục dẫn đầu doanh thu")}</CardTitle>
                <p className="mt-1 text-xs text-text-muted">{t("Chọn danh mục để lọc danh sách sản phẩm phía dưới.")}</p>
              </div>
              <Badge variant="muted">{overview.categories.length} danh mục có dữ liệu</Badge>
            </CardHeader>
            <CardContent className="grid gap-3 pt-5 md:grid-cols-2 xl:grid-cols-3">
              {overview.categories.map((item) => (
                <button
                  key={item.category}
                  type="button"
                  onClick={() => setCategory(item.category)}
                  className={cn(
                    "rounded-xl border p-4 text-left transition-all hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-sm",
                    category === item.category ? "border-accent bg-accent/[0.045]" : "border-border bg-surface",
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-2xs font-semibold uppercase tracking-wider text-accent">{tf("Top {hạng} danh mục", { hạng: item.rank })}</p>
                      <p className="mt-1 truncate text-sm font-bold text-text">{item.category}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="mb-0.5 text-2xs text-text-dim">{t("So với 30 ngày trước")}</p>
                      <Growth value={item.growth_pct} />
                    </div>
                  </div>
                  <p className="tnum mt-4 text-lg font-bold text-text">{vnd(item.revenue_vnd)}</p>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted">
                    <span>{tf("{phần_trăm}% tỷ trọng doanh thu shop", { phần_trăm: item.revenue_share_pct.toLocaleString("vi-VN") })}</span>
                    <span>{tf("{số_lượng} sản phẩm", { số_lượng: item.units_sold.toLocaleString("vi-VN") })}</span>
                    <span>{tf("{số_đơn} đơn", { số_đơn: item.orders_count.toLocaleString("vi-VN") })}</span>
                  </div>
                  <p className="mt-3 line-clamp-2 text-xs leading-5 text-text-muted">{t("Dẫn đầu:")} <b className="text-text">{item.top_product_name}</b></p>
                </button>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-border">
              <div>
                <CardTitle className="flex items-center gap-2"><ShoppingBag className="h-4 w-4 text-info" /> {t("Sản phẩm nổi bật")}</CardTitle>
                <p className="mt-1 text-xs text-text-muted">
                  {t("Xếp hạng theo thành tiền của các dòng hàng thuộc đơn hợp lệ trong kỳ 30 ngày, không dựa trên lượt xem.")}
                </p>
              </div>
              {category !== "Tất cả" && (
                <Button type="button" variant="outline" size="sm" onClick={() => setCategory("Tất cả")}>{t("Xem tất cả")}</Button>
              )}
            </CardHeader>
            <CardContent className="grid gap-4 pt-5 md:grid-cols-2 xl:grid-cols-3">
              {orderedProducts.map((product, index) => product ? (
                <ProductCard key={product.id} product={product} onSelect={() => void selectProduct(product.id)} />
              ) : (
                <div key={`empty-product-${index}`} className="hidden xl:block" aria-hidden="true" />
              ))}
            </CardContent>
          </Card>

          {detailLoading && (
            <Card><CardContent className="flex items-center justify-center gap-2 py-12 text-sm text-text-muted"><Loader2 className="h-5 w-5 animate-spin text-accent" /> {t("Đang đối chiếu các sản phẩm cùng shop…")}</CardContent></Card>
          )}

          {!detailLoading && detail?.product && (
            <Card className="overflow-hidden">
              <div className="border-b border-border bg-gradient-to-r from-accent/[0.055] to-transparent p-5">
                <p className="text-2xs font-semibold uppercase tracking-wider text-accent">{t("Chi tiết vì sao nổi bật")}</p>
                <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-center">
                  <ProductThumb product={detail.product} className="h-20 w-20" />
                  <div className="min-w-0 flex-1">
                    <h3 className="text-lg font-bold text-text">{detail.product.name}</h3>
                    <p className="mt-1 text-xs text-text-muted">{detail.product.brand || t("Chưa có thương hiệu")} · {detail.product.category} · SKU {detail.product.sku || t("sàn chưa trả")}</p>
                    <p className="mt-2 text-sm leading-6 text-text">{detail.product.highlight_reason}</p>
                  </div>
                  <div className="shrink-0 sm:text-right">
                    <p className="text-xs text-text-muted">Doanh thu {PERIOD_DAYS} ngày</p>
                    <p className="tnum mt-1 text-xl font-bold text-accent">{vnd(detail.product.revenue_vnd)}</p>
                    <p className="mt-1 text-xs text-text-muted">{tf("Hạng #{hạng} toàn shop", { hạng: detail.product.revenue_rank })}</p>
                  </div>
                </div>
              </div>

              <CardContent className="p-0">
                <div className="flex items-start gap-2 border-b border-border bg-surface-2/60 px-5 py-3 text-xs leading-5 text-text-muted">
                  <Info className="mt-0.5 h-4 w-4 shrink-0 text-info" />
                  {t("Sản phẩm tương tự được chọn trong cùng cửa hàng và cùng danh mục, ưu tiên cùng loại sản phẩm, thương hiệu, từ khoá tên và khoảng giá gần nhau.")}
                </div>
                {detail.similar_products.length === 0 ? (
                  <div className="flex flex-col items-center py-10 text-center">
                    <Layers3 className="h-7 w-7 text-text-dim" />
                    <p className="mt-2 text-sm font-semibold text-text">{t("Chưa có sản phẩm cùng danh mục để so sánh")}</p>
                    <p className="mt-1 text-xs text-text-muted">{t("Hệ thống không ghép một sản phẩm khác danh mục chỉ để lấp chỗ trống.")}</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[880px] text-left text-xs">
                      <thead className="border-b border-border bg-surface-2/35 text-text-muted">
                        <tr>
                          <th className="px-5 py-3 font-medium">{t("Lựa chọn tương tự")}</th>
                          <th className="px-4 py-3 font-medium">{t("Giá bán")}</th>
                          <th className="px-4 py-3 font-medium">Doanh thu</th>
                          <th className="px-4 py-3 font-medium">{t("Đã bán / đơn")}</th>
                          <th className="px-4 py-3 font-medium">{t("Hạng trong nhóm")}</th>
                          <th className="px-5 py-3 font-medium">{t("So với sản phẩm đang xem")}</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {detail.similar_products.map((product) => (
                          <tr key={product.id} className="align-top hover:bg-surface-2/40">
                            <td className="px-5 py-4">
                              <div className="flex gap-3">
                                <ProductThumb product={product} className="h-12 w-12 rounded-lg" />
                                <div className="min-w-0 max-w-sm">
                                  <button type="button" onClick={() => void selectProduct(product.id)} className="line-clamp-2 font-semibold text-text hover:text-accent">{product.name}</button>
                                  <p className="mt-1 text-2xs leading-4 text-text-muted">{product.relation}</p>
                                </div>
                              </div>
                            </td>
                            <td className="tnum px-4 py-4 font-medium text-text">{vnd(product.price_vnd)}</td>
                            <td className="tnum px-4 py-4 font-semibold text-text">{vnd(product.revenue_vnd)}</td>
                            <td className="tnum px-4 py-4 text-text-muted">{product.units_sold} / {product.orders_count}</td>
                            <td className="px-4 py-4"><Badge variant="muted">Top {product.category_rank} danh mục {product.category}</Badge></td>
                            <td className="max-w-xs px-5 py-4 leading-5 text-text-muted">{product.comparison}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardContent className="grid gap-4 p-5 lg:grid-cols-[auto_minmax(0,1fr)]">
              <span className="grid h-9 w-9 place-items-center rounded-lg bg-surface-2 text-text-muted"><Info className="h-4 w-4" /></span>
              <div>
                <p className="text-sm font-semibold text-text">{t("Cách các con số được tính")}</p>
                <p className="mt-1 text-xs leading-5 text-text-muted">
                  {t("Doanh thu = tổng thành tiền từng sản phẩm trong các đơn đã thanh toán, đang giao hoặc đã giao; không tính đơn chờ thanh toán, đã huỷ hay hoàn trả.")}
                </p>
                <div className="mt-3 grid gap-2 text-2xs leading-5 text-text-dim md:grid-cols-2">
                  <p><b className="text-text-muted">{t("Tăng/giảm doanh thu:")}</b> (doanh thu 30 ngày hiện tại − doanh thu 30 ngày trước) ÷ doanh thu 30 ngày trước × 100. Kỳ trước bằng 0 thì không hiện phần trăm.</p>
                  <p><b className="text-text-muted">{t("Tỷ trọng danh mục:")}</b> {t("doanh thu danh mục ÷ tổng doanh thu cửa hàng trong cùng 30 ngày × 100.")}</p>
                </div>
                <p className="mt-2 flex items-center gap-1.5 text-2xs text-text-dim"><Clock3 className="h-3.5 w-3.5" /> {t("Các biến thể có cùng mã sản phẩm được gộp thành một sản phẩm khi xếp hạng.")}</p>
              </div>
            </CardContent>
          </Card>
        </>
      ) : (
        <Card><CardContent className="flex flex-col items-center py-12 text-center"><Store className="h-8 w-8 text-text-dim" /><p className="mt-3 text-sm font-semibold text-text">{t("Chưa có nguồn cửa hàng")}</p></CardContent></Card>
      )}
    </div>
  );
}
