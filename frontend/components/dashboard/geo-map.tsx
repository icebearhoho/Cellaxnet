"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import type { PROVINCES, ProvinceNode } from "@/lib/mock-data";
import { useT, useTf } from "@/lib/i18n";

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
  const t = useT();
  const tf = useTf();
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    // Leaflet stores initialization state on its container. A fresh child for
    // every effect run makes this safe under Strict Mode and Fast Refresh.
    const container = document.createElement("div");
    container.style.height = "100%";
    container.style.width = "100%";
    container.style.background = "hsl(var(--bg))";
    host.replaceChildren(container);

    const map = L.map(container, {
      attributionControl: false,
      zoomControl: false,
      minZoom: 4,
      maxZoom: 8,
    }).setView([16.0, 108.0], 5);

    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: ["a", "b", "c", "d"],
    }).addTo(map);

    nodes.forEach((node) => {
      const marker = L.circleMarker([node.lat, node.lng], {
        radius: node.status === "critical" ? 8 : 6,
        color: statusColor[node.status],
        fillColor: statusColor[node.status],
        fillOpacity: 0.7,
        weight: 1.5,
      }).addTo(map);

      marker.bindTooltip(node.name, { direction: "top", offset: [0, -4], opacity: 1 });

      const popup = document.createElement("div");
      popup.className = "mono text-xs";
      const name = document.createElement("div");
      name.className = "font-semibold";
      name.textContent = node.name;
      const risk = document.createElement("div");
      risk.textContent = tf("Mức rủi ro: {phần_trăm}%", {
        phần_trăm: (node.load * 100).toFixed(0),
      });
      const state = document.createElement("div");
      state.textContent = tf("Trạng thái: {trạng_thái}", {
        trạng_thái: t(statusLabel[node.status]),
      });
      popup.append(name, risk, state);
      marker.bindPopup(popup);
    });

    return () => {
      map.remove();
      container.remove();
    };
  }, [nodes, t, tf]);

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>{t("Chuỗi cung ứng — 63 tỉnh thành")}</CardTitle>
          <p className="mt-1 text-xs text-text-muted">
            {t("Rủi ro vận hành theo kho vùng (màu = mức độ cảnh báo).")}
          </p>
        </div>
        <div className="flex items-center gap-3 text-2xs uppercase tracking-wider text-text-muted">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" /> {t("ổn định")}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-warning" /> {t("cảnh báo")}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-danger" /> {t("rủi ro")}
          </span>
        </div>
      </CardHeader>
      <div className="px-5 pb-5">
        <div ref={hostRef} className="h-72 w-full overflow-hidden rounded-lg border border-border" />
      </div>
    </Card>
  );
}
