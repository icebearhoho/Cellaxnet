"use client";

import { useEffect, useState } from "react";
import { ChevronsUpDown, Copy, Check, RefreshCw, Search, Wand2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ContentVariant } from "@/lib/mock-data";
import { contentGenerate, getStoreProducts, type StoreProduct } from "@/lib/features";
import { useT, useTf } from "@/lib/i18n";

const PLATFORMS = ["Shopee", "Tiki", "TikTok Shop"] as const;
type Platform = (typeof PLATFORMS)[number];

const PLATFORM_VARIANT: Record<Platform, "warning" | "info" | "success"> = {
  Shopee: "warning",
  Tiki: "info",
  "TikTok Shop": "success",
};

function CtrBar({ value }: { value: number }) {
  const t = useT();
  const pct = Math.round(value * 1000) / 10;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-2xs">
        <span className="mono uppercase tracking-wider text-text-dim">
          {t("CTR ước tính (quy tắc)")}
        </span>
        <span className="mono text-text" data-tnum>
          {pct.toFixed(1)}%
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
        <div
          className="h-full rounded-full bg-accent transition-all"
          style={{ width: `${Math.min(100, pct * 8)}%` }}
        />
      </div>
    </div>
  );
}

export function ContentGeneratorPanel() {
  const t = useT();
  const tf = useTf();
  const [productName, setProductName] = useState("Áo khoác denim unisex form rộng");
  const [features, setFeatures] = useState("Denim 12oz, wash nhẹ, 2 size, unisex, free ship");
  const [activePlatform, setActivePlatform] = useState<Platform>("Shopee");
  const [copied, setCopied] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [variants, setVariants] = useState<ContentVariant[]>([]);
  const [error, setError] = useState(false);

  // Catalogue của cửa hàng, để người bán chọn thay vì gõ tay. Ô nhập vẫn tự
  // do — sản phẩm mới chưa có trong catalogue vẫn viết nội dung được.
  const [products, setProducts] = useState<StoreProduct[]>([]);
  const [productsLoading, setProductsLoading] = useState(true);
  const [pickerOpen, setPickerOpen] = useState(false);

  useEffect(() => {
    let active = true;
    void getStoreProducts().then((response) => {
      if (!active) return;
      setProducts(response?.products ?? []);
      setProductsLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  /** Điền tên và đặc điểm từ sản phẩm đã chọn. */
  function selectProduct(product: StoreProduct) {
    setProductName(product.name);
    // Thuộc tính sản phẩm chính là đặc điểm nổi bật — ghép lại thành một dòng
    // đúng định dạng ô nhập, thay vì bắt người bán gõ lại.
    const attrs = Object.entries(product.attributes ?? {})
      .map(([key, value]) => `${key} ${value}`)
      .join(", ");
    if (attrs) setFeatures(attrs);
    setPickerOpen(false);
  }

  function copy(text: string) {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text).catch(() => {});
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  async function generate() {
    setGenerating(true);
    setError(false);
    try {
      const { variants: v } = await contentGenerate(
        productName, features, [...PLATFORMS],
      );
      setVariants(v);
    } catch {
      setError(true);
    }
    setGenerating(false);
  }

  return (
    <>
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      {/* Left: input form */}
      <Card className="lg:col-span-4">
        <CardHeader>
          <div>
            <CardTitle>{t("Thông tin sản phẩm")}</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              {t("Nhập thông tin một lần để tạo nội dung phù hợp cho từng sàn.")}
            </p>
          </div>
          <Badge variant="muted">{t("3 sàn")}</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          <Field label={t("Tên sản phẩm")}>
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search
                  className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-dim"
                  aria-hidden="true"
                />
                <Input
                  value={productName}
                  onChange={(e) => setProductName(e.target.value)}
                  placeholder={t("Nhập tên hoặc chọn từ danh sách")}
                  className="pl-10"
                />
              </div>
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="h-10 w-10 shrink-0 border-accent/30 text-accent hover:bg-accent/10"
                onClick={() => setPickerOpen(true)}
                aria-label={t("Chọn sản phẩm từ catalog")}
                aria-haspopup="dialog"
              >
                <ChevronsUpDown className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
            <p className="mt-1.5 text-xs text-text-muted">
              {t("Có thể nhập sản phẩm mới hoặc chọn nhanh từ catalog của cửa hàng.")}
            </p>
          </Field>
          <Field label={t("Đặc điểm nổi bật")}>
            <textarea
              value={features}
              onChange={(e) => setFeatures(e.target.value)}
              rows={4}
              className="flex w-full rounded-lg border border-border-strong bg-bg-alt px-3 py-2 text-sm text-text placeholder:text-text-dim focus-visible:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              placeholder={t("Mỗi dòng 1 đặc điểm")}
            />
          </Field>

          <Field label={t("Sàn đang xem")}>
            <div className="grid grid-cols-3 gap-2">
              {PLATFORMS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setActivePlatform(p)}
                  className={cn(
                    "flex h-9 items-center justify-center rounded-md border text-xs transition-colors",
                    activePlatform === p
                      ? "border-accent bg-accent/10 text-accent"
                      : "border-border bg-surface text-text-muted hover:border-border-strong hover:text-text",
                  )}
                >
                  {p}
                </button>
              ))}
            </div>
          </Field>

          <Button onClick={generate} disabled={generating || !productName.trim() || !features.trim()} className="w-full">
            {generating ? (
              <>
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                {t("Đang tạo…")}
              </>
            ) : (
              <>
                <Wand2 className="h-3.5 w-3.5" />
                {t("Tạo 3 phiên bản")}
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Right: 3 platform variants side-by-side */}
      <div className="lg:col-span-8 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-text-dim">
              {t("Nội dung đã tạo")}
            </div>
            <div className="text-sm text-text-muted">
              {t("So sánh nội dung và hiệu quả dự kiến trên 3 sàn")}
            </div>
          </div>
          <Badge variant="warning">
            {t("Cần duyệt trước khi đăng")}
          </Badge>
        </div>

        {error && (
          <p className="text-sm text-danger">{t("Không tạo được nội dung. Kiểm tra kết nối backend rồi thử lại.")}</p>
        )}

        {!generating && variants.length === 0 && !error && (
          <div className="rounded-xl border border-dashed border-border p-8 text-center text-sm text-text-muted">
            {t("Nhập thông tin sản phẩm rồi bấm “Tạo 3 phiên bản”.")}
          </div>
        )}
        <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
          {variants.map((v) => (
            <ContentCard
              key={v.platform}
              variant={v}
              highlighted={v.platform === activePlatform}
              onCopy={() => copy(`${v.title}\n\n${v.body}`)}
              copied={copied && v.platform === activePlatform}
            />
          ))}
        </div>
      </div>
    </div>

      <CommandDialog open={pickerOpen} onOpenChange={setPickerOpen}>
        <CommandInput placeholder={t("Tìm sản phẩm trong catalog…")} autoFocus />
        <CommandList>
          <CommandEmpty>
            {productsLoading
              ? t("Đang tải danh sách sản phẩm…")
              : t("Không tìm thấy sản phẩm phù hợp.")}
          </CommandEmpty>
          {!productsLoading && products.length > 0 && (
            <CommandGroup heading={tf("{số_lượng} sản phẩm", { số_lượng: products.length })}>
              {products.map((product) => (
                <CommandItem
                  key={product.id}
                  value={`${product.name} ${product.brand} ${product.category}`}
                  onSelect={() => selectProduct(product)}
                  className="h-auto min-h-12 cursor-pointer py-2.5"
                >
                  <Check
                    className={cn(
                      "h-4 w-4 shrink-0 text-accent",
                      productName === product.name ? "opacity-100" : "opacity-0",
                    )}
                    aria-hidden="true"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-text">{product.name}</p>
                    <p className="mt-0.5 truncate text-xs text-text-muted">
                      {product.brand} · {t(product.category)}
                    </p>
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
        </CommandList>
      </CommandDialog>
    </>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs font-medium text-text-dim">
        {label}
      </span>
      {children}
    </label>
  );
}

function ContentCard({
  variant,
  highlighted,
  onCopy,
  copied,
}: {
  variant: ContentVariant;
  highlighted: boolean;
  onCopy: () => void;
  copied: boolean;
}) {
  return (
    <Card
      className={cn(
        "transition-colors",
        highlighted ? "border-accent" : "",
      )}
    >
      <CardHeader>
        <div>
          <Badge variant={PLATFORM_VARIANT[variant.platform]}>
            {variant.platform}
          </Badge>
          <CardTitle className="mt-2 text-sm leading-snug">
            {variant.title}
          </CardTitle>
        </div>
        <Button size="icon" variant="ghost" onClick={onCopy} aria-label="Copy">
          {copied ? (
            <Check className="h-3.5 w-3.5 text-success" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm leading-relaxed text-text">{variant.body}</p>

        <CtrBar value={variant.predictedCtr} />

        <div className="rounded-md border border-border bg-bg-alt p-2.5 text-2xs text-text-muted">
          <span className="mono uppercase tracking-wider text-text-dim">
            Rationale
          </span>
          <p className="mt-1">{variant.rationale}</p>
        </div>
      </CardContent>
    </Card>
  );
}
