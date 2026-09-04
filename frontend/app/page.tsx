"use client";

import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Bot,
  MessageSquareText,
  Route,
  ShieldCheck,
  Sparkles,
  Star,
  TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { AppChooser } from "@/components/shell/app-chooser";
import { useT } from "@/lib/i18n";

export const dynamic = "force-dynamic";

const FEATURES = [
  {
    icon: MessageSquareText,
    title: "Phân tích đánh giá",
    desc: "Phân loại cảm xúc và phát hiện đánh giá giả ngay khi khách gửi, trước khi nó lên trang sản phẩm.",
  },
  {
    icon: Route,
    title: "Hành trình khách hàng",
    desc: "Thời gian trên trang, bỏ giỏ hàng, thời điểm chốt đơn — dựng lại từ hành vi thật, không phải phỏng đoán.",
  },
  {
    icon: TrendingUp,
    title: "Gợi ý giá bán",
    desc: "So sánh với trung vị ngành hàng và giá đối thủ để đề xuất mức giá không phá lợi nhuận.",
  },
  {
    icon: ShieldCheck,
    title: "Rủi ro khách hàng",
    desc: "Ai sắp rời đi, ai dễ hoàn hàng, ai sẽ hối tiếc sau mua — và ai đang rủi ro chồng cần xử lý gấp.",
  },
  {
    icon: Bot,
    title: "Trợ lý vận hành",
    desc: "Hỏi bằng giọng nói hoặc chữ, nhận câu trả lời tổng hợp từ dữ liệu giá, doanh số, tồn kho và KOL.",
  },
  {
    icon: BarChart3,
    title: "Nhóm khách hàng",
    desc: "Phân nhóm hành vi mua sắm bằng mô hình đã huấn luyện, không phải chia theo cảm tính.",
  },
];

const STATS = [
  { value: "19", label: "tính năng đang chạy" },
  { value: "63", label: "tỉnh thành theo dõi" },
  { value: "3", label: "sàn thương mại" },
];

