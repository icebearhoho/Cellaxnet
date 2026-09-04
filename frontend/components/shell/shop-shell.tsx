"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Sparkles, Menu, X, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { navForApp } from "@/lib/nav";
import { ShopSessionBar } from "@/components/shell/shop-session-bar";
import { CartButton } from "@/components/shell/cart-button";
import { useAuth } from "@/lib/auth-context";
import { useMounted } from "@/lib/hooks/use-mounted";
import { Button } from "@/components/ui/button";

const items = navForApp("shop");

export function ShopShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { user, isAdmin, logout } = useAuth();
  const sellerHref = isAdmin ? "/seller" : "/seller/onboarding";
  const sellerLabel = user?.role === "buyer" ? "Bắt đầu bán hàng →" : "Không gian bán hàng →";
  // Gate on mount so the server-rendered markup (which knows no cookie) and
  // the first client render agree — otherwise React reports a hydration
  // mismatch on every shop page.
  const mounted = useMounted();
  const isActive = (href: string) => pathname === href || pathname.startsWith(href + "/");

  return (
    <div className="min-h-screen bg-bg text-text">
      <header className="sticky top-0 z-30 border-b-2 border-border-strong/35 bg-bg/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="doodle-sticker h-9 w-9 bg-accent text-white">
              <Sparkles className="h-4 w-4" />
            </span>
            <span className="text-lg font-bold tracking-tight">Cellaxnet</span>
          </Link>

          <nav className="hidden flex-1 items-center gap-1 md:flex">
            {items.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.slug}
                  href={item.href}
                  className={cn(
                    "rounded-md border-b-2 px-3.5 py-2 text-sm font-medium transition-colors",
                    active
                      ? "border-accent bg-accent/10 text-accent"
                      : "border-transparent text-text-muted hover:bg-surface-2 hover:text-text",
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            {/* Order history needs an account — a guest order has no owner. */}
            {mounted && user && (
              <Link
                href="/shop/orders"
                className="hidden rounded-full px-3 py-2 text-sm font-medium text-text-muted transition-colors hover:bg-surface-2 hover:text-text md:inline-flex"
              >
                Đơn của tôi
              </Link>
            )}
            <CartButton />
            {mounted && user && (
              <Button asChild variant="secondary" size="sm" className="hidden md:inline-flex">
                <Link href={sellerHref}>{sellerLabel}</Link>
              </Button>
            )}
            {mounted && !user && (
              <Button asChild size="sm" className="hidden md:inline-flex">
                <Link href="/login">Đăng nhập</Link>
              </Button>
            )}
            {mounted && user && (
              <button
                onClick={logout}
                title={user.email}
                className="hidden items-center gap-1.5 rounded-full px-3 py-2 text-sm font-medium text-text-muted transition-colors hover:bg-surface-2 hover:text-text md:inline-flex"
              >
                <LogOut className="h-3.5 w-3.5" /> Đăng xuất
              </button>
            )}
          </div>

          <button
            onClick={() => setOpen((v) => !v)}
            className="grid h-9 w-9 place-items-center rounded-xl border border-border md:hidden"
            aria-label="Menu"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {open && (
          <div className="border-t border-border px-4 py-3 md:hidden">
            <div className="flex flex-col gap-1">
              {items.map((item) => (
                <Link
                  key={item.slug}
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className={cn(
                    "rounded-xl px-3 py-2.5 text-sm font-medium",
                    isActive(item.href) ? "bg-accent/10 text-accent" : "text-text-muted",
                  )}
                >
                  {item.label}
                </Link>
              ))}
              {mounted && user && (
                <Link
                  href={sellerHref}
                  onClick={() => setOpen(false)}
                  className="rounded-xl px-3 py-2.5 text-sm font-medium text-text-muted"
                >
                  {sellerLabel}
                </Link>
              )}
              {mounted && !user ? (
                <Link
                  href="/login"
                  onClick={() => setOpen(false)}
                  className="rounded-xl px-3 py-2.5 text-sm font-semibold text-accent"
                >
                  Đăng nhập
                </Link>
              ) : mounted ? (
                <button
                  onClick={() => {
                    setOpen(false);
                    logout();
                  }}
                  className="rounded-xl px-3 py-2.5 text-left text-sm font-medium text-text-muted"
                >
                  Đăng xuất
                </button>
              ) : null}
            </div>
          </div>
        )}
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">{children}</main>

      <footer className="border-t border-border">
        <div className="mx-auto max-w-6xl px-4 py-8 text-center text-xs text-text-dim sm:px-6">
          Cellaxnet · mua sắm thời trang & mỹ phẩm
        </div>
      </footer>

      <ShopSessionBar />
    </div>
  );
}
