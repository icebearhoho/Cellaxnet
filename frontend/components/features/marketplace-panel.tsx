"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle, CheckCircle2, Clock, ExternalLink, Info, Link2, Loader2,
  Plus, RefreshCw, ShieldAlert, Store, Unplug,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  beginShopConnect, createSellerAccount, disconnectShop, getMarketplacePlatforms,
  getSellerAccounts, getShopConnections, syncShop,
  type MarketplaceId, type MarketplacePlatform, type SellerAccount,
  type ShopConnection, type ShopStatus,
} from "@/lib/features";
import { cn } from "@/lib/utils";

/**
 * Status encoding pairs an icon with a label in every case — colour alone
 * excludes anyone who cannot distinguish the hues, and "expired" vs "revoked"
 * is exactly the distinction a seller needs to act on.
 */
const STATUS: Record<
  ShopStatus,
  { variant: "success" | "warning" | "danger" | "muted"; icon: typeof CheckCircle2; hint: string }
> = {
  connected: {
    variant: "success", icon: CheckCircle2,
    hint: "Đang hoạt động — bấm Đồng bộ để kéo dữ liệu về",
  },
  pending: {
    variant: "warning", icon: Clock,
    hint: "Đã gửi người bán sang sàn, chưa thấy quay lại",
  },
  expired: {
    variant: "warning", icon: Clock,
    hint: "Token hết hạn và không làm mới được — cần cấp quyền lại",
  },
  revoked: {
    variant: "danger", icon: ShieldAlert,
    hint: "Người bán đã thu hồi quyền từ phía sàn",
  },
  error: {
    variant: "danger", icon: AlertTriangle,
    hint: "Lần đồng bộ gần nhất thất bại — xem chi tiết lỗi",
  },
  disconnected: {
    variant: "muted", icon: Unplug,
    hint: "Đã ngắt — dữ liệu đã đồng bộ vẫn được giữ lại",
  },
};

