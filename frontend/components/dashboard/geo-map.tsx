"use client";

import { MapContainer, TileLayer, CircleMarker, Popup, Tooltip as LTooltip } from "react-leaflet";
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
        <div className="h-72 w-full overflow-hidden rounded-lg border border-border">
          <MapContainer
            center={[16.0, 108.0]}
            zoom={5}
            minZoom={4}
            maxZoom={8}
            style={{ height: "100%", width: "100%", background: "hsl(var(--bg))" }}
            attributionControl={false}
            zoomControl={false}
          >
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
              subdomains={["a", "b", "c", "d"]}
            />
            {nodes.map((n) => (
              <CircleMarker
                key={n.id}
                center={[n.lat, n.lng]}
                radius={n.status === "critical" ? 8 : 6}
                pathOptions={{
                  color: statusColor[n.status],
                  fillColor: statusColor[n.status],
                  fillOpacity: 0.7,
                  weight: 1.5,
                }}
              >
                <LTooltip direction="top" offset={[0, -4]} opacity={1}>
                  <span className="mono">{n.name}</span>
                </LTooltip>
                <Popup>
                  <div className="mono text-xs">
                    <div className="font-semibold">{n.name}</div>
                    <div>Mức rủi ro: {(n.load * 100).toFixed(0)}%</div>
                    <div>Trạng thái: {statusLabel[n.status]}</div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
      </div>
    </Card>
  );
}
