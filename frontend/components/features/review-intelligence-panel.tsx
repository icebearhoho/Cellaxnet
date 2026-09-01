"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronsUpDown, Loader2, Search, Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  getProductReviews, getStoreProducts,
  type ProductReviews, type ScoredReview, type StoreProduct,
} from "@/lib/features";
import { cn } from "@/lib/utils";

const TONE = {
  positive: { label: "Tích cực", chip: "bg-success/10 text-success", dot: "bg-success" },
  neutral: { label: "Trung tính", chip: "bg-warning/10 text-warning", dot: "bg-warning" },
  negative: { label: "Tiêu cực", chip: "bg-danger/10 text-danger", dot: "bg-danger" },
} as const;

type Tone = keyof typeof TONE;

const FILTERS = [
  { key: "all" as const, label: "Tất cả" },
  { key: "negative" as const, label: "Tiêu cực" },
  { key: "neutral" as const, label: "Trung tính" },
  { key: "positive" as const, label: "Tích cực" },
];

export function ReviewIntelligencePanel() {
  return <ProductReviewsPanel />;
}

function ProductReviewsPanel() {
  const [products, setProducts] = useState<StoreProduct[]>([]);
  const [productId, setProductId] = useState<string | null>(null);
  const [data, setData] = useState<ProductReviews | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tone, setTone] = useState<"all" | Tone>("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let active = true;
    void getStoreProducts().then((response) => {
      if (!active) return;
      const list = response?.products ?? [];
      setProducts(list);
      setProductId((current) => current ?? list[0]?.id ?? null);
    });
    return () => { active = false; };
  }, []);

  const load = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    const result = await getProductReviews(id);
    if (result) {
      setData(result);
    } else {
      setData(null);
      setError("Không lấy được đánh giá của sản phẩm này.");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (productId) void load(productId);
  }, [productId, load]);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = data?.reviews ?? [];
    if (tone !== "all") list = list.filter((r) => r.sentiment === tone);
    if (q) {
      list = list.filter(
        (r) => r.text.toLowerCase().includes(q) || r.author.toLowerCase().includes(q),
      );
    }
    return list;
  }, [data, tone, query]);

  useEffect(() => { setTone("all"); setQuery(""); }, [productId]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Trải nghiệm khách hàng</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Chọn một sản phẩm để đọc toàn bộ đánh giá, đã phân loại sẵn theo cảm xúc.
        </p>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* The product is the unit. Scoring one pasted sentence answered a
            question the seller could already answer; what they cannot do by
            hand is read every review on a product and see the shape of it. */}
        <div>
          <label htmlFor="review-product" className="text-sm font-medium text-text">
            Sản phẩm
          </label>
          <div className="relative mt-2">
            <select
              id="review-product"
              value={productId ?? ""}
              onChange={(e) => setProductId(e.target.value)}
              disabled={products.length === 0}
              className="h-10 w-full appearance-none rounded-lg border border-border bg-surface px-3 pr-9 text-sm text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50"
            >
              {products.length === 0 && <option>Đang tải danh sách sản phẩm…</option>}
              {products.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <ChevronsUpDown
              className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-dim"
              aria-hidden="true"
            />
          </div>
        </div>

        {error ? (
          <p className="text-sm text-danger" role="alert">{error}</p>
        ) : loading || !data ? (
          <p className="flex items-center gap-2 py-8 text-sm text-text-muted">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Đang đọc đánh giá…
          </p>
        ) : data.total === 0 ? (
          <p className="py-8 text-center text-sm text-text-muted">
            Sản phẩm này chưa có đánh giá nào.
          </p>
        ) : (
          <>
            {/* The shape of the feedback, before any of the words. */}
            <div className="grid gap-4 rounded-xl border border-border bg-bg-alt p-4 sm:grid-cols-[160px_1fr]">
              <div className="flex items-center gap-3 border-b border-border pb-4 sm:border-b-0 sm:border-r sm:pb-0 sm:pr-4">
                <Star className="h-5 w-5 shrink-0 text-warning" aria-hidden="true" />
                <div>
                  <p className="tnum text-2xl font-bold leading-none text-text">
                    {data.avg_rating}
                  </p>
                  <p className="mt-1 text-xs text-text-muted">
                    {data.total} đánh giá
                  </p>
                </div>
              </div>
              <div className="min-w-0">
                <div className="flex h-3 w-full overflow-hidden rounded-full bg-surface-3">
                  {(["positive", "neutral", "negative"] as const).map((key) =>
                    data[key] > 0 ? (
                      <span
                        key={key}
                        className={cn("h-full border-r-2 border-bg-alt last:border-r-0", TONE[key].dot)}
                        style={{ width: `${(data[key] / data.total) * 100}%` }}
                        aria-hidden="true"
                      />
                    ) : null,
                  )}
                </div>
                <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5">
                  {(["positive", "neutral", "negative"] as const).map((key) => (
                    <li key={key} className="flex items-center gap-2 text-xs text-text-muted">
                      <span className={cn("h-2.5 w-2.5 rounded-full", TONE[key].dot)} aria-hidden="true" />
                      {TONE[key].label}
                      <span className="tnum text-text-dim">{data[key]}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="inline-flex flex-wrap gap-1.5">
                {FILTERS.map((f) => {
                  const count = f.key === "all" ? data.total : data[f.key];
                  return (
                    <button
                      key={f.key}
                      type="button"
                      onClick={() => setTone(f.key)}
                      disabled={count === 0}
                      className={cn(
                        "rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                        "disabled:cursor-not-allowed disabled:opacity-40",
                        tone === f.key
                          ? f.key === "all" ? "bg-accent/15 text-accent" : TONE[f.key].chip
                          : "bg-surface-2 text-text-muted hover:text-text",
                      )}
                    >
                      {f.label} <span className="tnum opacity-70">{count}</span>
                    </button>
                  );
                })}
              </div>
              <div className="relative sm:w-56">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-dim" />
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Tìm trong đánh giá…"
                  className="h-9 pl-9 text-xs"
                  aria-label="Tìm trong đánh giá"
                />
              </div>
            </div>

            {shown.length === 0 ? (
              <p className="py-8 text-center text-sm text-text-muted">
                Không có đánh giá nào khớp bộ lọc này.
              </p>
            ) : (
              <ul className="space-y-2">
                {shown.map((review, index) => (
                  <ReviewRow key={`${review.author}-${index}`} review={review} />
                ))}
              </ul>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ReviewRow({ review }: { review: ScoredReview }) {
  const tone = TONE[review.sentiment];
  return (
    <li className="rounded-lg border border-border bg-surface-2/40 p-4">
      <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
        <span className="text-sm font-medium text-text">{review.author}</span>
        <span className="tnum flex items-center gap-0.5 text-xs text-warning">
          {review.rating}
          <Star className="h-3 w-3 fill-current" aria-hidden="true" />
        </span>
        <span className={cn("rounded-md px-1.5 py-0.5 text-2xs font-medium", tone.chip)}>
          {tone.label}
        </span>
        {review.from_customers && (
          <span className="rounded-md bg-accent/10 px-1.5 py-0.5 text-2xs font-medium text-accent">
            Khách gửi
          </span>
        )}
        {review.days_ago !== null && (
          <span className="tnum ml-auto text-2xs text-text-dim">
            {review.days_ago} ngày trước
          </span>
        )}
      </div>
      <p className="mt-2 text-sm leading-6 text-text-muted">{review.text}</p>
    </li>
  );
}
