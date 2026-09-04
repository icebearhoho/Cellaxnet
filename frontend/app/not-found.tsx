"use client";

import Link from "next/link";
import { DashboardShell } from "@/components/shell/dashboard-shell";

export const dynamic = "force-dynamic";

import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n";

export default function NotFound() {
  const t = useT();
  return (
    <DashboardShell breadcrumb={[{ label: "Không tìm thấy" }]}>
      <div className="flex flex-col items-start gap-4">
        <div className="text-xs font-medium text-text-dim">
          {t("404 — không tìm thấy")}
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-text">
          {t("Trang này không tồn tại")}
        </h1>
        <p className="text-sm text-text-muted">
          {t("Đường dẫn có thể đã thay đổi hoặc chưa sẵn sàng.")}
        </p>
        <Button asChild variant="secondary">
          <Link href="/">{t("Về trang tổng quan")}</Link>
        </Button>
      </div>
    </DashboardShell>
  );
}
