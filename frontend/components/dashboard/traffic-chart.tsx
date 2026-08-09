"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const SERIES = [
  { key: "fashion",     color: "hsl(var(--series-1))", label: "Thời trang" },
  { key: "beauty",      color: "hsl(var(--series-2))", label: "Mỹ phẩm" },
  { key: "accessories", color: "hsl(var(--series-3))", label: "Phụ kiện" },
] as const;

export function TrafficChart({
  data,
}: {
  data: Array<{ t: string; fashion: number; beauty: number; accessories: number }>;
}) {
  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Doanh thu hàng hóa — 24 giờ gần nhất</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            Triệu ₫ theo giờ, phân nhóm theo ngành hàng.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-text-muted">
          {SERIES.map((s) => (
            <span key={s.key} className="inline-flex items-center gap-1.5">
              <span
                className="h-2 w-2 rounded-sm"
                style={{ backgroundColor: s.color }}
              />
              {s.label}
            </span>
          ))}
          <Badge variant="live">
            <span className="live-dot" />
            trực tiếp
          </Badge>
        </div>
      </CardHeader>
      <div className="px-5 pb-5">
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="t"
                stroke="hsl(var(--text-dim))"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                interval={2}
                className="mono"
              />
              <YAxis
                stroke="hsl(var(--text-dim))"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                className="mono"
              />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--surface-2))",
                  border: "1px solid hsl(var(--border-strong))",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                labelStyle={{ color: "hsl(var(--text-muted))" }}
                itemStyle={{ color: "hsl(var(--text))" }}
                formatter={(value: number) => [`${value}M ₫`, ""]}
              />
              {SERIES.map((s) => (
                <Line
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  stroke={s.color}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 3 }}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Card>
  );
}
