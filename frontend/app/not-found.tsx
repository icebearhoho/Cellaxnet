import Link from "next/link";
import { DashboardShell } from "@/components/shell/dashboard-shell";

export const dynamic = "force-dynamic";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <DashboardShell breadcrumb={[{ label: "Không tìm thấy" }]}>
      <div className="flex flex-col items-start gap-4">
        <div className="mono text-2xs uppercase tracking-wider text-text-dim">
          404 — không tìm thấy
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-text">
          Trang này không tồn tại
        </h1>
        <p className="text-sm text-text-muted">
          Đường dẫn có thể đã thay đổi hoặc chưa sẵn sàng.
        </p>
        <Button asChild variant="secondary">
          <Link href="/">Về trang tổng quan</Link>
        </Button>
      </div>
    </DashboardShell>
  );
}