function relativeTime(iso: string | null): string {
  if (!iso) return "chưa bao giờ";
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "vừa xong";
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} giờ trước`;
  return `${Math.floor(hours / 24)} ngày trước`;
}

export function MarketplacePanel() {
  const [platforms, setPlatforms] = useState<MarketplacePlatform[]>([]);
  const [accounts, setAccounts] = useState<SellerAccount[]>([]);
  const [shops, setShops] = useState<ShopConnection[]>([]);
  const [activeAccount, setActiveAccount] = useState<number | null>(null);

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");

  const refresh = useCallback(async () => {
    const [p, a, s] = await Promise.all([
      getMarketplacePlatforms(), getSellerAccounts(), getShopConnections(),
    ]);
    if (p) setPlatforms(p);
    if (a) {
      setAccounts(a);
      setActiveAccount((cur) => cur ?? (a.length ? a[0].id : null));
    }
    if (s) setShops(s);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // The marketplace sends the seller back to this page with the outcome on the
  // query string, since the callback lands in a browser rather than in fetch().
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const result = params.get("connect");
    if (!result) return;
    if (result === "ok") {
      setNotice({ kind: "ok", text: "Kết nối shop thành công." });
    } else {
      setNotice({
        kind: "err",
        text: params.get("message") || "Kết nối không thành công.",
      });
    }
    window.history.replaceState({}, "", window.location.pathname);
    void refresh();
  }, [refresh]);

  async function handleCreateAccount() {
    if (!newName.trim()) return;
    setBusy("account");
    const created = await createSellerAccount({ name: newName.trim() });
    setBusy(null);
    if (created) {
      setNewName("");
      setCreating(false);
      setActiveAccount(created.id);
      setNotice({ kind: "ok", text: `Đã tạo tài khoản bán hàng “${created.name}”.` });
      await refresh();
    } else {
      setNotice({ kind: "err", text: "Không tạo được tài khoản bán hàng." });
    }
  }

  async function handleConnect(platform: MarketplaceId) {
    if (activeAccount === null) return;
    setBusy(platform);
    const res = await beginShopConnect(activeAccount, platform);
    setBusy(null);
    if (res.ok) {
      // Full navigation, not a popup: the marketplace refuses to render its
      // consent screen inside a frame.
      window.location.href = res.authorizeUrl;
    } else {
      setNotice({ kind: "err", text: res.message });
    }
  }

  async function handleSync(shopId: number) {
    setBusy(`sync-${shopId}`);
    const res = await syncShop(shopId);
    setBusy(null);
    setNotice(
      res.ok
        ? {
            kind: res.data.errors.length ? "err" : "ok",
            text: res.data.errors.length
              ? `Đồng bộ xong nhưng có lỗi: ${res.data.errors.join("; ")}`
              : `Đã đồng bộ ${res.data.products} sản phẩm, ${res.data.orders} đơn hàng.`,
          }
        : { kind: "err", text: res.message },
    );
    await refresh();
  }

  async function handleDisconnect(shopId: number) {
    setBusy(`off-${shopId}`);
    await disconnectShop(shopId);
    setBusy(null);
    await refresh();
  }

  const visibleShops = activeAccount === null
    ? shops
    : shops.filter((s) => s.seller_account_id === activeAccount);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 py-10 text-text-dim">
          <Loader2 className="h-4 w-4 animate-spin" /> Đang tải…
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {notice && (
        <div
          role="status"
          className={cn(
            "flex items-start gap-2 rounded-lg border px-3 py-2 text-sm",
            notice.kind === "ok"
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
              : "border-red-500/30 bg-red-500/10 text-red-200",
          )}
        >
          {notice.kind === "ok"
            ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            : <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />}
          <span>{notice.text}</span>
        </div>
      )}

      {/* --- seller accounts ------------------------------------------- */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Store className="h-4 w-4" /> Tài khoản bán hàng
          </CardTitle>
          <Button size="sm" variant="outline" onClick={() => setCreating((v) => !v)}>
            <Plus className="mr-1 h-3.5 w-3.5" /> Tạo mới
          </Button>
        </CardHeader>
        <CardContent className="space-y-3">
          {creating && (
            <div className="flex flex-wrap gap-2">
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Tên tài khoản bán hàng"
                className="min-w-48 flex-1 rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
              />
              <Button size="sm" onClick={handleCreateAccount} disabled={busy === "account"}>
                {busy === "account" && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}
                Lưu
              </Button>
            </div>
          )}

          {accounts.length === 0 ? (
            <p className="text-sm text-text-dim">
              Chưa có tài khoản bán hàng. Tạo một cái trước khi kết nối shop.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {accounts.map((a) => (
                <button
                  key={a.id}
                  onClick={() => setActiveAccount(a.id)}
                  className={cn(
                    "rounded-lg border px-3 py-2 text-left text-sm transition",
                    activeAccount === a.id
                      ? "border-primary bg-primary/10"
                      : "border-border hover:border-primary/50",
                  )}
                >
                  <div className="font-medium">{a.name}</div>
                  <div className="text-xs text-text-dim">
                    {a.shop_count} shop · {a.business_type === "company" ? "Doanh nghiệp" : "Cá nhân"}
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* --- connect a new shop ----------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Link2 className="h-4 w-4" /> Kết nối shop trên sàn
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-2 sm:grid-cols-3">
            {platforms.map((p) => {
              const blocked = !p.implemented || !p.configured || activeAccount === null;
              return (
                <div key={p.platform} className="rounded-lg border border-border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{p.display_name}</span>
                    {!p.implemented && <Badge variant="muted">Chưa hỗ trợ</Badge>}
                    {p.implemented && !p.configured && (
                      <Badge variant="warning">Chưa cấu hình</Badge>
                    )}
                    {p.implemented && p.configured && <Badge variant="success">Sẵn sàng</Badge>}
                  </div>

                  {/* Say exactly which key is missing — "not configured" alone
                      leaves the reader guessing which of several to go find. */}
                  {p.implemented && !p.configured && p.missing_settings.length > 0 && (
                    <p className="mt-1 text-xs text-text-dim">
                      Thiếu {p.missing_settings.join(", ")}
                    </p>
                  )}

                  <Button
                    size="sm"
                    className="mt-2 w-full"
                    disabled={blocked || busy === p.platform}
                    onClick={() => handleConnect(p.platform)}
                  >
                    {busy === p.platform && <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />}
                    Kết nối
                  </Button>

                  {p.implemented && !p.configured && p.console_url && (
                    <a
                      href={p.console_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                    >
                      Lấy khoá ứng dụng <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              );
            })}
          </div>

          <div className="flex items-start gap-2 rounded-lg border border-border bg-surface/50 px-3 py-2 text-xs text-text-dim">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              Mỗi sàn cấp khoá ứng dụng riêng — khoá của Shopee không dùng được cho
              Lazada hay TikTok Shop. Sàn nào chưa có khoá thì nút Kết nối bị khoá,
              vì bấm vào cũng không thể hoàn tất.
            </span>
          </div>
        </CardContent>
      </Card>

      {/* --- connected shops -------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Shop đã kết nối {visibleShops.length > 0 && `(${visibleShops.length})`}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {visibleShops.length === 0 ? (
            <p className="text-sm text-text-dim">
              Chưa có shop nào được kết nối.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase text-text-dim">
                  <tr>
                    <th className="pb-2 pr-3">Shop</th>
                    <th className="pb-2 pr-3">Sàn</th>
                    <th className="pb-2 pr-3">Trạng thái</th>
                    <th className="pb-2 pr-3">Đồng bộ gần nhất</th>
                    <th className="pb-2 pr-3 text-right">Dữ liệu</th>
                    <th className="pb-2 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleShops.map((shop) => {
                    const meta = STATUS[shop.status] ?? STATUS.error;
                    const Icon = meta.icon;
                    return (
                      <tr key={shop.id} className="border-t border-border align-top">
                        <td className="py-2 pr-3">
                          <div className="font-medium">
                            {shop.shop_name || `Shop ${shop.external_shop_id}`}
                          </div>
                          <div className="text-xs text-text-dim">
                            ID {shop.external_shop_id} · {shop.region}
                          </div>
                        </td>
                        <td className="py-2 pr-3">{shop.platform_label}</td>
                        <td className="py-2 pr-3">
                          <Badge variant={meta.variant} className="gap-1">
                            <Icon className="h-3 w-3" /> {shop.status_label}
                          </Badge>
                          <div className="mt-1 max-w-56 text-xs text-text-dim">
                            {shop.last_error || meta.hint}
                          </div>
                        </td>
                        <td className="py-2 pr-3 text-text-dim">
                          {relativeTime(shop.last_synced_at)}
                        </td>
                        <td className="py-2 pr-3 text-right tabular-nums">
                          <div>{shop.products.toLocaleString("vi-VN")} SP</div>
                          <div className="text-xs text-text-dim">
                            {shop.orders.toLocaleString("vi-VN")} đơn
                          </div>
                        </td>
                        <td className="py-2 text-right">
                          <div className="flex justify-end gap-1">
                            <Button
                              size="sm" variant="outline"
                              disabled={busy === `sync-${shop.id}` || shop.status === "disconnected"}
                              onClick={() => handleSync(shop.id)}
                            >
                              {busy === `sync-${shop.id}`
                                ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                : <RefreshCw className="h-3.5 w-3.5" />}
                            </Button>
                            <Button
                              size="sm" variant="ghost"
                              disabled={busy === `off-${shop.id}`}
                              onClick={() => handleDisconnect(shop.id)}
                            >
                              <Unplug className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
