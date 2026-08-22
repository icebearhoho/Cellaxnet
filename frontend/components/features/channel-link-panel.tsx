"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Link2, Loader2, CheckCircle2, AlertTriangle, ExternalLink, Unplug, Info,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  getChannelLink, connectChannel, disconnectChannel, syncChannel,
  type ChannelLinkStatus,
} from "@/lib/features";
import { cn } from "@/lib/utils";

/** Status encoding — never colour alone: each pairs an icon with a label. */
const STATUS: Record<
  ChannelLinkStatus["status"],
  { label: string; variant: "success" | "warning" | "danger" | "muted"; hint: string }
> = {
  connected: {
    label: "Đã kết nối", variant: "success",
    hint: "Bấm “Lấy đơn hàng” để kéo đơn của các sàn về",
  },
  pending: {
    label: "Đang chờ", variant: "warning", hint: "Đang xử lý",
  },
  error: {
    label: "Lỗi", variant: "danger", hint: "Lần kết nối gần nhất thất bại",
  },
  disconnected: {
    label: "Chưa nối", variant: "muted", hint: "Sẵn sàng — bấm Kết nối",
  },
  not_configured: {
    label: "Chưa cấu hình", variant: "muted",
    hint: "Chưa khai khoá API của cửa hàng",
  },
};

function compactVnd(n: number) {
  if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(1) + " tỷ";
  if (n >= 1_000_000) return Math.round(n / 1_000_000) + " tr";
  if (n >= 1_000) return Math.round(n / 1_000) + "k";
  return String(n);
}

