"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Alert, ALERTS } from "@/lib/mock-data";
import { useT, useTf } from "@/lib/i18n";

type AlertRow = (typeof ALERTS)[number];

const severityVariant: Record<
  Alert["severity"],
  "danger" | "warning" | "info"
> = {
  critical: "danger",
  warning: "warning",
  info: "info",
};

const statusVariant: Record<
  Alert["status"],
  "danger" | "warning" | "muted"
> = {
  open: "danger",
  monitoring: "warning",
  resolved: "muted",
};

const severityLabel: Record<Alert["severity"], string> = {
  critical: "Nghiêm trọng",
  warning: "Cảnh báo",
  info: "Thông tin",
};

const statusLabel: Record<Alert["status"], string> = {
  open: "Đang mở",
  monitoring: "Đang theo dõi",
  resolved: "Đã xử lý",
};

export function AlertsTable({ data }: { data: AlertRow[] }) {
  const t = useT();
  const tf = useTf();
  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>{t("Cảnh báo mới nhất")}</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            {t("Các sự kiện gần nhất cần người bán chú ý.")}
          </p>
        </div>
        <Badge variant="muted">{tf("{số_lượng} hiển thị", { số_lượng: data.length })}</Badge>
      </CardHeader>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>{t("Tính năng")}</TableHead>
            <TableHead>{t("Vùng")}</TableHead>
            <TableHead>{t("Mức độ")}</TableHead>
            <TableHead>{t("Trạng thái")}</TableHead>
            <TableHead className="text-right">{t("Bắt đầu lúc")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((a) => (
            <TableRow key={a.id}>
              <TableCell className="mono text-text">{a.id}</TableCell>
              <TableCell>
                <div className="flex flex-col">
                  <span>{a.featureLabel}</span>
                  <span className="text-xs text-text-muted">{a.message}</span>
                </div>
              </TableCell>
              <TableCell className="mono text-xs text-text-muted">{a.region}</TableCell>
              <TableCell>
                <Badge variant={severityVariant[a.severity]}>{t(severityLabel[a.severity])}</Badge>
              </TableCell>
              <TableCell>
                <Badge variant={statusVariant[a.status]}>{t(statusLabel[a.status])}</Badge>
              </TableCell>
              <TableCell className="mono text-xs text-text-muted text-right">
                {a.startedAt}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
