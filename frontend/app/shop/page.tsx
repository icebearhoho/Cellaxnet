import Link from "next/link";
import { ArrowRight, Sparkles, Store } from "lucide-react";
import { navForApp } from "@/lib/nav";

export const dynamic = "force-dynamic";

export default function ShopHome() {
  const items = navForApp("shop");

  return (
    <div className="space-y-10">
      {/* Hero */}
      <section className="rounded-[28px] border border-border bg-surface p-8 shadow-soft sm:p-12">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs font-semibold text-text-muted">
          <Sparkles className="h-3.5 w-3.5 text-accent" /> gợi ý dành riêng cho bạn
        </span>
        <h1 className="mt-4 max-w-2xl text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl">
          Tìm đúng món bạn thích, nhanh &amp; dễ thương ✨
        </h1>
        <p className="mt-3 max-w-xl text-text-muted">
          Trợ lý mua sắm thông minh cho thời trang &amp; mỹ phẩm — cứ nói bạn cần gì,
          tụi mình gợi ý ngay.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/shop/store"
            className="inline-flex items-center gap-2 rounded-full bg-accent px-5 py-2.5 font-bold text-white transition-transform hover:-translate-y-0.5"
          >
            <Store className="h-4 w-4" /> Vào cửa hàng »
          </Link>
          <Link
            href="/shop/personal-shopper"
            className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-5 py-2.5 font-bold text-text transition-colors hover:border-text"
          >
            Hỏi trợ lý mua sắm <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/shop/recsys"
            className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-5 py-2.5 font-bold text-text transition-colors hover:border-text"
          >
            Gợi ý cho bạn
          </Link>
        </div>
      </section>

      {/* Feature cards */}
      <section>
        <h2 className="mb-4 text-lg font-extrabold">Khám phá</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.slug}
                href={item.href}
                className="group flex flex-col rounded-3xl border border-border bg-surface p-6 transition-all hover:-translate-y-0.5 hover:shadow-soft"
              >
                <span className="grid h-12 w-12 place-items-center rounded-2xl border-2 border-text/80 text-text transition-colors group-hover:border-accent group-hover:text-accent">
                  <Icon className="h-5 w-5" strokeWidth={2} />
                </span>
                <div className="mt-4 flex items-center gap-2">
                  <span className="text-base font-extrabold">{item.label}</span>
                </div>
                <div className="mt-1 flex items-center text-sm text-text-muted">
                  <span>Thử ngay</span>
                  <ArrowRight className="ml-auto h-4 w-4 text-text-dim transition-transform group-hover:translate-x-1 group-hover:text-accent" />
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
