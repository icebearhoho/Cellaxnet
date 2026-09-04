"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Loader2, PackageOpen, ReceiptText } from "lucide-react";
import { getMyOrders, type Order, type OrderStatus } from "@/lib/features";
import { useAuth } from "@/lib/auth-context";
import { useMounted } from "@/lib/hooks/use-mounted";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n";

const VND = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});
const fmt = (n: number) => VND.format(n).replace(/\s*₫/g, "") + "₫";

const STATUS: Record<OrderStatus, { label: string; cls: string }> = {
  pending: { label: "Chờ xử lý", cls: "bg-warning/10 text-warning" },
  paid: { label: "Đã thanh toán", cls: "bg-info/10 text-info" },
  shipped: { label: "Đã giao", cls: "bg-success/10 text-success" },
  cancelled: { label: "Đã hủy", cls: "bg-danger/10 text-danger" },
};

export default function MyOrdersPage() {
  const t = useT();
  const { user } = useAuth();
  const mounted = useMounted();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setOrders(await getMyOrders());
    setLoading(false);
  }, []);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  // Order history is the one buyer feature that needs an account — a guest
  // order has no owner to scope the query by.
  if (mounted && !user) {
    return (
      <div className="grid place-items-center rounded-lg border border-border bg-surface py-20 text-center">
        <ReceiptText className="h-8 w-8 text-text-dim" />
        <p className="mt-3 text-lg font-bold">{t("Cần đăng nhập")}</p>
        <p className="mt-1 max-w-sm text-text-muted">
          {t("Đơn đặt khi chưa đăng nhập không gắn với tài khoản nào, nên không tra được ở đây — hãy dùng mã đơn đã hiện lúc đặt.")}
        </p>
        <Link
          href="/login?next=%2Fshop%2Forders"
          className="mt-6 rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
        >
          {t("Đăng nhập")}
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="border-b border-border pb-6">
        <h1 className="text-3xl font-extrabold">{t("Đơn của tôi")}</h1>
        <p className="mt-1 text-text-muted">{t("Lịch sử đặt hàng của tài khoản này.")}</p>
      </div>

      {!mounted || loading ? (
        <div className="grid place-items-center rounded-lg border border-border bg-surface py-20 text-text-muted">
          <Loader2 className="h-6 w-6 animate-spin" />
          <p className="mt-3 text-sm">{t("Đang tải đơn…")}</p>
        </div>
      ) : orders === null ? (
        <div className="grid place-items-center rounded-lg border border-border bg-surface py-20 text-center">
          <PackageOpen className="h-8 w-8 text-text-dim" />
          <p className="mt-3 text-lg font-bold">{t("Chưa tải được đơn")}</p>
          <p className="mt-1 text-text-muted">{t("Kiểm tra kết nối rồi thử lại.")}</p>
        </div>
      ) : orders.length === 0 ? (
        <div className="grid place-items-center rounded-lg border border-border bg-surface py-20 text-center">
          <PackageOpen className="h-8 w-8 text-text-dim" />
          <p className="mt-3 text-lg font-bold">{t("Chưa có đơn nào")}</p>
          <Link
            href="/shop/store"
            className="mt-5 rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
          >
            {t("Đi mua sắm")}
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((o) => {
            const s = STATUS[o.status];
            return (
              <div key={o.order_no} className="card-surface rounded-lg border p-5">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="mono text-sm font-semibold text-text">{o.order_no}</span>
                  <span className={cn("rounded-full px-2.5 py-0.5 text-2xs font-semibold", s.cls)}>
                    {t(s.label)}
                  </span>
                  <span className="text-xs text-text-dim">
                    {new Date(o.created_at).toLocaleString("vi-VN")}
                  </span>
                  <span className="mono ml-auto text-sm font-semibold text-text">
                    {fmt(o.total_vnd)}
                  </span>
                </div>

                <div className="mt-4 divide-y divide-border border-t border-border">
                  {o.items.map((it) => (
                    <div
                      key={it.product_id}
                      className="flex items-center gap-3 py-2.5 text-sm"
                    >
                      <Link
                        href={`/shop/store/${it.product_id}`}
                        className="min-w-0 flex-1 truncate text-text hover:text-accent"
                      >
                        {it.product_name}
                      </Link>
                      <span className="mono text-xs text-text-dim">×{it.qty}</span>
                      <span className="mono w-28 text-right text-text-muted">
                        {fmt(it.line_total_vnd)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
