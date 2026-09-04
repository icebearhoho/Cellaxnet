"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Star, ShoppingBag, CheckCircle2, Loader2, PackageOpen, Flame, MessageSquareText, ChevronLeft, ChevronRight, Images, Send } from "lucide-react";
import { getStoreProduct, isOutOfStock, submitStoreReview, type StoreProduct, type StoreReview } from "@/lib/features";
import { trackEvent } from "@/lib/journey-track";
import { addToCart } from "@/lib/cart";
import { StoreImage } from "@/components/store/store-image";
import { StoreProductCard } from "@/components/store/store-product-card";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

const VND = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});

export default function StoreDetailPage() {
  const t = useT();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params?.id;

  const [product, setProduct] = useState<StoreProduct | null>(null);
  const [similar, setSimilar] = useState<StoreProduct[]>([]);
  const [reviews, setReviews] = useState<StoreReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [added, setAdded] = useState(false);
  const [selectedImage, setSelectedImage] = useState(0);
  // behaviour signals: dwell time + max scroll depth
  const [dwell, setDwell] = useState(0);
  const [scroll, setScroll] = useState(0);
  const reviewsRef = useRef<HTMLDivElement | null>(null);
  const reviewTrackedRef = useRef(false);

  // Dwell timer (seconds on the product page).
  useEffect(() => {
    const t = setInterval(() => setDwell((d) => d + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // Max scroll depth (%).
  useEffect(() => {
    const onScroll = () => {
      const h = document.documentElement.scrollHeight - window.innerHeight;
      const pct = h > 0 ? Math.round((window.scrollY / h) * 100) : 0;
      setScroll((s) => Math.max(s, Math.min(100, pct)));
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Emotion-aware flash-sale nudge driven by real dwell + scroll: lingering on
  // the page (and browsing it fully) without buying signals hesitation.
  const hesitating = !added && dwell >= 20 && scroll >= 40;
  const nudgeDiscount = dwell >= 40 ? 10 : 5;

  function doAddToCart(p: StoreProduct) {
    addToCart({ id: p.id, name: p.name, brand: p.brand, price_vnd: p.price_vnd, image_url: p.image_url });
    trackEvent("cart", { category: p.category });
    setAdded(true);
  }

  const recordReviewRead = useCallback(() => {
    if (!product || reviewTrackedRef.current) return;
    reviewTrackedRef.current = true;
    trackEvent("review", { category: product.category });
  }, [product]);

  useEffect(() => {
    if (!id) return;
    let alive = true;
    setLoading(true);
    getStoreProduct(id).then((res) => {
      if (!alive) return;
      const p = res?.product ?? null;
      reviewTrackedRef.current = false;
      setProduct(p);
      setSelectedImage(0);
      setSimilar(res?.similar ?? []);
      setReviews(res?.review_items ?? []);
      setLoading(false);
      if (p) trackEvent("view", { category: p.category });
    });
    return () => {
      alive = false;
    };
  }, [id]);

  // Reading reviews is a real purchase-intent signal — track it once the
  // section has actually sat in view for a bit, not on a drive-by scroll past.
  useEffect(() => {
    if (!product || reviews.length === 0) return;
    const el = reviewsRef.current;
    if (!el) return;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !reviewTrackedRef.current) {
          timer = setTimeout(() => {
            recordReviewRead();
          }, 1500);
        } else if (timer) {
          clearTimeout(timer);
          timer = null;
        }
      },
      { threshold: 0.5 },
    );
    observer.observe(el);
    return () => {
      observer.disconnect();
      if (timer) clearTimeout(timer);
    };
  }, [product, reviews.length, recordReviewRead]);
  if (loading) {
    return (
      <div className="grid place-items-center rounded-lg border border-border bg-surface py-24 text-text-muted">
        <Loader2 className="h-6 w-6 animate-spin" />
        <p className="mt-3 text-sm">{t("Đang tải sản phẩm…")}</p>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="grid place-items-center rounded-lg border border-border bg-surface py-24 text-center">
        <PackageOpen className="h-8 w-8 text-text-dim" strokeWidth={1.5} />
        <p className="mt-3 text-lg font-bold">{t("Không tìm thấy sản phẩm")}</p>
        <Link href="/shop/store" className="mt-4 inline-flex items-center gap-1.5 font-medium text-accent">
          <ArrowLeft className="h-4 w-4" /> {t("Về cửa hàng")}
        </Link>
      </div>
    );
  }

  const attributes = Object.entries(product.attributes ?? {});
  const soldOut = isOutOfStock(product);
  const gallery = product.image_urls?.length ? product.image_urls : [product.image_url];
  const activeImage = gallery[selectedImage] ?? gallery[0];

  function moveImage(delta: number) {
    setSelectedImage((current) => (current + delta + gallery.length) % gallery.length);
  }

  return (
    <div className="space-y-8">
      <Link href="/shop/store" className="inline-flex items-center gap-1.5 text-sm font-medium text-text-muted hover:text-text">
        <ArrowLeft className="h-4 w-4" strokeWidth={1.5} /> {t("Về cửa hàng")}
      </Link>

      <div className="grid gap-10 md:grid-cols-2">
        {/* Product gallery: exact Tiki hero + clearly-labelled curated demo imagery. */}
        <div className="space-y-3">
          <div className="group relative">
            <StoreImage
              key={activeImage}
              name={`${product.name} — ảnh ${selectedImage + 1}`}
              category={product.category}
              src={activeImage}
              iconClassName="h-1/4 w-1/4"
            />
            {gallery.length > 1 && (
              <>
                <button
                  type="button"
                  aria-label={t("Ảnh trước")}
                  onClick={() => moveImage(-1)}
                  className="absolute left-3 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-full border border-white/70 bg-black/45 text-white transition-colors hover:bg-black/65"
                >
                  <ChevronLeft className="h-5 w-5" />
                </button>
                <button
                  type="button"
                  aria-label={t("Ảnh tiếp theo")}
                  onClick={() => moveImage(1)}
                  className="absolute right-3 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-full border border-white/70 bg-black/45 text-white transition-colors hover:bg-black/65"
                >
                  <ChevronRight className="h-5 w-5" />
                </button>
              </>
            )}
            <span className="mono absolute bottom-3 right-3 rounded-full bg-black/55 px-2.5 py-1 text-2xs text-white">
              {selectedImage + 1} / {gallery.length}
            </span>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1" aria-label={t("Thư viện ảnh sản phẩm")}>
            {gallery.map((src, index) => (
              <button
                key={src}
                type="button"
                aria-label={`Xem ảnh ${index + 1}`}
                aria-current={selectedImage === index}
                onClick={() => setSelectedImage(index)}
                className={cn(
                  "group w-16 shrink-0 rounded-xl border p-0.5 transition-colors sm:w-[4.5rem]",
                  selectedImage === index ? "border-accent" : "border-transparent hover:border-border",
                )}
              >
                <StoreImage
                  name={`${product.name} — ảnh thu nhỏ ${index + 1}`}
                  category={product.category}
                  src={src}
                  className="border-0"
                  iconClassName="h-6 w-6"
                />
              </button>
            ))}
          </div>
          <p className="flex items-center gap-1.5 text-2xs text-text-dim">
            <Images className="h-3.5 w-3.5" strokeWidth={1.5} />
            {gallery.length} ảnh minh hoạ · giá bán chính xác hiển thị trong phần thông tin sản phẩm
          </p>
        </div>

        {/* Info */}
        <div className="space-y-5">
          <div>
            <span className="text-xs font-medium uppercase tracking-wider text-text-dim">{product.category}</span>
            <h1 className="mt-2 text-3xl font-extrabold">{product.name}</h1>
            <div className="mt-1 text-sm uppercase tracking-wider text-text-dim">{product.brand}</div>
          </div>

          <div className="flex items-baseline gap-1.5">
            <span className="mono text-2xl text-text" data-tnum>
              {VND.format(product.price_vnd).replace(/\s*₫/g, "")}
            </span>
            <span className="mono text-base text-text-dim">₫</span>
          </div>

          <div className="flex items-center gap-1.5 text-sm text-text-muted">
            <Star className="h-4 w-4 fill-warning stroke-warning" />
            <span className="mono text-text">{product.rating.toFixed(1)}</span>
            <span className="mono text-text-dim">({product.reviews.toLocaleString()} đánh giá)</span>
            {reviews.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  recordReviewRead();
                  reviewsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
                className="ml-2 border-b border-accent font-medium text-accent"
              >
                {t("Đọc đánh giá")}
              </button>
            )}
          </div>

          {attributes.length > 0 && (
            <div className="flex flex-wrap gap-4 border-y border-border py-4 text-xs">
              {attributes.map(([k, v]) => (
                <span key={k} className="inline-flex items-center gap-1.5 text-text-muted">
                  <span className="text-text-dim">{k}</span>
                  <span className="text-text">{v}</span>
                </span>
              ))}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
            <div className="text-2xs uppercase tracking-wider text-text-dim">
              SKU <span className="mono text-text-muted">{product.sku}</span>
            </div>
            {/* stock === null means "unknown", not "sold out" — say nothing then. */}
            {soldOut ? (
              <span className="rounded-full bg-text px-2.5 py-0.5 text-2xs font-semibold text-bg">
                {t("Hết hàng")}
              </span>
            ) : product.stock !== null ? (
              <span
                className={cn(
                  "rounded-full px-2.5 py-0.5 text-2xs font-semibold",
                  product.stock <= 5 ? "bg-warning/15 text-warning" : "bg-success/10 text-success",
                )}
              >
                {product.stock <= 5 ? `Chỉ còn ${product.stock}` : `Còn ${product.stock} sản phẩm`}
              </span>
            ) : null}
          </div>

          {/* Emotion-aware flash-sale nudge, driven by real dwell/scroll */}
          {hesitating && (
            <div className="rounded-xl border border-warning/50 bg-warning/5 px-4 py-3">
              <div className="flex items-center gap-2 text-sm font-medium text-warning">
                <Flame className="h-4 w-4" strokeWidth={1.5} /> Ưu đãi dành cho bạn · giảm thêm {nudgeDiscount}%
              </div>
              <p className="mt-1 text-xs text-text-muted">
                {t("Đặt trong 10 phút để nhận thêm ưu đãi.")}
              </p>
            </div>
          )}

          {soldOut ? (
            <div className="inline-flex items-center gap-2 rounded-full border border-border-strong bg-surface-2 px-5 py-3 text-sm font-semibold text-text-muted">
              <PackageOpen className="h-4 w-4" /> {t("Sản phẩm đã hết hàng")}
            </div>
          ) : (
            <div className="flex flex-wrap gap-3 pt-2">
              <button
                type="button"
                onClick={() => doAddToCart(product)}
                className={cn(
                  "inline-flex items-center gap-2 rounded-full border px-6 py-3 text-sm font-semibold transition-colors",
                  added
                    ? "border-success/40 text-success"
                    : "border-border-strong text-text hover:border-accent hover:text-accent",
                )}
              >
                {added ? <CheckCircle2 className="h-4 w-4" /> : <ShoppingBag className="h-4 w-4" />}
                {added ? "Đã thêm vào giỏ" : t("Thêm vào giỏ")}
              </button>
              <button
                type="button"
                onClick={() => {
                  // Straight to checkout, like any real store. The `purchase`
                  // event now fires when the order is actually placed in the
                  // cart, not on this click — so Journey records a real sale.
                  doAddToCart(product);
                  router.push("/shop/cart");
                }}
                className="inline-flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-accent-hover"
              >
                Mua ngay
              </button>
              <Link
                href="/shop/cart"
                className="inline-flex items-center gap-2 border-b border-transparent px-1 py-3 text-sm font-medium text-text-muted transition-colors hover:border-accent hover:text-text"
              >
                {t("Xem giỏ →")}
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Reviews */}
      <section ref={reviewsRef} className="border-t border-border pt-10">
        <h2 className="mb-6 flex items-center gap-2 text-2xl font-bold">
          <MessageSquareText className="h-5 w-5 text-text-dim" strokeWidth={1.5} />
          {t("Đánh giá sản phẩm")}
          <span className="mono text-base font-normal text-text-dim">({reviews.length})</span>
        </h2>
        {reviews.length > 0 && (
          <div className="mb-8 divide-y divide-border">
            {reviews.map((r, i) => (
              <div key={i} className="py-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-text">{r.author}</span>
                  <span className="text-2xs text-text-dim">
                    {r.days_ago === 0 ? "Hôm nay" : `${r.days_ago} ngày trước`}
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-0.5">
                  {Array.from({ length: 5 }).map((_, j) => (
                    <Star
                      key={j}
                      className={cn(
                        "h-3.5 w-3.5",
                        j < r.rating ? "fill-warning stroke-warning" : "fill-none stroke-border",
                      )}
                    />
                  ))}
                </div>
                <p className="mt-2 text-sm text-text-muted">{r.text}</p>
              </div>
            ))}
          </div>
        )}
        <ReviewForm
          productId={product.id}
          onPublished={(review) => setReviews((rs) => [review, ...rs])}
        />
      </section>

      {/* Similar products */}
      {similar.length > 0 && (
        <section className="border-t border-border pt-10">
          <h2 className="mb-6 text-2xl font-bold">{t("Sản phẩm tương tự")}</h2>
          <div className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-3 lg:grid-cols-4">
            {similar.map((p) => (
              <StoreProductCard
                key={p.id}
                product={p}
                onClick={() => trackEvent("click", { category: p.category })}
                onCart={() => doAddToCart(p)}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function ReviewForm({
  productId, onPublished,
}: {
  productId: string;
  onPublished: (review: StoreReview) => void;
}) {
  const t = useT();
  const [authorName, setAuthorName] = useState("");
  const [rating, setRating] = useState(5);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState<{ ok: boolean; message: string } | null>(null);

  async function submit() {
    if (busy || !authorName.trim() || !text.trim()) return;
    setBusy(true);
    setBanner(null);
    const res = await submitStoreReview(productId, authorName.trim(), rating, text.trim());
    if (!res) {
      setBanner({ ok: false, message: t("Không gửi được đánh giá. Hãy thử lại.") });
      setBusy(false);
      return;
    }
    setBanner({ ok: res.status === "published", message: res.message });
    if (res.status === "published" && res.review) {
      onPublished(res.review);
    }
    setText("");
    setBusy(false);
  }

  return (
    <div className="rounded-lg border border-border bg-bg-alt p-6">
      <h3 className="text-sm font-medium text-text">{t("Viết đánh giá")}</h3>
      <div className="mt-4 space-y-3">
        <input
          value={authorName}
          onChange={(e) => setAuthorName(e.target.value)}
          placeholder={t("Tên của bạn")}
          className="h-11 w-full rounded-xl border border-border bg-surface px-4 text-sm text-text outline-none focus:border-accent"
        />
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          placeholder={t("Chia sẻ cảm nhận của bạn về sản phẩm…")}
          className="w-full resize-none rounded-xl border border-border bg-surface px-4 py-3 text-sm text-text outline-none focus:border-accent"
        />
        <div className="flex flex-wrap items-center gap-3">
          <div className="inline-flex items-center gap-0.5">
            {[1, 2, 3, 4, 5].map((r) => (
              <button key={r} type="button" onClick={() => setRating(r)} aria-label={`${r} sao`}>
                <Star className={cn("h-4.5 w-4.5", r <= rating ? "fill-warning stroke-warning" : "fill-none stroke-border")} />
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={submit}
            disabled={busy || !authorName.trim() || !text.trim()}
            className="ml-auto inline-flex items-center gap-1.5 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
          >
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" strokeWidth={1.5} />}
            Gửi đánh giá
          </button>
        </div>
        {banner && (
          <p className={cn("text-xs", banner.ok ? "text-success" : "text-warning")}>{banner.message}</p>
        )}
      </div>
    </div>
  );
}
