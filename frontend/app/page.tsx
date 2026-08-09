import Link from "next/link";
import { Store, ShoppingCart, ArrowRight } from "lucide-react";
import { navForApp } from "@/lib/nav";

export const dynamic = "force-dynamic";

const APPS = [
  {
    href: "/shop",
    icon: ShoppingCart,
    title: "Shop",
    tagline: "Dành cho người mua",
    desc: "Khám phá sản phẩm, xem đánh giá, nhận gợi ý phù hợp và quản lý giỏ hàng.",
    app: "shop" as const,
  },
  {
    href: "/seller",
    icon: Store,
    title: "Cổng người bán",
    tagline: "Dành cho người bán",
    desc: "Công cụ cho người bán — phân tích review, chặn review giả, định giá động, dự báo, huấn luyện shop.",
    app: "seller" as const,
  },
];

export default function LandingPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col justify-center px-6 py-16">
      <div className="mono text-2xs uppercase tracking-[0.2em] text-accent">AREA-303 · thương mại điện tử</div>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-text sm:text-4xl">
        Chọn ứng dụng bạn muốn mở
      </h1>
      <p className="mt-2 max-w-2xl text-text-muted">
        Hai ứng dụng kết nối cùng một hệ thống: một cho <span className="text-text">người mua</span> và một cho{" "}
        <span className="text-text">người bán</span>, tập trung vào thời trang &amp; mỹ phẩm.
      </p>

      <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {APPS.map((a) => {
          const Icon = a.icon;
          const items = navForApp(a.app);
          return (
            <Link
              key={a.href}
              href={a.href}
              className="group flex flex-col rounded-xl border border-border bg-surface p-6 transition-colors hover:border-accent"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/15">
                  <Icon className="h-5 w-5 text-accent" />
                </div>
                <div>
                  <div className="text-lg font-semibold text-text">{a.title}</div>
                  <div className="mono text-2xs uppercase tracking-wider text-text-dim">{a.tagline}</div>
                </div>
                <ArrowRight className="ml-auto h-4 w-4 text-text-dim transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
              </div>
              <p className="mt-4 flex-1 text-sm text-text-muted">{a.desc}</p>
              <div className="mono mt-4 text-2xs text-text-dim">
                {items.length} tính năng đang hoạt động
              </div>
            </Link>
          );
        })}
      </div>
    </main>
  );
}
