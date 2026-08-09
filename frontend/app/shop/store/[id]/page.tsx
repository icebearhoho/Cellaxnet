"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, Star, ShoppingBag, CheckCircle2, Loader2, PackageOpen, Flame, MessageSquareText, ChevronLeft, ChevronRight, Images, Send } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { getStoreProduct, submitStoreReview, type StoreProduct, type StoreReview } from "@/lib/features";
import { trackEvent } from "@/lib/journey-track";
import { addToCart } from "@/lib/cart";
import { StoreImage } from "@/components/store/store-image";
import { StoreProductCard } from "@/components/store/store-product-card";
import { cn } from "@/lib/utils";

const VND = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});

export default function StoreDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;

  const [product, setProduct] = useState<StoreProduct | null>(null);
  const [similar, setSimilar] = useState<StoreProduct[]>([]);
  const [reviews, setReviews] = useState<StoreReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [ordered, setOrdered] = useState(false);
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
  const hesitating = !ordered && !added && dwell >= 20 && scroll >= 40;
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
      <div className="grid place-items-center rounded-3xl border border-border bg-surface py-24 text-text-muted">
        <Loader2 className="h-6 w-6 animate-spin" />
        <p className="mt-3 text-sm">Đang tải sản phẩm…</p>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="grid place-items-center rounded-3xl border border-border bg-surface py-24 text-center">
        <PackageOpen className="h-8 w-8 text-text-dim" />
        <p className="mt-3 text-lg font-extrabold">Không tìm thấy sản phẩm</p>
        <Link href="/shop/store" className="mt-4 inline-flex items-center gap-1.5 font-bold text-accent">
          <ArrowLeft className="h-4 w-4" /> Về cửa hàng
        </Link>
      </div>
    );
  }

  const attributes = Object.entries(product.attributes ?? {});
  const gallery = product.image_urls?.length ? product.image_urls : [product.image_url];
  const activeImage = gallery[selectedImage] ?? gallery[0];

  function moveImage(delta: number) {
    setSelectedImage((current) => (current + delta + gallery.length) % gallery.length);
  }

  return (
    <div className="space-y-8">
      <Link href="/shop/store" className="inline-flex items-center gap-1.5 text-sm font-bold text-accent">
        <ArrowLeft className="h-4 w-4" /> Về cửa hàng
      </Link>

      <div className="grid gap-8 md:grid-cols-2">
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
                  aria-label="Ảnh trước"
                  onClick={() => moveImage(-1)}
                  className="absolute left-3 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-full border border-white/70 bg-black/45 text-white shadow-sm backdrop-blur transition-colors hover:bg-black/65"
                >
                  <ChevronLeft className="h-5 w-5" />
                </button>
                <button
                  type="button"
                  aria-label="Ảnh tiếp theo"
                  onClick={() => moveImage(1)}
                  className="absolute right-3 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-full border border-white/70 bg-black/45 text-white shadow-sm backdrop-blur transition-colors hover:bg-black/65"
                >
                  <ChevronRight className="h-5 w-5" />
                </button>
              </>
            )}
            <span className="mono absolute bottom-3 right-3 rounded-full bg-black/55 px-2.5 py-1 text-2xs text-white backdrop-blur">
              {selectedImage + 1} / {gallery.length}
            </span>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1" aria-label="Thư viện ảnh sản phẩm">
            {gallery.map((src, index) => (
              <button
                key={src}
                type="button"
                aria-label={`Xem ảnh ${index + 1}`}
                aria-current={selectedImage === index}
                onClick={() => setSelectedImage(index)}
                className={cn(
                  "group w-16 shrink-0 rounded-xl border-2 p-0.5 transition-colors sm:w-[4.5rem]",
                  selectedImage === index ? "border-accent" : "border-transparent hover:border-border",
                )}
              >
                <StoreImage
                  name={`${product.name} — ảnh thu nhỏ ${index + 1}`}
                  category={product.category}
                  src={src}
                  className="rounded-lg border-0"
                  iconClassName="h-6 w-6"
                />
              </button>
            ))}
          </div>
          <p className="flex items-center gap-1.5 text-2xs text-text-dim">
            <Images className="h-3.5 w-3.5" />
            {gallery.length} ảnh minh hoạ · giá bán chính xác hiển thị trong phần thông tin sản phẩm
          </p>
        </div>

        {/* Info */}
        <div className="space-y-4">
          <div>
            <Badge variant="info">{product.category}</Badge>
            <h1 className="mt-2 text-2xl font-extrabold tracking-tight">{product.name}</h1>
            <div className="mt-1 text-sm uppercase tracking-wider text-text-dim">{product.brand}</div>
          </div>

          <div className="flex items-baseline gap-1.5">
            <span className="mono text-3xl font-extrabold text-text" data-tnum>
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
                className="ml-2 font-semibold text-accent hover:underline"
              >
                Đọc đánh giá
              </button>
            )}
          </div>

          {attributes.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {attributes.map(([k, v]) => (
                <span
                  key={k}
                  className="inline-flex items-center gap-1 rounded-full border border-border bg-bg-alt px-3 py-1 text-xs text-text-muted"
                >
                  <span className="text-text-dim">{k}:</span>
                  <span className="font-semibold text-text">{v}</span>
                </span>
              ))}
            </div>
          )}

          <div className="text-2xs uppercase tracking-wider text-text-dim">
            SKU <span className="mono text-text-muted">{product.sku}</span>
          </div>

          {/* Emotion-aware flash-sale nudge, driven by real dwell/scroll */}
          {hesitating && (
            <div className="rounded-2xl border border-warning/50 bg-warning/10 px-4 py-3">
              <div className="flex items-center gap-2 text-sm font-bold text-warning">
                <Flame className="h-4 w-4" /> Ưu đãi dành cho bạn · giảm thêm {nudgeDiscount}%
              </div>
              <p className="mt-1 text-xs text-text-muted">
                Đặt trong 10 phút để nhận thêm ưu đãi.
              </p>
            </div>
          )}

          {ordered ? (
            <div className="inline-flex items-center gap-2 rounded-2xl border border-success/40 bg-success/10 px-4 py-3 text-sm font-bold text-success">
              <CheckCircle2 className="h-5 w-5" /> Đã đặt hàng!
            </div>
          ) : (
            <div className="flex flex-wrap gap-3 pt-2">
              <button
                type="button"
                onClick={() => doAddToCart(product)}
                className={cn(
                  "inline-flex items-center gap-2 rounded-2xl border px-5 py-2.5 text-sm font-bold transition-colors",
                  added
                    ? "border-success/40 bg-success/10 text-success"
                    : "border-accent/40 bg-accent/10 text-accent hover:bg-accent hover:text-white",
                )}
              >
                {added ? <CheckCircle2 className="h-4 w-4" /> : <ShoppingBag className="h-4 w-4" />}
                {added ? "Đã thêm vào giỏ" : "Thêm vào giỏ"}
              </button>
              <button
                type="button"
                onClick={() => {
                  trackEvent("purchase", { category: product.category });
                  setOrdered(true);
                }}
                className="inline-flex items-center gap-2 rounded-2xl bg-accent px-5 py-2.5 text-sm font-bold text-white transition-transform hover:-translate-y-0.5"
              >
                Mua ngay
              </button>
              <Link
                href="/shop/cart"
                className="inline-flex items-center gap-2 rounded-2xl border border-border px-5 py-2.5 text-sm font-bold text-text-muted transition-colors hover:border-text hover:text-text"
              >
                Xem giỏ →
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Reviews */}
      <section ref={reviewsRef}>
        <h2 className="mb-4 flex items-center gap-2 text-lg font-extrabold">
          <MessageSquareText className="h-5 w-5 text-text-dim" />
          Đánh giá sản phẩm
          <span className="mono text-sm font-normal text-text-dim">({reviews.length})</span>
        </h2>
        {reviews.length > 0 && (
          <div className="mb-6 space-y-3">
            {reviews.map((r, i) => (
              <div key={i} className="rounded-2xl border border-border bg-surface p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-text">{r.author}</span>
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
        <section>
          <h2 className="mb-4 text-lg font-extrabold">Sản phẩm tương tự</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
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
      setBanner({ ok: false, message: "Không gửi được đánh giá. Hãy thử lại." });
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
    <div className="rounded-2xl border border-border bg-bg-alt p-4">
      <h3 className="text-sm font-bold text-text">Viết đánh giá</h3>
      <div className="mt-3 space-y-3">
        <input
          value={authorName}
          onChange={(e) => setAuthorName(e.target.value)}
          placeholder="Tên của bạn"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-text outline-none focus:border-accent"
        />
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          placeholder="Chia sẻ cảm nhận của bạn về sản phẩm…"
          className="w-full resize-none rounded-md border border-border bg-surface px-3 py-2 text-sm text-text outline-none focus:border-accent"
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
            className="ml-auto inline-flex items-center gap-1.5 rounded-xl bg-accent px-4 py-2 text-sm font-bold text-white transition-opacity disabled:opacity-50"
          >
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
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
