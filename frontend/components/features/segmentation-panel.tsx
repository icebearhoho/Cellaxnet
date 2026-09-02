"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  ChartNoAxesColumnIncreasing, ChevronDown, Lightbulb, Mail, MapPin, Phone, Search, ShoppingBag,
  Store, UserMinus, UserRound, UserRoundX, UsersRound, type LucideIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { DEMO_CUSTOMERS } from "@/lib/demo-customers";
import { cn } from "@/lib/utils";

const PERSONAS = [
  "Active Buyers",
  "Sellers (listing & selling activity)",
  "At-risk / Low-activity Users",
  "Dormant / Ghost Users",
] as const;

type Persona = (typeof PERSONAS)[number];
type PersonaMeta = {
  label: string;
  shortDescription: string;
  action: ReactNode;
  icon: LucideIcon;
  tone: string;
  bar: string;
  badge: "success" | "live" | "warning" | "danger";
};

const PERSONA_META: Record<Persona, PersonaMeta> = {
  "Active Buyers": {
    label: "Khách hàng tích cực",
    shortDescription: "Nhóm còn tương tác nhiều nhất: có lượt thích, wishlist và lịch sử mua.",
    action: "Cung cấp thẻ loyalty/VIP và gợi ý sản phẩm theo lịch sử mua hoặc yêu thích.",
    icon: ShoppingBag,
    tone: "border-success/30 bg-success/[0.06] text-success",
    bar: "bg-success",
    badge: "success",
  },
  "Sellers (listing & selling activity)": {
    label: "Người bán",
    shortDescription: "Có lịch sử đăng bán hoặc bán được hàng, nhưng phần lớn đã lâu không quay lại.",
    action: (
      <>
        Hướng dẫn dùng <span className="font-semibold text-text">Cải thiện cửa hàng</span> để rà soát lại gian hàng.
        Sau đó xin phản hồi để biết họ đang vướng ở đâu và giới thiệu đúng tính năng hỗ trợ tiếp theo.
      </>
    ),
    icon: Store,
    tone: "border-accent/30 bg-accent/[0.06] text-accent",
    bar: "bg-accent",
    badge: "live",
  },
  "At-risk / Low-activity Users": {
    label: "Có nguy cơ rời bỏ",
    shortDescription: "Vẫn còn hiện diện nhưng mức tương tác đang giảm.",
    action: "Can thiệp sớm bằng thông báo nhắc nhớ và ưu đãi nhỏ có thời hạn ngắn.",
    icon: UserMinus,
    tone: "border-warning/30 bg-warning/[0.06] text-warning",
    bar: "bg-warning",
    badge: "warning",
  },
  "Dormant / Ghost Users": {
    label: "Không còn hoạt động",
    shortDescription: "Đã ngừng tương tác trong thời gian dài.",
    action: "Chạy chiến dịch win-back qua email/SMS với ưu đãi quay lại đủ mạnh nhưng tần suất vừa phải.",
    icon: UserRoundX,
    tone: "border-danger/30 bg-danger/[0.06] text-danger",
    bar: "bg-danger",
    badge: "danger",
  },
};

/** Nhóm đông nhất có ~130 khách. Đổ hết một lượt thì trang dài lê thê, còn
 *  nhốt trong khung cuộn riêng lại để thừa một mảng trắng bên dưới — phân
 *  trang cho danh sách cao vừa phải và trôi theo trang như mọi nội dung khác. */
const PAGE_SIZE = 12;

