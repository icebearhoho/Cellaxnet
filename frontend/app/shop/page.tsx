"use client";

import Link from "next/link";
import { ArrowRight, Sparkles, Store } from "lucide-react";
import { navForApp } from "@/lib/nav";

export const dynamic = "force-dynamic";

export default function ShopHome() {
  const items = navForApp("shop");

  return (
    <div className="space-y-14">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-lg border border-border bg-surface px-7 py-12 shadow-soft sm:px-12 sm:py-16">
        <div className="glow-field">
          <div className="glow-blob left-[-15%] top-[-40%] h-[26rem] w-[26rem] bg-accent" />
          <div className="glow-blob right-[-10%] top-[-30%] h-[22rem] w-[22rem] bg-accent-2" />
        </div>

        <div className="relative max-w-xl">
          <span className="float-chip">
            <Sparkles className="h-3.5 w-3.5 text-accent" />
            Gợi ý dành riêng cho bạn
          </span>
          <h1 className="mt-6 text-4xl font-extrabold sm:text-5xl">
            Tìm đúng món <span className="text-gradient">bạn thích</span>
          </h1>
          <p className="mt-5 text-text-muted">
            Trợ lý mua sắm thông minh cho thời trang & mỹ phẩm — cứ nói bạn cần gì, Cellaxnet gợi ý ngay.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              href="/shop/store"
              className="inline-flex items-center gap-2 rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-accent-hover"
            >
              <Store className="h-4 w-4" /> Vào cửa hàng
            </Link>
            <Link
              href="/shop/personal-shopper"
              className="inline-flex items-center gap-1.5 rounded-full border border-border-strong px-6 py-3 text-sm font-semibold text-text transition-colors hover:border-accent hover:text-accent"
            >
              Hỏi trợ lý mua sắm <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </section>

      {/* Feature cards */}
      <section>
        <h2 className="mb-6 text-2xl font-bold">Khám phá</h2>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.slug}
                href={item.href}
                className="card-surface group flex flex-col rounded-lg border p-6 transition-all hover:rotate-[0.4deg] hover:-translate-y-1 hover:border-accent/50"
              >
                <span className="doodle-sticker h-11 w-11">
                  <Icon className="h-5 w-5" />
                </span>
                <div className="mt-5 text-base font-bold">{item.label}</div>
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
