"use client";

import { useEffect, useRef } from "react";
import * as L from "leaflet";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import type { PROVINCES, ProvinceNode } from "@/lib/mock-data";

const statusColor: Record<ProvinceNode["status"], string> = {
  ok: "hsl(var(--accent))",
  warn: "hsl(var(--warning))",
  critical: "hsl(var(--danger))",
};

const statusLabel: Record<ProvinceNode["status"], string> = {
  ok: "Ổn định",
  warn: "Cảnh báo",
  critical: "Rủi ro cao",
};

export function GeoMap({ nodes }: { nodes: typeof PROVINCES }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const map = L.map(container, {
      center: [16, 108],
      zoom: 5,
      minZoom: 4,
      maxZoom: 8,
      attributionControl: false,
      zoomControl: false,
    });

    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
    }).addTo(map);

    for (const node of nodes) {
      const color = statusColor[node.status];
      L.circleMarker([node.lat, node.lng], {
        radius: node.status === "critical" ? 8 : 6,
        color,
        fillColor: color,
        fillOpacity: 0.7,
        weight: 1.5,
      })
        .bindTooltip(node.name, { direction: "top", offset: [0, -4], opacity: 1 })
        .bindPopup(
          `<div class="mono text-xs"><div class="font-semibold">${node.name}</div>` +
            `<div>Mức rủi ro: ${(node.load * 100).toFixed(0)}%</div>` +
            `<div>Trạng thái: ${statusLabel[node.status]}</div></div>`,
        )
        .addTo(map);
    }

    return () => {
      map.remove();
      container.replaceChildren();
    };
  }, [nodes]);

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Chuỗi cung ứng — 63 tỉnh thành</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            Rủi ro vận hành theo kho vùng (màu = mức độ cảnh báo).
          </p>
        </div>
        <div className="flex items-center gap-3 text-2xs uppercase tracking-wider text-text-muted">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" /> ổn định
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-warning" /> cảnh báo
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-danger" /> rủi ro
          </span>
        </div>
      </CardHeader>
      <div className="px-5 pb-5">
        <div
          ref={containerRef}
          className="h-72 w-full overflow-hidden rounded-lg border border-border bg-bg"
        />
      </div>
    </Card>
  );
}
