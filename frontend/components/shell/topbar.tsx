"use client";

import { useEffect, useState, useCallback } from "react";
import { LogOut, Search, User } from "lucide-react";
import { useRouter } from "next/navigation";
import { READY_NAV_ITEMS, SELLER_SELF_SERVICE_SLUGS } from "@/lib/nav";
import { useAuth } from "@/lib/auth-context";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
} from "@/components/ui/command";
import { Button } from "@/components/ui/button";
import { LanguageToggle } from "@/components/shell/language-toggle";
import { useMounted } from "@/lib/hooks/use-mounted";

type Crumb = { label: string; href?: string };

export function TopBar({ breadcrumb }: { breadcrumb: Crumb[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const mounted = useMounted();
  const { user, logout } = useAuth();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const runCommand = useCallback(
    (href: string) => {
      setOpen(false);
      router.push(href);
    },
    [router],
  );

  // Nền mờ thay vì trắng đặc: để quầng sáng tím/xanh sau lưng ánh qua, nên
  // thanh trên và nội dung bên dưới đọc ra cùng một mặt phẳng.
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-border bg-surface/70 px-4 backdrop-blur-xl lg:px-6">
      {/* Breadcrumb */}
      <nav className="flex min-w-0 items-center gap-1.5 text-sm">
        {breadcrumb.map((c, i) => (
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && <span className="text-text-dim">/</span>}
            {c.href ? (
              <a href={c.href} className="text-text-muted hover:text-text">
                {c.label}
              </a>
            ) : (
              <span className="text-text">{c.label}</span>
            )}
          </span>
        ))}
      </nav>

      {/* Search */}
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        className="ml-auto h-9 w-72 justify-start gap-2 rounded-xl px-3 text-text-muted"
      >
        <Search className="h-3.5 w-3.5" />
        <span className="text-xs">Tìm tính năng…</span>
        <CommandShortcut>Ctrl K</CommandShortcut>
      </Button>

      {/* Ngôn ngữ. Chỉ hiện sau khi mount vì lựa chọn nằm trong localStorage,
          server render không thấy được. */}
      {mounted ? <LanguageToggle /> : <div className="shrink-0" style={{ width: 74, height: 32 }} />}

      {/* Signed-in identity + logout. Rendered after mount so the markup
          matches the server render, which can't know the cookie. */}
      {mounted && user ? (
        <div className="flex items-center gap-2">
          <div className="hidden text-right leading-tight sm:block">
            <div className="text-xs font-semibold">{user.name || user.email}</div>
            <div className="text-2xs font-medium text-text-dim">
              {user.role === "admin"
                ? "Quản trị viên"
                : user.role === "seller"
                  ? "Người bán"
                  : "Người mua"}
            </div>
          </div>
          <button
            onClick={logout}
            title="Đăng xuất"
            aria-label="Đăng xuất"
            className="grid h-9 w-9 place-items-center rounded-full border border-border bg-surface-2 text-text-muted transition-colors hover:border-danger/40 hover:text-danger"
          >
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <div className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface-2">
          <User className="h-3.5 w-3.5 text-text-muted" />
        </div>
      )}

      {mounted ? (
        <CommandDialog open={open} onOpenChange={setOpen}>
          <CommandInput placeholder="Tìm tính năng…" />
          <CommandList>
            <CommandEmpty>Không tìm thấy.</CommandEmpty>
            <CommandGroup heading="Điều hướng">
              {READY_NAV_ITEMS.filter(
                (item) =>
                  item.app !== "seller" ||
                  user?.role === "admin" ||
                  SELLER_SELF_SERVICE_SLUGS.has(item.slug),
              ).map((item) => (
                <CommandItem
                  key={item.slug}
                  value={`${item.label} ${item.slug}`}
                  onSelect={() => runCommand(item.href)}
                >
                  <item.icon className="h-3.5 w-3.5 text-text-muted" />
                  <span>{item.label}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </CommandDialog>
      ) : null}
    </header>
  );
}
