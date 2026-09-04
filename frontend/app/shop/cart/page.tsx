"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Minus, Plus, Trash2, ShoppingCart, CheckCircle2, Loader2 } from "lucide-react";
import {
  getCart, setQty, removeItem, clearCart, cartTotal, cartCount, CART_EVENT, type CartItem,
} from "@/lib/cart";
import { trackEvent } from "@/lib/journey-track";
import { StoreImage } from "@/components/store/store-image";
import { Input } from "@/components/ui/input";
import { checkout as placeOrder, type Order } from "@/lib/features";
import { ApiClientError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useT } from "@/lib/i18n";

const VND = new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND", maximumFractionDigits: 0 });
const fmt = (n: number) => VND.format(n).replace(/\s*₫/g, "") + "₫";

export default function CartPage() {
  const t = useT();
  const { user } = useAuth();
  const [items, setItems] = useState<CartItem[]>([]);
  const [order, setOrder] = useState<Order | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const sync = () => setItems(getCart());
    sync();
    window.addEventListener(CART_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(CART_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  // Prefill from the signed-in account; guests type it in.
  useEffect(() => {
    if (user) {
      setName((n) => n || user.name || user.email);
      setEmail((e) => e || user.email);
    }
  }, [user]);

  async function submit() {
    if (items.length === 0 || busy || !name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const placed = await placeOrder({
        items: items.map((it) => ({ product_id: it.id, qty: it.qty })),
        customerName: name.trim(),
        email: email.trim() || undefined,
      });
      // Feed Journey: one purchase event per line.
      items.forEach(() => trackEvent("purchase"));
      setOrder(placed);
      clearCart();
    } catch (err) {
      // 409 = a line went out of stock between adding and checking out.
      setError(
        err instanceof ApiClientError
          ? (err.envelope.error?.message ?? t("Không đặt được hàng."))
          : t("Không kết nối được máy chủ. Hãy thử lại."),
      );
    } finally {
      setBusy(false);
    }
  }

  if (order) {
    return (
      <div className="grid place-items-center rounded-lg border border-success/40 bg-success/5 py-16 text-center">
        <CheckCircle2 className="h-10 w-10 text-success" />
        <p className="mt-4 text-2xl font-bold">{t("Đặt hàng thành công!")}</p>
        <p className="mono mt-2 text-lg text-text">{order.order_no}</p>
        <p className="mt-1 text-text-muted">
          {order.items.length} sản phẩm · tổng{" "}
          <span className="mono font-semibold text-text">{fmt(order.total_vnd)}</span>
        </p>
        <p className="mt-3 max-w-sm text-xs text-text-dim">
          {t("Đơn đang ở trạng thái")} <span className="font-semibold">{t("chờ xử lý")}</span> {t("— hệ thống chưa tích hợp cổng thanh toán, người bán sẽ xác nhận thủ công.")}
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link href="/shop/store" className="inline-flex items-center gap-1.5 rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent-hover">
            {t("Tiếp tục mua sắm")}
          </Link>
          {user && (
            <Link href="/shop/orders" className="inline-flex items-center gap-1.5 rounded-full border border-border-strong px-6 py-3 text-sm font-semibold text-text transition-colors hover:border-accent hover:text-accent">
              {t("Xem đơn của tôi")}
            </Link>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between border-b border-border pb-6">
        <div className="flex items-center gap-2.5">
          <ShoppingCart className="h-5 w-5 text-text-dim" strokeWidth={1.5} />
          <h1 className="text-3xl font-extrabold">{t("Giỏ hàng")}</h1>
        </div>
        <Link href="/shop/store" className="inline-flex items-center gap-1.5 text-sm font-medium text-text-muted hover:text-text">
          <ArrowLeft className="h-4 w-4" strokeWidth={1.5} /> {t("Về cửa hàng")}
        </Link>
      </div>

      {items.length === 0 ? (
        <div className="grid place-items-center rounded-lg border border-border bg-surface py-20 text-center">
          <ShoppingCart className="h-8 w-8 text-text-dim" strokeWidth={1.5} />
          <p className="mt-3 text-lg font-bold">{t("Giỏ hàng trống")}</p>
          <p className="mt-1 text-text-muted">{t("Vào cửa hàng chọn vài món nhé!")}</p>
          <Link href="/shop/store" className="mt-5 inline-flex items-center gap-1.5 rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent-hover">
            {t("Đi mua sắm")}
          </Link>
        </div>
      ) : (
        <div className="grid gap-8 lg:grid-cols-3">
          {/* Items */}
          <div className="divide-y divide-border lg:col-span-2">
            {items.map((it) => (
              <div key={it.id} className="flex gap-4 py-4 first:pt-0">
                <div className="w-24 shrink-0">
                  <StoreImage name={it.name} category="" src={it.image_url} iconClassName="h-1/3 w-1/3" />
                </div>
                <div className="flex min-w-0 flex-1 flex-col">
                  <Link href={`/shop/store/${it.id}`} className="truncate text-sm text-text hover:text-accent">
                    {it.name}
                  </Link>
                  <div className="truncate text-2xs uppercase tracking-wider text-text-dim">{it.brand}</div>
                  <div className="mono mt-1 text-sm text-text">{fmt(it.price_vnd)}</div>
                  <div className="mt-auto flex items-center gap-3 pt-2">
                    <div className="inline-flex items-center rounded-full border border-border">
                      <button onClick={() => setQty(it.id, it.qty - 1)} className="grid h-8 w-8 place-items-center text-text-muted hover:text-text" aria-label={t("Giảm")}>
                        <Minus className="h-3.5 w-3.5" />
                      </button>
                      <span className="mono w-8 text-center text-sm text-text">{it.qty}</span>
                      <button onClick={() => setQty(it.id, it.qty + 1)} className="grid h-8 w-8 place-items-center text-text-muted hover:text-text" aria-label={t("Tăng")}>
                        <Plus className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <button onClick={() => removeItem(it.id)} className="inline-flex items-center gap-1 text-2xs text-text-dim hover:text-danger">
                      <Trash2 className="h-3.5 w-3.5" strokeWidth={1.5} /> {t("Xóa")}
                    </button>
                  </div>
                </div>
                <div className="mono shrink-0 self-center text-sm text-text">{fmt(it.price_vnd * it.qty)}</div>
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="card-surface h-fit rounded-lg border p-6">
            <div className="text-sm font-medium text-text">{t("Tóm tắt đơn")}</div>
            <div className="mt-3 flex justify-between text-sm text-text-muted">
              <span>{t("Số lượng")}</span><span className="mono text-text">{cartCount()} sản phẩm</span>
            </div>
            <div className="mt-2 flex justify-between text-sm text-text-muted">
              <span>{t("Tạm tính")}</span><span className="mono text-text">{fmt(cartTotal())}</span>
            </div>
            <div className="mt-3 flex items-baseline justify-between border-t border-border pt-3">
              <span className="font-medium text-text">{t("Tổng cộng")}</span>
              <span className="mono text-lg text-accent">{fmt(cartTotal())}</span>
            </div>

            <div className="mt-5 space-y-2.5 border-t border-border pt-5">
              <label htmlFor="cust-name" className="block text-xs font-medium text-text-muted">
                {t("Người nhận")}
              </label>
              <Input
                id="cust-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t("Tên của bạn")}
              />
              <label htmlFor="cust-email" className="block text-xs font-medium text-text-muted">
                {t("Email")} <span className="font-normal text-text-dim">{t("(không bắt buộc)")}</span>
              </label>
              <Input
                id="cust-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ban@email.com"
              />
            </div>

            {error && (
              <p className="mt-3 rounded-xl border border-danger/30 bg-danger/5 px-3 py-2 text-xs text-danger">
                {error}
              </p>
            )}

            <button
              onClick={submit}
              disabled={busy || !name.trim()}
              className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-full bg-accent px-5 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-accent-hover disabled:opacity-50"
            >
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              Đặt hàng ({cartCount()} món)
            </button>
            {!user && (
              <p className="mt-2.5 text-center text-2xs text-text-dim">
                Mua không cần đăng nhập.{" "}
                <Link href="/login" className="font-semibold text-accent">
                  {t("Đăng nhập")}
                </Link>{" "}
                để lưu lịch sử đơn.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
