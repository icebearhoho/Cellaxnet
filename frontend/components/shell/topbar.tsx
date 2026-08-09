"use client";

import { useEffect, useState, useCallback } from "react";
import { Search, User } from "lucide-react";
import { useRouter } from "next/navigation";
import { READY_NAV_ITEMS } from "@/lib/nav";
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
import { useMounted } from "@/lib/hooks/use-mounted";

type Crumb = { label: string; href?: string };

export function TopBar({ breadcrumb }: { breadcrumb: Crumb[] }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const mounted = useMounted();

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

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-4 border-b border-border bg-bg/80 px-4 backdrop-blur lg:px-6">
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
        className="ml-auto h-8 w-72 justify-start gap-2 px-3 text-text-muted"
      >
        <Search className="h-3.5 w-3.5" />
        <span className="text-xs">Tìm tính năng…</span>
        <CommandShortcut>Ctrl K</CommandShortcut>
      </Button>

      {/* User menu placeholder */}
      <div className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-surface">
        <User className="h-3.5 w-3.5 text-text-muted" />
      </div>

      {mounted ? (
        <CommandDialog open={open} onOpenChange={setOpen}>
          <CommandInput placeholder="Tìm tính năng…" />
          <CommandList>
            <CommandEmpty>Không tìm thấy.</CommandEmpty>
            <CommandGroup heading="Điều hướng">
              {READY_NAV_ITEMS.map((item) => (
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
