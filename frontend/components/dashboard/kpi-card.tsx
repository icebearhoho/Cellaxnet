"use client";

import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import type { Kpi } from "@/lib/mock-data";

const VND = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});

function formatValue(kpi: Kpi): string {
  if (kpi.unit === "₫") {
    return VND.format(kpi.value).replace(/\s*₫/g, "");
  }
  if (kpi.unit === "%") {
    return kpi.value.toFixed(2);
  }
  if (kpi.value >= 1000) {
    return kpi.value.toLocaleString("vi-VN");
  }
  return String(kpi.value);
}

export function KpiCard({ kpi }: { kpi: Kpi }) {
  const positive = kpi.delta >= 0;
  // For AOV, churn proxy, return rate — down is good. Toggle using kpi.id.
  const inverted = !!kpi.inverted;
  const goodWhenDown = inverted;
  const isGood = goodWhenDown ? !positive : positive;

  return (
    <div className="rounded-[10px] border border-border bg-surface p-5 transition-colors hover:border-border-strong">
      <div className="flex items-center justify-between">
        <span className="text-2xs uppercase tracking-wider text-text-muted">
          {kpi.label}
        </span>
        <span
          className={cn(
            "mono inline-flex items-center gap-1 text-xs",
            isGood ? "text-success" : "text-danger",
          )}
        >
          {positive ? (
            <ArrowUpRight className="h-3 w-3" />
          ) : (
            <ArrowDownRight className="h-3 w-3" />
          )}
          {Math.abs(kpi.delta).toFixed(1)}%
        </span>
      </div>

      <div className="mt-2 flex items-baseline gap-1.5">
        <span className="mono text-4xl font-medium text-text" data-tnum>
          {formatValue(kpi)}
        </span>
        {kpi.unit && (
          <span className="mono text-base text-text-muted">{kpi.unit}</span>
        )}
      </div>

      <div className="mt-3 h-10 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={kpi.spark.map((v, i) => ({ i, v }))}>
            <defs>
              <linearGradient id={`spark-${kpi.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity={0.4} />
                <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="v"
              stroke="hsl(var(--accent))"
              strokeWidth={1.5}
              fill={`url(#spark-${kpi.id})`}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