export function ChannelLinkPanel() {
  const [data, setData] = useState<ChannelLinkStatus | null>(null);
  const [busy, setBusy] = useState<"connect" | "sync" | "disconnect" | null>(null);
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setData(await getChannelLink());
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function connect() {
    setBusy("connect");
    setNotice(null);
    // No redirect: KiotViet authenticates server-to-server, so the answer
    // comes back on this same request.
    const r = await connectChannel();
    setNotice(
      r.ok
        ? { ok: true, text: "Đã kết nối KiotViet — bấm “Lấy đơn hàng” để kéo đơn về." }
        : { ok: false, text: r.message },
    );
    setBusy(null);
    void load();
  }

  async function sync() {
    setBusy("sync");
    setNotice(null);
    const r = await syncChannel();
    setNotice(
      r.ok
        ? {
            ok: true,
            text: `Lấy được ${r.data.total_orders} đơn trong ${r.data.days} ngày `
              + `từ ${r.data.marketplaces.length} kênh — kế hoạch nhập hàng giờ `
              + `dùng số này thay cho phần bạn tự khai.`,
          }
        : { ok: false, text: r.message },
    );
    setBusy(null);
    void load();
  }

  async function disconnect() {
    setBusy("disconnect");
    await disconnectChannel();
    setBusy(null);
    setNotice({ ok: true, text: "Đã ngắt kết nối và xoá token" });
    void load();
  }

  const s = data ? STATUS[data.status] : null;
  const connected = data?.status === "connected";

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Kết nối tài khoản bán hàng</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            Nối qua <strong>KiotViet</strong> — nền tảng bán hàng đa kênh đã
            được Shopee, Lazada và TikTok Shop cấp quyền sẵn. Một liên kết mang
            về đơn của cả ba sàn, mỗi đơn có ghi rõ đến từ kênh nào.
          </p>
        </div>
        {s ? <Badge variant={s.variant}>{s.label}</Badge> : null}
      </CardHeader>

      <CardContent className="space-y-3">
        {notice ? (
          <div
            className={cn(
              "flex items-start gap-2 rounded-md border px-3 py-2 text-xs",
              notice.ok
                ? "border-success/40 bg-success/5 text-success"
                : "border-danger/40 bg-danger/5 text-danger",
            )}
          >
            {notice.ok ? (
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            ) : (
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            )}
            <span>{notice.text}</span>
          </div>
        ) : null}

        {loading ? (
          <p className="py-4 text-center text-xs text-text-muted">Đang tải…</p>
        ) : !data ? (
          <p className="py-4 text-center text-xs text-danger">
            Không gọi được backend.
          </p>
        ) : (
          <>
            <div className="rounded-lg border border-border bg-surface-2 p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-medium">{data.name}</p>
                  <p className="mt-0.5 text-2xs text-text-muted">{s?.hint}</p>
                  {data.retailer ? (
                    <p className="mt-0.5 text-2xs text-text-dim">
                      Cửa hàng: {data.retailer}
                    </p>
                  ) : null}
                </div>

                <div className="flex flex-wrap gap-2">
                  {connected ? (
                    <>
                      <Button size="sm" onClick={sync} disabled={busy !== null}>
                        {busy === "sync" ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="h-3.5 w-3.5" />
                        )}
                        Lấy đơn hàng
                      </Button>
                      <Button
                        variant="secondary" size="sm"
                        onClick={disconnect} disabled={busy !== null}
                      >
                        <Unplug className="h-3.5 w-3.5" /> Ngắt
                      </Button>
                    </>
                  ) : (
                    <Button
                      size="sm" onClick={connect}
                      disabled={busy !== null || !data.configured}
                      title={data.configured ? undefined : "Chưa khai khoá API của cửa hàng"}
                    >
                      {busy === "connect" ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Link2 className="h-3.5 w-3.5" />
                      )}
                      Kết nối
                    </Button>
                  )}
                </div>
              </div>

              {/* Which marketplaces one link can carry — shown before any sync
                  so the seller knows what to expect. */}
              <div className="mt-2.5 flex flex-wrap items-center gap-1.5 border-t border-border pt-2.5">
                <span className="text-2xs text-text-muted">Mang về đơn từ:</span>
                {data.supported.map((name) => (
                  <Badge key={name} variant="muted">{name}</Badge>
                ))}
              </div>

              {data.last_error ? (
                <p className="mt-2 break-words text-2xs text-danger">{data.last_error}</p>
              ) : null}
            </div>

            {/* After a sync: what each marketplace actually contributed. */}
            {data.marketplaces.length ? (
              <div>
                <div className="flex items-baseline justify-between">
                  <p className="text-xs font-medium">
                    Đơn hàng {data.sync_days} ngày gần nhất
                  </p>
                  <p className="text-2xs text-text-dim">
                    tổng {data.total_orders} đơn
                    {data.last_synced_at
                      ? ` · lấy lúc ${new Date(data.last_synced_at).toLocaleString("vi-VN")}`
                      : ""}
                  </p>
                </div>
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="text-text-muted">
                      <tr className="border-b border-border text-left">
                        <th className="py-1.5 pr-3 font-medium">Sàn</th>
                        <th className="py-1.5 pr-3 text-right font-medium">Đơn</th>
                        <th className="py-1.5 pr-3 text-right font-medium">Đơn/ngày</th>
                        <th className="py-1.5 text-right font-medium">Doanh thu</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.marketplaces.map((m) => (
                        <tr key={m.channel} className="border-b border-border/50">
                          <td className="py-1.5 pr-3 font-medium">{m.name}</td>
                          <td className="py-1.5 pr-3 text-right tabular-nums">{m.orders}</td>
                          <td className="py-1.5 pr-3 text-right tabular-nums">
                            {m.daily_orders}
                          </td>
                          <td className="py-1.5 text-right tabular-nums">
                            {m.revenue_vnd ? compactVnd(m.revenue_vnd) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}
          </>
        )}

        <div className="flex items-start gap-2 border-t border-border pt-3 text-2xs text-text-dim">
          <Info className="mt-0.5 h-3 w-3 shrink-0" />
          <span>
            Khoá API lấy trong <strong>{data?.credentials_hint}</strong> của cửa
            hàng bạn. Hệ thống chỉ lưu số đơn và doanh thu tổng hợp, không lưu
            thông tin khách hàng, và ngắt kết nối được bất cứ lúc nào.{" "}
            {data ? (
              <a
                href={data.docs_url} target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-0.5 text-accent hover:underline"
              >
                Tài liệu API <ExternalLink className="h-2.5 w-2.5" />
              </a>
            ) : null}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