export function SegmentationPanel() {
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);

  const segmentCounts = useMemo(
    () => Object.fromEntries(PERSONAS.map((persona) => [
      persona,
      DEMO_CUSTOMERS.filter((customer) => customer.persona === persona).length,
    ])) as Record<Persona, number>,
    [],
  );

  const customers = useMemo(() => {
    if (!selectedPersona) return [];
    const keyword = query.trim().toLocaleLowerCase("vi");
    return DEMO_CUSTOMERS.filter((customer) => {
      if (customer.persona !== selectedPersona) return false;
      if (!keyword) return true;
      return [customer.name, customer.phone, customer.email, customer.city]
        .some((value) => value.toLocaleLowerCase("vi").includes(keyword));
    });
  }, [query, selectedPersona]);

  const selectedMeta = selectedPersona ? PERSONA_META[selectedPersona] : null;

  const pageCount = Math.max(1, Math.ceil(customers.length / PAGE_SIZE));
  const current = Math.min(page, pageCount - 1);
  const visible = customers.slice(current * PAGE_SIZE, current * PAGE_SIZE + PAGE_SIZE);

  useEffect(() => { setPage(0); }, [query, selectedPersona]);

  function selectPersona(persona: Persona) {
    setSelectedPersona(persona);
    setQuery("");
  }

  return (
    <section aria-labelledby="customer-segments-title" className="space-y-5">
      <Card className="overflow-hidden">
        <CardHeader className="border-b border-border bg-gradient-to-r from-accent/[0.07] to-accent-2/[0.05] p-5 sm:p-6">
          <div className="min-w-0">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-accent">
              <UsersRound className="h-4 w-4" aria-hidden="true" /> Phân khúc khách hàng
            </div>
            <CardTitle id="customer-segments-title" className="text-lg sm:text-xl">
              Bạn muốn xem nhóm khách hàng nào?
            </CardTitle>
            <p className="mt-1.5 max-w-3xl text-sm leading-6 text-text-muted">
              Chọn một phân khúc để xem toàn bộ khách hàng thuộc nhóm, thông tin liên hệ, hành vi và lịch sử hoạt động.
            </p>
          </div>
          <Badge variant="muted" className="hidden shrink-0 sm:inline-flex">
            {DEMO_CUSTOMERS.length} khách hàng
          </Badge>
        </CardHeader>
        <CardContent className="p-5 sm:p-6">
          <div className="mb-5 grid gap-4 rounded-2xl border border-border bg-bg-alt p-4 lg:grid-cols-[220px_1fr] lg:p-5">
            <div className="flex items-center gap-4 border-b border-border pb-4 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-5">
              <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-accent/10 text-accent">
                <ChartNoAxesColumnIncreasing className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-text-muted">Tổng quy mô</p>
                <p className="tnum mt-1 text-3xl font-bold tracking-tight text-text">{DEMO_CUSTOMERS.length}</p>
                <p className="text-xs text-text-muted">khách hàng đã phân nhóm</p>
              </div>
            </div>

            <div className="min-w-0">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-text">Phân bổ khách hàng</p>
                <p className="text-xs text-text-muted">4 phân khúc</p>
              </div>
              <div
                className="mt-3 flex h-4 w-full overflow-hidden rounded-full bg-surface-3"
                role="img"
                aria-label="Phân bổ gồm 85 khách hàng tích cực, 42 người bán, 44 khách hàng có nguy cơ rời bỏ và 129 khách hàng không còn hoạt động"
              >
                {PERSONAS.map((persona) => (
                  <span
                    key={persona}
                    className={cn("h-full border-r-2 border-bg-alt last:border-r-0", PERSONA_META[persona].bar)}
                    style={{ width: `${(segmentCounts[persona] / DEMO_CUSTOMERS.length) * 100}%` }}
                    aria-hidden="true"
                  />
                ))}
              </div>
              <ul className="mt-4 grid grid-cols-2 gap-x-5 gap-y-2 sm:grid-cols-4" aria-label="Chú thích phân khúc">
                {PERSONAS.map((persona) => {
                  const meta = PERSONA_META[persona];
                  return (
                    <li key={persona} className="flex min-w-0 items-center gap-2">
                      <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", meta.bar)} aria-hidden="true" />
                      <span className="min-w-0 truncate text-xs text-text-muted" title={meta.label}>{meta.label}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4" role="group" aria-label="Chọn phân khúc khách hàng">
            {PERSONAS.map((persona) => {
              const meta = PERSONA_META[persona];
              const Icon = meta.icon;
              const isSelected = selectedPersona === persona;
              const count = segmentCounts[persona];
              return (
                <button
                  key={persona}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => selectPersona(persona)}
                  className={cn(
                    "min-h-40 cursor-pointer rounded-2xl border p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2",
                    isSelected
                      ? `${meta.tone} ring-1 ring-current`
                      : "border-border bg-surface hover:border-border-strong hover:bg-bg-alt",
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className={cn("grid h-10 w-10 place-items-center rounded-xl", isSelected ? "bg-surface/80" : meta.tone)}>
                      <Icon className="h-5 w-5" aria-hidden={true} />
                    </span>
                    <span className="flex items-center gap-1.5 text-text">
                      <UserRound className="h-5 w-5 text-text-muted" aria-hidden="true" />
                      <span className="tnum text-2xl font-bold">{count}</span>
                    </span>
                  </div>
                  <p className="mt-4 font-semibold text-text">{meta.label}</p>
                  <p className="mt-1 text-sm leading-5 text-text-muted">{meta.shortDescription}</p>
                  <p className={cn("mt-3 text-xs font-semibold", isSelected ? "text-current" : "text-accent")}>Chọn để xem danh sách</p>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {!selectedPersona || !selectedMeta ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center p-8 text-center">
            <div className="mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-accent/10 text-accent">
              <UsersRound className="h-7 w-7" aria-hidden="true" />
            </div>
            <p className="font-semibold text-text">Chưa chọn phân khúc</p>
            <p className="mt-2 max-w-md text-sm leading-6 text-text-muted">
              Chọn một trong bốn nhóm phía trên để mở danh sách khách hàng tương ứng.
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <CardHeader className="gap-4 border-b border-border p-5 sm:flex-row sm:items-center sm:p-6">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <CardTitle className="text-lg">{selectedMeta.label}</CardTitle>
                <Badge variant={selectedMeta.badge}>{segmentCounts[selectedPersona]} khách hàng</Badge>
              </div>
            </div>
            <div className="relative w-full shrink-0 sm:w-80">
              <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-dim" aria-hidden="true" />
              <Input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Tìm tên, SĐT, email, thành phố…"
                className="pl-10"
                aria-label={`Tìm trong nhóm ${selectedMeta.label}`}
              />
            </div>
          </CardHeader>

          <CardContent className="space-y-5 p-5 sm:p-6">
            <div className="rounded-2xl border border-border bg-bg-alt p-4">
              <p className="flex items-center gap-2 text-sm font-semibold text-text">
                <Lightbulb className="h-4 w-4 text-warning" aria-hidden="true" /> Hành động đề xuất
              </p>
              <p className="mt-1.5 text-sm leading-6 text-text-muted">{selectedMeta.action}</p>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-text" aria-live="polite">
                Hiển thị {customers.length} trên {segmentCounts[selectedPersona]} khách hàng
              </p>
              {query && <p className="text-xs text-text-muted">Kết quả cho “{query}”</p>}
            </div>

            {customers.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border p-10 text-center">
                <Search className="mx-auto h-6 w-6 text-text-dim" aria-hidden="true" />
                <p className="mt-3 font-semibold text-text">Không tìm thấy khách hàng</p>
                <p className="mt-1 text-sm text-text-muted">Thử tên, số điện thoại, email hoặc thành phố khác.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 items-start gap-3 xl:grid-cols-2" aria-label={`Danh sách ${selectedMeta.label}`}>
                {visible.map((customer) => (
                  <article key={customer.id} className="rounded-2xl border border-border bg-surface p-4 transition-colors hover:border-border-strong">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="truncate font-semibold text-text" title={customer.name}>{customer.name}</h3>
                        <p className="mt-1 text-xs text-text-muted">{customer.gender} · {customer.age} tuổi · {customer.id}</p>
                      </div>
                      <Badge variant={selectedMeta.badge} className="shrink-0">{selectedMeta.label}</Badge>
                    </div>

                    <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
                      <div className="flex min-w-0 items-center gap-2 text-text-muted">
                        <Phone className="h-4 w-4 shrink-0" aria-hidden="true" />
                        <dt className="sr-only">Số điện thoại</dt><dd className="tnum truncate">{customer.phone}</dd>
                      </div>
                      <div className="flex min-w-0 items-center gap-2 text-text-muted">
                        <MapPin className="h-4 w-4 shrink-0" aria-hidden="true" />
                        <dt className="sr-only">Thành phố</dt><dd className="truncate">{customer.city}</dd>
                      </div>
                      <div className="flex min-w-0 items-center gap-2 text-text-muted sm:col-span-2">
                        <Mail className="h-4 w-4 shrink-0" aria-hidden="true" />
                        <dt className="sr-only">Email</dt><dd className="truncate" title={customer.email}>{customer.email}</dd>
                      </div>
                    </dl>

                    <details className="group mt-4 border-t border-border pt-3">
                      <summary className="flex min-h-8 cursor-pointer list-none items-center justify-between text-sm font-semibold text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 [&::-webkit-details-marker]:hidden">
                        Xem hành vi và lịch sử
                        <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180 motion-reduce:transition-none" aria-hidden="true" />
                      </summary>
                      <div className="mt-3 space-y-3 rounded-xl bg-bg-alt p-3 text-sm leading-6">
                        <div><p className="text-xs font-semibold uppercase tracking-wider text-text-dim">Hành vi</p><p className="mt-1 text-text-muted">{customer.behavior}</p></div>
                        <div><p className="text-xs font-semibold uppercase tracking-wider text-text-dim">Lịch sử hoạt động</p><p className="mt-1 text-text-muted">{customer.history}</p></div>
                      </div>
                    </details>
                  </article>
                ))}
              </div>
            )}

            {customers.length > 0 && pageCount > 1 && (
              <div className="mt-4 flex items-center justify-between border-t border-border pt-4">
                <span className="tnum text-xs text-text-muted">
                  {current * PAGE_SIZE + 1}–{Math.min((current + 1) * PAGE_SIZE, customers.length)}
                  {" / "}{customers.length} khách hàng
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="secondary" size="sm"
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={current === 0}
                  >
                    Trước
                  </Button>
                  <Button
                    variant="secondary" size="sm"
                    onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                    disabled={current >= pageCount - 1}
                  >
                    Sau
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </section>
  );
}
