"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Star } from "lucide-react";
import { api } from "@/lib/api";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { TrafficChart } from "@/components/dashboard/traffic-chart";
import { AlertsTable } from "@/components/dashboard/incidents-table";
import { GeoMap } from "@/components/dashboard/geo-map-client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  KPIS,
  TIMESERIES,
  ALERTS,
  PROVINCES,
  type Kpi,
  type Alert,
  type ProvinceNode,
} from "@/lib/mock-data";
import { useT } from "@/lib/i18n";

type Summary = {
  shop: { name: string; channels: string[]; data_as_of: string; demo_mode: boolean };
  counts: { products: number; customers: number; orders: number; reviews: number };
  kpis: Kpi[];
  timeseries: typeof TIMESERIES;
  alerts: Alert[];
  provinces: ProvinceNode[];
  demo_mode: boolean;
};

export function SellerOverview() {
  const t = useT();
  const [data, setData] = useState<Summary | null>(null);

  useEffect(() => {
    let active = true;
    api.get<Summary>("/kpis/summary")
      .then((response) => {
        if (active && response.data) setData(response.data);
      })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  const kpis = data?.kpis ?? KPIS;
  const timeseries = data?.timeseries ?? TIMESERIES;
  const alerts = data?.alerts ?? ALERTS;
  const provinces = data?.provinces ?? PROVINCES;
  const okNodes = provinces.filter((node) => node.status === "ok").length;

  return (
    <>
      <div className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-sm font-medium text-text-dim">
            {data?.shop.name ?? "Mây House Official"} · dữ liệu demo thống nhất
          </div>
          <h1 className="mt-2 text-5xl font-extrabold leading-[1.05] tracking-tight text-text sm:text-6xl">
            {t("Tình hình")} <span className="text-gradient">{t("cửa hàng")}</span>
          </h1>
          <p className="mt-3 max-w-2xl text-base text-text-muted">
            {data
              ? `${data.counts.products} SKU · ${data.counts.customers} khách · ${data.counts.orders} đơn · ${data.counts.reviews} đánh giá.`
              : t("Đang tải snapshot sản phẩm, khách, đơn, tồn kho và đánh giá dùng chung cho mọi feature.")}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="muted">{t("shop demo có quan hệ dữ liệu")}</Badge>
          <span className="mono text-xs text-text-muted">{okNodes}/{provinces.length} khu vực ổn định</span>
          <Button asChild size="sm" variant="primary">
            <Link href="/seller/review-intelligence"><Star className="h-3.5 w-3.5" />{t("Phân tích đánh giá")}</Link>
          </Button>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi) => <KpiCard key={kpi.id} kpi={kpi} />)}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-8"><TrafficChart data={timeseries} /></div>
        <div className="lg:col-span-4"><GeoMap nodes={provinces} /></div>
        <div className="lg:col-span-12"><AlertsTable data={alerts} /></div>
      </div>
    </>
  );
}
