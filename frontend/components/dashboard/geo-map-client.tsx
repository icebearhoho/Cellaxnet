"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import type { PROVINCES } from "@/lib/mock-data";

/**
 * Client-only wrapper around <GeoMap> so that react-leaflet (which
 * touches `window` at module init) is never evaluated during SSR.
 */
const LazyGeoMap = dynamic(
  () => import("@/components/dashboard/geo-map").then((m) => m.GeoMap),
  { ssr: false, loading: () => <GeoMapSkeleton /> },
);

function GeoMapSkeleton() {
  return (
    <div className="h-72 w-full animate-pulse rounded-lg border border-border bg-surface-2" />
  );
}

export type GeoMapClientProps = { nodes: typeof PROVINCES };

export function GeoMap({ nodes }: GeoMapClientProps) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // React Strict Mode performs a setup/cleanup probe in development. Waiting
    // one frame means that probe is cancelled before Leaflet receives a DOM
    // node, preventing two map instances from claiming the same container.
    const frame = window.requestAnimationFrame(() => setReady(true));
    return () => window.cancelAnimationFrame(frame);
  }, []);

  return ready ? <LazyGeoMap nodes={nodes} /> : <GeoMapSkeleton />;
}