export default function LandingPage() {
  const t = useT();
  return (
    <div className="landing-motion relative overflow-hidden">
      {/* Ambient colour field + dot texture behind the hero. */}
      <div className="glow-field">
        <div className="glow-blob glow-blob-one left-[-12%] top-[-18%] h-[42rem] w-[42rem] bg-accent" />
        <div className="glow-blob glow-blob-two right-[-8%] top-[-12%] h-[34rem] w-[34rem] bg-accent-2" />
      </div>
      <div className="dot-grid pointer-events-none absolute inset-x-0 top-0 h-[46rem] opacity-60" />

      {/* Nav */}
      <header className="landing-reveal relative z-10 mx-auto flex h-20 max-w-6xl items-center px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="doodle-sticker h-10 w-10 bg-accent text-white">
            <Sparkles className="h-4 w-4" />
          </span>
          <span className="text-lg font-bold tracking-tight">Cellaxnet</span>
        </Link>
        <div className="ml-auto flex items-center gap-2">
          <Button asChild variant="ghost" size="sm">
            <Link href="/login">{t("Đăng nhập")}</Link>
          </Button>
          <Button asChild size="sm">
            <Link href="/register">{t("Bắt đầu miễn phí")}</Link>
          </Button>
        </div>
      </header>

      {/* Hero */}
      <section className="relative z-10 mx-auto max-w-6xl px-4 pb-16 pt-12 text-center sm:px-6 sm:pb-24 sm:pt-20">
        <span className="hero-chip float-chip mx-auto">
          <Sparkles className="h-3.5 w-3.5 text-accent" />
          {t("Nền tảng thương mại điện tử có AI")}
        </span>

        <h1 className="hero-title mx-auto mt-7 max-w-3xl text-5xl font-extrabold sm:text-6xl">
          Bán hàng thông minh hơn,{" "}
          <span className="text-gradient">{t("không phải nhiều việc hơn.")}</span>
        </h1>

        <p className="hero-copy mx-auto mt-6 max-w-xl text-base text-text-muted sm:text-lg">
          {t("Cellaxnet gom phân tích đánh giá, hành trình khách hàng, gợi ý giá và trợ lý vận hành vào một nơi — cho cả người mua và người bán.")}
        </p>

        <div className="hero-actions mt-9 flex flex-wrap items-center justify-center gap-3">
          <Button asChild size="lg">
            <Link href="/register">
              {t("Bắt đầu miễn phí")} <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link href="/shop/store">{t("Xem cửa hàng demo")}</Link>
          </Button>
        </div>

        {/* Social proof + stats */}
        <div className="hero-proof mt-12 flex flex-wrap items-center justify-center gap-x-10 gap-y-5">
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <span className="flex">
              {Array.from({ length: 5 }).map((_, i) => (
                <Star key={i} className="h-4 w-4 fill-warning stroke-warning" />
              ))}
            </span>
            Shopee · Tiki · TikTok Shop
          </div>
          {STATS.map((s) => (
            <div key={s.label} className="text-sm text-text-muted">
              <span className="stat-pop mono text-xl font-bold text-text">{s.value}</span>{" "}
              {s.label}
            </div>
          ))}
        </div>
      </section>

      <span aria-hidden="true" className="hero-doodle hero-doodle-star">✦</span>
      <span aria-hidden="true" className="hero-doodle hero-doodle-loop">↝</span>
      <span aria-hidden="true" className="hero-doodle hero-doodle-heart">♡</span>

      {/* App chooser */}
      <section className="landing-section-reveal relative z-10 mx-auto max-w-4xl px-4 pb-20 sm:px-6">
        <AppChooser />
      </section>

      {/* Features */}
      <section className="relative z-10 border-t border-border bg-bg-alt/60">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-extrabold sm:text-4xl">
              {t("Mọi thứ người bán cần, trong một cổng")}
            </h2>
            <p className="mt-4 text-text-muted">
              {t("Không phải một tá dashboard rời rạc — các tính năng dùng chung dữ liệu nên câu trả lời luôn khớp nhau.")}
            </p>
          </div>

          <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <div
                  key={f.title}
                  className="feature-doodle-card card-surface rounded-lg border p-6 transition-all hover:-translate-y-1"
                >
                  <span className="doodle-sticker h-11 w-11">
                    <Icon className="h-5 w-5" />
                  </span>
                  <h3 className="mt-5 text-base font-bold">{f.title}</h3>
                  <p className="mt-2 text-sm text-text-muted">{f.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Closing CTA */}
      <section className="relative z-10 mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <div className="relative overflow-hidden rounded-lg border-2 border-text bg-text px-8 py-14 text-center shadow-[6px_7px_0_hsl(var(--accent)/0.28)] sm:px-14">
          <h2 className="text-3xl font-extrabold text-bg sm:text-4xl">
            {t("Thử toàn bộ hệ thống ngay")}
          </h2>
          <p className="mx-auto mt-4 max-w-lg text-bg/70">
            {t("Tạo tài khoản người mua trong vài giây, hoặc mở cửa hàng demo để xem sản phẩm, đánh giá và giỏ hàng hoạt động thật.")}
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Button
              asChild
              size="lg"
              className="bg-bg text-text hover:bg-bg-alt hover:text-text"
            >
              <Link href="/register">
                {t("Tạo tài khoản")} <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="ghost"
              className="text-bg/80 hover:bg-white/10 hover:text-bg"
            >
              <Link href="/shop/store">{t("Xem cửa hàng")}</Link>
            </Button>
          </div>
        </div>
      </section>

      <footer className="relative z-10 border-t border-border">
        <div className="mx-auto max-w-6xl px-4 py-8 text-center text-xs text-text-dim sm:px-6">
          {t("Cellaxnet · thương mại điện tử thời trang & mỹ phẩm")}
        </div>
      </footer>
    </div>
  );
}
