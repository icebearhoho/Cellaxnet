"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ArrowLeftRight,
  ChevronRight,
  LayoutGrid,
  Menu,
  PlugZap,
  ShoppingCart,
  Store,
  X,
} from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import {
  INTERNAL_TOOL_SLUGS,
  navForApp,
  PRODUCT_AREAS,
  SELLER_SELF_SERVICE_SLUGS,
  type AppKind,
} from "@/lib/nav";
import { useAuth } from "@/lib/auth-context";
import { useMounted } from "@/lib/hooks/use-mounted";
import { useT } from "@/lib/i18n";

export function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const closeTimerRef = useRef<number | null>(null);
  const { user, isAdmin } = useAuth();
  const mounted = useMounted();
  const t = useT();

  useEffect(() => {
    setOpen(false);
    setExpandedSection(null);
  }, [pathname]);

  useEffect(() => () => {
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current);
    }
  }, []);

  function cancelScheduledClose() {
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  }

  function showSection(sectionId: string) {
    cancelScheduledClose();
    setExpandedSection(sectionId);
  }

  function hideSectionSoon() {
    cancelScheduledClose();
    closeTimerRef.current = window.setTimeout(() => {
      setExpandedSection(null);
      closeTimerRef.current = null;
    }, 350);
  }

  const app: AppKind = pathname.startsWith("/seller") ? "seller" : "shop";
  const items = navForApp(app).filter(
    (item) => app !== "seller" || isAdmin || SELLER_SELF_SERVICE_SLUGS.has(item.slug),
  );
  const brand = app === "seller"
    ? { label: t("Người bán"), icon: Store, other: "/shop", otherLabel: t("Cửa hàng") }
    : { label: t("Cửa hàng"), icon: ShoppingCart, other: "/seller", otherLabel: t("Người bán") };
  const BrandIcon = brand.icon;
  const home = app === "seller" ? "/seller" : "/shop";

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
        onKeyDown={(event) => {
          if (event.key === "Escape") setExpandedSection(null);
        }}
        className={cn(
          "card-surface fixed inset-y-0 left-0 z-40 flex w-64 flex-col overflow-visible border-r bg-surface/95 transition-transform lg:translate-x-0",
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

        {/* Product-style navigation: compact categories open a Firebase-like
            flyout on desktop and an inline accordion on mobile. */}
        <nav className="flex-1 overflow-y-auto p-3 lg:overflow-visible">
          <p className="px-3 pb-2 pt-1 text-2xs font-medium uppercase tracking-wider text-text-dim">
            {t("Không gian làm việc")}
          </p>

          <Link
            href={home}
            className={cn(
              "mb-1 flex h-11 items-center gap-3 rounded-xl border-[1.5px] px-3 text-sm font-semibold transition-all",
              pathname === home
                ? "border-accent/40 bg-accent/12 text-accent shadow-[2px_2px_0_hsl(var(--accent)/0.14)]"
                : "border-transparent text-text-muted hover:border-border hover:bg-surface-2 hover:text-text",
            )}
          >
            <LayoutGrid className="h-4 w-4 shrink-0" />
            <span className="flex-1">{t("Tổng quan")}</span>
          </Link>

          {PRODUCT_AREAS.filter((area) => area.app === app).map((section) => {
            const areaItems = items.filter((item) => section.slugs.includes(item.slug));
            const secItems = areaItems.filter((item) => !INTERNAL_TOOL_SLUGS.has(item.slug));
            const advancedItems = areaItems.filter((item) => INTERNAL_TOOL_SLUGS.has(item.slug));
            if (!areaItems.length) return null;
            const SectionIcon = section.icon;
            const sectionActive = areaItems.some((item) => isActive(item.href));
            const expanded = expandedSection === section.id;
            const primaryItem = secItems.find((item) => item.slug === section.primarySlug);
            const supportingItems = secItems.filter((item) => item.slug !== section.primarySlug);
            const orderedItems = primaryItem ? [primaryItem, ...supportingItems] : supportingItems;
            return (
              <div
                key={section.id}
                className="relative"
                onMouseEnter={() => showSection(section.id)}
                onMouseLeave={hideSectionSoon}
                onFocus={() => showSection(section.id)}
                onBlur={(event) => {
                  if (!event.currentTarget.contains(event.relatedTarget)) {
                    hideSectionSoon();
                  }
                }}
              >
                <button
                  type="button"
                  aria-expanded={expanded}
                  aria-controls={`nav-section-${section.id}`}
                  onClick={() => {
                    cancelScheduledClose();
                    setExpandedSection(expanded ? null : section.id);
                  }}
                  className={cn(
                    "group mb-1 flex h-11 w-full items-center gap-3 rounded-xl border-[1.5px] px-3 text-left text-sm font-semibold transition-all",
                    sectionActive || expanded
                      ? "border-accent/35 bg-accent/10 text-accent"
                      : "border-transparent text-text-muted hover:border-border hover:bg-surface-2 hover:text-text",
                  )}
                >
                  <SectionIcon className="h-4 w-4 shrink-0" />
                  <span className="flex-1 truncate">{t(section.title)}</span>
                  <span className="mono text-2xs text-text-dim">{secItems.length}</span>
                  <ChevronRight
                    className={cn(
                      "h-4 w-4 shrink-0 transition-transform lg:group-hover:translate-x-0.5",
                      expanded && "rotate-90 lg:rotate-0",
                    )}
                  />
                </button>

                <div
                  id={`nav-section-${section.id}`}
                  className={cn(
                    "mb-2 ml-3 border-l border-dashed border-border pl-2 lg:absolute lg:left-full lg:top-0 lg:z-50 lg:mb-0 lg:ml-0 lg:max-h-[calc(100vh-2rem)] lg:w-80 lg:translate-x-3 lg:overflow-y-auto lg:rounded-2xl lg:border lg:border-solid lg:bg-surface lg:p-3 lg:shadow-[6px_7px_0_hsl(var(--border)/0.65)]",
                    expanded ? "nav-flyout block" : "hidden",
                  )}
                >
                  <span
                    aria-hidden="true"
                    className="absolute -left-3 top-0 hidden h-full w-3 lg:block"
                  />
                  <div className="hidden border-b border-dashed border-border px-2 pb-2.5 pt-1 lg:block">
                    <p className="text-xs font-semibold text-text">{t(section.title)}</p>
                    <p className="mt-0.5 text-2xs text-text-dim">
                      {t(section.description)}
                    </p>
                  </div>
                  <ul className="space-y-1 lg:pt-2">
                  {orderedItems.map((item, itemIndex) => {
                    const Icon = item.icon;
                    const active = isActive(item.href);
                    const primary = item.slug === section.primarySlug;
                    return (
                      <li
                        key={item.slug}
                        className="nav-flyout-item"
                        style={{ animationDelay: `${45 + itemIndex * 35}ms` }}
                      >
                        <Link
                          href={item.href}
                          className={cn(
                            "group flex min-h-10 items-center gap-2.5 rounded-xl border-[1.5px] border-transparent px-3 py-2 text-sm font-medium transition-all",
                            active
                              ? "rotate-[-0.5deg] border-accent/40 bg-accent/12 text-accent shadow-[2px_2px_0_hsl(var(--accent)/0.14)]"
                              : primary
                                ? "border-accent/20 bg-accent/[0.06] text-text hover:border-accent/40 hover:bg-accent/10"
                                : "text-text-muted hover:border-border hover:bg-surface-2 hover:text-text",
                          )}
                        >
                          <Icon className="h-4 w-4 shrink-0" />
                          <span className="min-w-0 flex-1 truncate">{t(item.label)}</span>
                          <span className={cn(
                            "mono shrink-0 text-2xs",
                            primary ? "rounded-full bg-accent/10 px-1.5 py-0.5 text-accent" : "text-text-dim",
                          )}>
                            {primary ? t("Luồng chính") : item.id}
                          </span>
                        </Link>
                      </li>
                    );
                  })}
                  </ul>
                  {advancedItems.length > 0 && (
                    <details className="mt-2 border-t border-dashed border-border pt-2">
                      <summary className="cursor-pointer list-none rounded-lg px-2 py-1.5 text-2xs font-semibold text-text-dim transition-colors hover:bg-surface-2 hover:text-text">
                        {t("Công cụ nâng cao")} · {advancedItems.length}
                      </summary>
                      <div className="mt-1 space-y-0.5">
                        {advancedItems.map((item) => {
                          const Icon = item.icon;
                          return (
                            <Link
                              key={item.slug}
                              href={item.href}
                              className={cn(
                                "flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs transition-colors",
                                isActive(item.href)
                                  ? "bg-accent/10 text-accent"
                                  : "text-text-muted hover:bg-surface-2 hover:text-text",
                              )}
                            >
                              <Icon className="h-3.5 w-3.5 shrink-0" />
                              <span className="min-w-0 flex-1 truncate">{t(item.label)}</span>
                            </Link>
                          );
                        })}
                      </div>
                    </details>
                  )}
                </div>
              </div>
            );
          })}
        </nav>

        {app === "seller" && mounted && isAdmin && (
          <div className="border-t border-dashed border-border px-3 py-2">
            <Link
              href="/seller/marketplace"
              className={cn(
                "flex items-center gap-2 rounded-xl px-3 py-2.5 text-xs transition-colors",
                pathname.startsWith("/seller/marketplace")
                  ? "bg-accent/10 text-accent"
                  : "text-text-muted hover:bg-surface-2 hover:text-text",
              )}
            >
              <PlugZap className="h-3.5 w-3.5" />
              <span className="flex-1">{t("Kết nối dữ liệu")}</span>
              <span className="mono text-2xs text-text-dim">SETUP</span>
            </Link>
          </div>
        )}

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
              <span>{t("Chuyển sang")} <span className="text-text">{brand.otherLabel}</span></span>
            </Link>
          </div>
        )}
      </aside>
    </>
  );
}
