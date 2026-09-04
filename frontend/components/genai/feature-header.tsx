"use client";

import { Button } from "@/components/ui/button";
import Link from "next/link";
import type { ReactNode } from "react";
import { useT } from "@/lib/i18n";

export function FeatureHeader({
  title,
  subtitle,
  action,
  backHref = "/seller",
}: {
  id: string;
  title: string;
  subtitle: string;
  category: string;
  owner: "TL" | "DA" | "FS" | "D1" | "D2";
  demoMode?: boolean;
  action?: ReactNode;
  backHref?: string;
}) {
  const t = useT();
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-text">
          {t(title)}
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-text-muted">{t(subtitle)}</p>
      </div>

      <div className="flex flex-col items-end gap-2">
        {action ?? (
          <Button asChild variant="ghost" size="sm">
            <Link href={backHref}>← {t("Tổng quan")}</Link>
          </Button>
        )}
      </div>
    </div>
  );
}
