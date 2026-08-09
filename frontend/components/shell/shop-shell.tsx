"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Store, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { navForApp } from "@/lib/nav";
import { ShopSessionBar } from "@/components/shell/shop-session-bar";
import { CartButton } from "@/components/shell/cart-button";

const items = navForApp("shop");

export function ShopShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const isActive = (href: string) => pathname === href || pathname.startsWith(href + "/");

  return (
    <div className="min-h-screen bg-bg text-text">
      {/* Friendly top bar */}
      <header className="sticky top-0 z-30 border-b border-border bg-bg/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4 sm:px-6">
          <Link href="/shop" className="flex items-center gap-2">
            <span className="grid h-9 w-9 place-items-center rounded-2xl border-2 border-text/80 text-text">
              <Store className="h-4 w-4" />
            </span>
            <span className="text-lg font-extrabold tracking-tight">Shop</span>
          </Link>

          {/* desktop nav */}
          <nav className="ml-4 hidden flex-1 items-center gap-1 md:flex">
            {items.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <Link
                  key={item.slug}
                  href={item.href}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-semibold transition-colors",
                    active
                      ? "border-accent bg-accent/10 text-accent"
                      : "border-transparent text-text-muted hover:border-border hover:text-text",
                  )}
                >
                  <Icon className="h-4 w-4" strokeWidth={2} />
                  <span className="hidden lg:inline">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <CartButton />
            <Link
              href="/seller"
              className="hidden rounded-full border border-border px-3 py-1.5 text-sm font-semibold text-text-muted transition-colors hover:border-text hover:text-text md:inline-flex"
            >
              Người bán →
            </Link>
          </div>

          <button
            onClick={() => setOpen((v) => !v)}
            className="grid h-10 w-10 place-items-center rounded-2xl border border-border md:hidden"
            aria-label="Menu"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {/* mobile nav */}
        {open && (
          <div className="border-t border-border px-4 py-3 md:hidden">
            <div className="flex flex-wrap gap-2">
              {items.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.slug}
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-semibold",
                      isActive(item.href) ? "border-accent bg-accent/10 text-accent" : "border-border text-text-muted",
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
              <Link href="/seller" onClick={() => setOpen(false)}
                className="inline-flex items-center rounded-full border border-border px-3 py-1.5 text-sm font-semibold text-text-muted">
                Người bán →
              </Link>
            </div>
          </div>
        )}
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</main>

      <footer className="mx-auto max-w-6xl px-4 pb-10 pt-4 text-center text-xs text-text-dim sm:px-6">
        AREA-303 · mua sắm thời trang &amp; mỹ phẩm
      </footer>

      <ShopSessionBar />
    </div>
  );
}
