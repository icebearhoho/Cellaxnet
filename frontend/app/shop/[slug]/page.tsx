import Link from "next/link";
import { FeaturePanel } from "@/components/features/feature-registry";
import { findBySlug, IMPLEMENTED, SUBTITLE } from "@/lib/nav";
import {
  ShopFeatureComingSoon,
  ShopFeatureHeading,
  ShopFeatureNotFound,
} from "@/components/shell/shop-feature-not-found";

export const dynamic = "force-dynamic";

export default async function ShopFeaturePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const item = findBySlug(slug);

  if (!item || item.app !== "shop") {
    return (
      <ShopFeatureNotFound />
    );
  }

  const Icon = item.icon;

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-accent/10 text-accent">
          <Icon className="h-5 w-5" />
        </span>
        <ShopFeatureHeading
          label={item.label}
          subtitle={SUBTITLE[slug] ?? "Tính năng mua sắm."}
        />
      </div>

      {IMPLEMENTED.has(slug) ? (
        <FeaturePanel slug={slug} />
      ) : (
        <ShopFeatureComingSoon />
      )}
    </div>
  );
}
