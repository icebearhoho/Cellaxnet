"use client";

/** Màn "không tìm thấy" cho một trang tính năng của gian hàng.
 *
 *  Tách riêng vì trang gọi nó là server component async — không gọi được hook
 *  ở đó, mà chuỗi thì cần dịch.
 */

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useT } from "@/lib/i18n";

export function ShopFeatureNotFound() {
  const t = useT();
  return (
    <div className="card-surface rounded-lg border p-10 text-center">
      <p className="text-lg font-bold">{t("Không tìm thấy trang này")}</p>
      <Link href="/shop" className="mt-3 inline-block font-semibold text-accent">
        {t("← Về trang chủ")}
      </Link>
    </div>
  );
}

/** Màn "sắp ra mắt" cho một tính năng chưa dựng xong. Tách ra cùng lý do. */
export function ShopFeatureComingSoon() {
  const t = useT();
  return (
    <div className="card-surface rounded-lg border p-10 text-center">
      <div className="text-4xl">🛠️</div>
      <p className="mt-3 text-lg font-bold">{t("Sắp ra mắt")}</p>
      <p className="mt-1 text-text-muted">
        {t("Tính năng này đang được hoàn thiện. Quay lại sau nhé!")}
      </p>
      <Link href="/shop" className="mt-4 inline-flex items-center gap-1.5 font-semibold text-accent">
        <ArrowLeft className="h-4 w-4" /> {t("Khám phá tính năng khác")}
      </Link>
    </div>
  );
}

/** Tiêu đề và mô tả của một trang tính năng gian hàng.
 *
 *  Nhận chuỗi tiếng Việt từ nav.ts và dịch tại đây — trang gọi nó là server
 *  component async nên không tự dịch được.
 */
export function ShopFeatureHeading({
  label,
  subtitle,
}: {
  label: string;
  subtitle: string;
}) {
  const t = useT();
  return (
    <div>
      <h1 className="text-2xl font-extrabold tracking-tight">{t(label)}</h1>
      <p className="mt-1 max-w-2xl text-text-muted">{t(subtitle)}</p>
    </div>
  );
}
