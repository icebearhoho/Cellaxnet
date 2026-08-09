import { DashboardShell } from "@/components/shell/dashboard-shell";
import { FeatureHeader } from "@/components/genai/feature-header";
import { FeaturePanel } from "@/components/features/feature-registry";
import { ComingSoon } from "@/components/shell/coming-soon";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { findBySlug, IMPLEMENTED, SUBTITLE } from "@/lib/nav";

export const dynamic = "force-dynamic";

export default async function SellerFeaturePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const item = findBySlug(slug);

  if (!item || item.app !== "seller") {
    return (
      <DashboardShell breadcrumb={[{ label: "Người bán", href: "/seller" }, { label: "Không tìm thấy" }]}>
        <Card>
          <CardHeader>
            <CardTitle>Not found</CardTitle>
            <p className="mt-1 text-xs text-text-muted">Không có tính năng dành cho người bán nào khớp với đường dẫn này.</p>
          </CardHeader>
        </Card>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell breadcrumb={[{ label: "Người bán", href: "/seller" }, { label: item.label }]}>
      <FeatureHeader
        id={item.id}
        title={item.label}
        subtitle={SUBTITLE[slug] ?? "Tính năng dành cho người bán."}
        category={item.category}
        owner={item.owner}
      />
      {IMPLEMENTED.has(slug) ? <FeaturePanel slug={slug} /> : <ComingSoon item={item} />}
    </DashboardShell>
  );
}
