"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, Store, ShoppingCart, ArrowLeftRight } from "lucide-react";
import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { navForApp, NAV_SECTIONS, SELLER_SELF_SERVICE_SLUGS, type AppKind } from "@/lib/nav";
import { useAuth } from "@/lib/auth-context";
import { useMounted } from "@/lib/hooks/use-mounted";

export function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { user, isAdmin } = useAuth();
  const mounted = useMounted();

  useEffect(() => setOpen(false), [pathname]);

  const app: AppKind = pathname.startsWith("/seller") ? "seller" : "shop";
  const items = navForApp(app).filter(
    (item) => app !== "seller" || isAdmin || SELLER_SELF_SERVICE_SLUGS.has(item.slug),
  );
  const brand = app === "seller"
    ? { label: "Người bán", icon: Store, other: "/shop", otherLabel: "Cửa hàng" }
    : { label: "Cửa hàng", icon: ShoppingCart, other: "/seller", otherLabel: "Người bán" };
  const BrandIcon = brand.icon;
  const home = app === "seller" && user?.role !== "admin" ? "/seller/workspace" : app === "seller" ? "/seller" : "/shop";

  const isActive = (href: string) =>
    href === home ? pathname === home : pathname.startsWith(href);

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        className="card-surface fixed left-4 top-3 z-50 inline-flex h-9 w-9 rotate-[-2deg] items-center justify-center rounded-lg border bg-surface text-text lg:hidden"
        aria-label="Toggle navigation"
      >
        {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
      </button>

      {open && (
        <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setOpen(false)} />
      )}

      <aside
        className={cn(
          "card-surface fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r bg-surface/95 transition-transform lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Brand */}
        <Link href={home} className="flex h-16 items-center gap-2.5 border-b border-border px-5">
          <div className="doodle-sticker h-9 w-9">
            <BrandIcon className="h-4 w-4 text-accent" />
          </div>
          <div className="flex flex-col leading-none">
            <span className="text-sm font-semibold">{brand.label}</span>
            <span className="mono text-2xs text-text-dim">AREA-303</span>
          </div>
        </Link>

        {/* Nav grouped by section */}
        <nav className="flex-1 overflow-y-auto p-3">
          {NAV_SECTIONS.map((section) => {
            const secItems = items.filter((i) => i.section === section.id);
            if (!secItems.length) return null;
            return (
              <div key={section.id} className="mb-5">
                <div className="px-3 pb-2 pt-2 text-2xs font-medium uppercase tracking-wider text-text-dim">
                  {section.title}
                </div>
                <ul className="space-y-1">
                  {secItems.map((item) => {
                    const Icon = item.icon;
                    const active = isActive(item.href);
                    return (
                      <li key={item.slug}>
                        <Link
                          href={item.href}
                          className={cn(
                            "group flex h-10 items-center gap-2.5 rounded-md border-[1.5px] border-transparent px-3 text-sm font-medium transition-all",
                            active
                              ? "rotate-[-0.5deg] border-accent/40 bg-accent/12 text-accent shadow-[2px_2px_0_hsl(var(--accent)/0.14)]"
                              : "text-text-muted hover:border-border hover:bg-surface-2 hover:text-text",
                          )}
                        >
                          <Icon className="h-4 w-4 shrink-0" />
                          <span className="truncate">{item.label}</span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </nav>

        {/* Switch app — direction-aware, because this sidebar renders for both
            apps. Leaving the seller portal is always fine; entering it is
            admin-only, so hide that direction for everyone else. */}
        {(app === "seller" || (mounted && isAdmin)) && (
          <div className="border-t border-border p-3">
            <Link
              href={brand.other}
              className="flex items-center gap-2 rounded-xl bg-surface-2 px-3 py-2.5 text-xs text-text-muted transition-colors hover:bg-surface-3 hover:text-text"
            >
              <ArrowLeftRight className="h-3.5 w-3.5" />
              <span>Chuyển sang <span className="text-text">{brand.otherLabel}</span></span>
            </Link>
          </div>
        )}
      </aside>
    </>
  );
}
