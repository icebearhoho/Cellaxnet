"use client";

import { useEffect, useState, useCallback } from "react";
import { Search, Loader2, PackageOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { getStoreProducts, type StoreProduct } from "@/lib/features";
import { trackEvent } from "@/lib/journey-track";
import { addToCart } from "@/lib/cart";
import { StoreProductCard } from "@/components/store/store-product-card";

const CATEGORIES = ["Tất cả", "Thời trang", "Mỹ phẩm", "Phụ kiện"] as const;

export default function StorePage() {
  const [query, setQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState<string>("Tất cả");
  const [products, setProducts] = useState<StoreProduct[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (q: string, category: string) => {
    setLoading(true);
    setError(null);
    try {
      const cat = category === "Tất cả" ? undefined : category;
      const res = await getStoreProducts(q || undefined, cat);
      if (!res) {
        setProducts(null);
        setError("Chưa kết nối được cửa hàng. Máy chủ có thể đang khởi động, hãy thử lại.");
        return;
      }
      setProducts(res.products);
    } catch {
      setProducts(null);
      setError("Chưa kết nối được cửa hàng. Máy chủ có thể đang khởi động, hãy thử lại.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Load all products on mount.
  useEffect(() => {
    load("", "Tất cả");
  }, [load]);

  const activeCat = activeCategory === "Tất cả" ? undefined : activeCategory;

  const submitSearch = () => {
    trackEvent("search", { category: activeCat, query });
    load(query, activeCategory);
  };

  const selectCategory = (category: string) => {
    setActiveCategory(category);
    load(query, category);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold">Cửa hàng Cellaxnet</h1>
        <p className="mt-1 text-text-muted">Thời trang, mỹ phẩm và phụ kiện.</p>
      </div>

      {/* Search + filters */}
      <div className="space-y-4 border-b border-border pb-6">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-text-dim" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") submitSearch();
              }}
              placeholder="Tìm sản phẩm, thương hiệu…"
              className="h-11 w-full rounded-full border border-border bg-surface pl-11 pr-4 text-sm text-text outline-none transition-colors focus:border-accent"
            />
          </div>
          <button
            type="button"
            onClick={submitSearch}
            className="inline-flex items-center gap-1.5 rounded-full bg-accent px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
          >
            Tìm
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => selectCategory(c)}
              className={cn(
                "rounded-full px-4 py-2 text-sm font-medium transition-colors",
                activeCategory === c
                  ? "bg-accent text-white"
                  : "bg-surface-2 text-text-muted hover:text-text",
              )}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Grid / states */}
      {loading ? (
        <div className="grid place-items-center rounded-lg border border-border bg-surface py-20 text-text-muted">
          <Loader2 className="h-6 w-6 animate-spin" />
          <p className="mt-3 text-sm">Đang tải sản phẩm…</p>
        </div>
      ) : products === null ? (
        <div className="grid place-items-center rounded-lg border border-border bg-surface py-20 text-center">
          <PackageOpen className="h-8 w-8 text-text-dim" strokeWidth={1.5} />
          <p className="mt-3 text-lg font-bold">Cửa hàng đang nghỉ một chút</p>
          <p className="mt-1 text-text-muted">{error ?? "Chưa tải được sản phẩm. Bạn thử lại sau nhé!"}</p>
          <button
            type="button"
            onClick={() => load(query, activeCategory)}
            className="mt-4 rounded-full bg-accent px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
          >
            Thử tải lại
          </button>
        </div>
      ) : products.length === 0 ? (
        <div className="grid place-items-center rounded-lg border border-border bg-surface py-20 text-center">
          <PackageOpen className="h-8 w-8 text-text-dim" strokeWidth={1.5} />
          <p className="mt-3 text-lg font-bold">Không có sản phẩm phù hợp</p>
          <p className="mt-1 text-text-muted">Thử từ khoá khác hoặc chọn danh mục khác nhé.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-3 lg:grid-cols-4">
          {products.map((p) => (
            <StoreProductCard
              key={p.id}
              product={p}
              onClick={() => trackEvent("click", { category: p.category })}
              onCart={() => {
                addToCart({ id: p.id, name: p.name, brand: p.brand, price_vnd: p.price_vnd, image_url: p.image_url });
                trackEvent("cart", { category: p.category });
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
