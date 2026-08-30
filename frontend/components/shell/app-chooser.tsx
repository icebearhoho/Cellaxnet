"use client";

import Link from "next/link";
import { ArrowRight, ShoppingCart, Store } from "lucide-react";
import { canAccessApp, navForApp, type AppKind } from "@/lib/nav";
import { useAuth } from "@/lib/auth-context";
import { useMounted } from "@/lib/hooks/use-mounted";

const APPS = [
  {
    href: "/shop",
    icon: ShoppingCart,
    title: "Cửa hàng",
    tagline: "Dành cho người mua",
    desc: "Khám phá sản phẩm, đọc đánh giá thật, nhận gợi ý theo nhu cầu và ngân sách.",
    app: "shop" as AppKind,
  },
  {
    href: "/seller",
    icon: Store,
    title: "Cổng người bán",
    tagline: "Dành cho tài khoản người bán",
    desc: "Phân tích đánh giá, rủi ro khách hàng, gợi ý giá, hành trình khách và trợ lý vận hành.",
    app: "seller" as AppKind,
  },
];

/** The seller card appears after a user activates a seller workspace. */
export function AppChooser() {
  const { user } = useAuth();
  const mounted = useMounted();
  // Before mount we don't know the role, so show only the public app rather
  // than flashing a card the user may not be allowed to open.
  const visible = APPS.filter((a) =>
    a.app === "shop" ? true : mounted && canAccessApp(a.app, user?.role),
  );

  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
      {visible.map((a) => {
        const Icon = a.icon;
        const count = navForApp(a.app).length;
        return (
          <Link
            key={a.href}
            href={a.href}
            className="card-surface group flex flex-col rounded-lg border p-7 transition-all hover:rotate-[0.4deg] hover:-translate-y-1 hover:border-accent/50"
          >
            <div className="flex items-center gap-3">
              <span className="doodle-sticker h-11 w-11">
                <Icon className="h-5 w-5" />
              </span>
              <div>
                <div className="text-lg font-bold tracking-tight">{a.title}</div>
                <div className="text-xs text-text-dim">{a.tagline}</div>
              </div>
              <ArrowRight className="ml-auto h-4 w-4 text-text-dim transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
            </div>
            <p className="mt-4 flex-1 text-sm text-text-muted">{a.desc}</p>
            <div className="mt-5 text-xs font-medium text-text-dim">
              {count} tính năng đang hoạt động
            </div>
          </Link>
        );
      })}
    </div>
  );
}
