import { DashboardShell } from "@/components/shell/dashboard-shell";
import { SellerOverview } from "@/components/dashboard/seller-overview";

export const dynamic = "force-dynamic";

export default function SellerHome() {
  return (
    <DashboardShell breadcrumb={[{ label: "Người bán", href: "/seller" }, { label: "Tổng quan" }]}>
      <SellerOverview />
    </DashboardShell>
  );
}
