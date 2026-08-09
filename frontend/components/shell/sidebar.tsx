"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, Store, ShoppingCart, ArrowLeftRight } from "lucide-react";
import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { navForApp, NAV_SECTIONS, type AppKind } from "@/lib/nav";

export function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => setOpen(false), [pathname]);

  const app: AppKind = pathname.startsWith("/seller") ? "seller" : "shop";
  const items = navForApp(app);
  const brand = app === "seller"
    ? { label: "Người bán", icon: Store, other: "/shop", otherLabel: "Cửa hàng" }
    : { label: "Cửa hàng", icon: ShoppingCart, other: "/seller", otherLabel: "Người bán" };
  const BrandIcon = brand.icon;
  const home = app === "seller" ? "/seller" : "/shop";

  const isActive = (href: string) =>
    href === home ? pathname === home : pathname.startsWith(href);

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed left-4 top-3 z-50 inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-surface text-text lg:hidden"
        aria-label="Toggle navigation"
      >
        {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
      </button>

      {open && (
        <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setOpen(false)} />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-border bg-bg-alt transition-transform lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Brand */}
        <Link href={home} className="flex h-14 items-center gap-2 border-b border-border px-4">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent/15">
            <BrandIcon className="h-3.5 w-3.5 text-accent" />
          </div>
          <div className="flex flex-col leading-none">
            <span className="mono text-sm font-semibold tracking-wider">{brand.label}</span>
            <span className="mono text-2xs text-text-dim">AREA-303</span>
          </div>
        </Link>

        {/* Nav grouped by section */}
        <nav className="flex-1 overflow-y-auto p-2">
          {NAV_SECTIONS.map((section) => {
            const secItems = items.filter((i) => i.section === section.id);
            if (!secItems.length) return null;
            return (
              <div key={section.id} className="mb-4">
                <div className="px-3 pb-1.5 pt-2 text-2xs uppercase tracking-wider text-text-dim">
                  {section.title}
                </div>
                <ul className="space-y-0.5">
                  {secItems.map((item) => {
                    const Icon = item.icon;
                    const active = isActive(item.href);
                    return (
                      <li key={item.slug}>
                        <Link
                          href={item.href}
                          className={cn(
                            "group relative flex h-9 items-center gap-2.5 rounded-md px-3 text-sm transition-colors",
                            active ? "bg-surface-3 text-text"
                              : "text-text-muted hover:bg-surface-2 hover:text-text",
                          )}
                        >
                          {active && (
                            <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r bg-accent" />
                          )}
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

        {/* Switch app */}
        <div className="border-t border-border p-3">
          <Link
            href={brand.other}
            className="flex items-center gap-2 rounded-md bg-surface px-3 py-2 text-xs text-text-muted transition-colors hover:text-text"
          >
            <ArrowLeftRight className="h-3.5 w-3.5" />
            <span>Chuyển sang <span className="text-text">{brand.otherLabel}</span></span>
          </Link>
        </div>
      </aside>
    </>
  );
}
