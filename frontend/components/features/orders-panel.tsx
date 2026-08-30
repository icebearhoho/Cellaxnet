"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, PackageOpen, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  getAllOrders,
  setOrderStatus,
  type Order,
  type OrderStatus,
} from "@/lib/features";
import { cn } from "@/lib/utils";

const VND = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});
const fmt = (n: number) => VND.format(n).replace(/\s*₫/g, "") + "₫";

const STATUS: Record<OrderStatus, { label: string; cls: string }> = {
  pending: { label: "Chờ xử lý", cls: "bg-warning/10 text-warning" },
  paid: { label: "Đã thanh toán", cls: "bg-info/10 text-info" },
  shipped: { label: "Đã xuất hàng", cls: "bg-success/10 text-success" },
  cancelled: { label: "Đã hủy", cls: "bg-danger/10 text-danger" },
};

// What a seller can move an order to from where it is now.
const NEXT: Record<OrderStatus, OrderStatus[]> = {
  pending: ["paid", "cancelled"],
  paid: ["shipped", "cancelled"],
  shipped: [],
  cancelled: [],
};

export function OrdersPanel() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [busyNo, setBusyNo] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setOrders(await getAllOrders());
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function advance(orderNo: string, status: OrderStatus) {
    setBusyNo(orderNo);
    const updated = await setOrderStatus(orderNo, status);
    if (updated) {
      setOrders((prev) =>
        (prev ?? []).map((o) => (o.order_no === orderNo ? updated : o)),
      );
    }
    setBusyNo(null);
  }

  const revenue = (orders ?? [])
    .filter((o) => o.status === "paid" || o.status === "shipped")
    .reduce((sum, o) => sum + o.total_vnd, 0);

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Đơn hàng</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            Đơn thật do khách đặt từ cửa hàng. Chưa có cổng thanh toán — người bán
            xác nhận trạng thái thủ công.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="muted">{orders?.length ?? 0} đơn</Badge>
          {orders && orders.length > 0 && (
            <Badge variant="live">{fmt(revenue)}</Badge>
          )}
          <Button variant="secondary" size="sm" onClick={load} disabled={loading}>
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            Làm mới
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading && !orders ? (
          <p className="text-sm text-text-muted">Đang tải đơn…</p>
        ) : orders === null ? (
          <p className="text-sm text-danger">
            Không tải được đơn. Kiểm tra kết nối backend rồi thử lại.
          </p>
        ) : orders.length === 0 ? (
          <p className="flex items-center gap-2 text-sm text-text-muted">
            <PackageOpen className="h-4 w-4" /> Chưa có đơn nào. Đặt thử một đơn từ
            cửa hàng để thấy nó ở đây.
          </p>
        ) : (
          <div className="space-y-3">
            {orders.map((o) => {
              const s = STATUS[o.status];
              return (
                <div key={o.order_no} className="rounded-lg border border-border p-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="mono text-sm font-semibold">{o.order_no}</span>
                    <span
                      className={cn(
                        "rounded-full px-2.5 py-0.5 text-2xs font-semibold",
                        s.cls,
                      )}
                    >
                      {s.label}
                    </span>
                    <span className="text-xs text-text-muted">{o.customer_name}</span>
                    {o.channel && <Badge variant="muted">{o.channel}</Badge>}
                    {o.demo_order && <Badge variant="muted">đơn mẫu</Badge>}
                    <span className="text-xs text-text-dim">
                      {new Date(o.created_at).toLocaleString("vi-VN")}
                    </span>
                    <span className="mono ml-auto text-sm font-semibold">
                      {fmt(o.total_vnd)}
                    </span>
                  </div>

                  <div className="mt-2 text-xs text-text-muted">
                    {o.items
                      .map((i) => `${i.product_name} ×${i.qty}`)
                      .join(" · ")}
                  </div>

                  {!o.demo_order && NEXT[o.status].length > 0 && (
                    <div className="mt-3 flex gap-2">
                      {NEXT[o.status].map((next) => (
                        <Button
                          key={next}
                          size="sm"
                          variant={next === "cancelled" ? "secondary" : "primary"}
                          disabled={busyNo === o.order_no}
                          onClick={() => advance(o.order_no, next)}
                        >
                          {STATUS[next].label}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
