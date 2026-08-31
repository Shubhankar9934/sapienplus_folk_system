"use client";

import { useEffect, useState, useMemo } from "react";
import { geoPath, geoMercator, geoEqualEarth } from "d3-geo";

export function CountryShape({ iso3, className }: { iso3: string; className?: string }) {
  const [feature, setFeature] = useState<any>(null);

  useEffect(() => {
    fetch("/world.geojson")
      .then((r) => r.json())
      .then((data) => {
        const f = data.features.find(
          (d: any) =>
            d.properties.ISO_A3_EH === iso3 ||
            d.properties.ISO_A3 === iso3 ||
            d.properties.SU_A3 === iso3 ||
            d.id === iso3
        );
        if (f) setFeature(f);
      })
      .catch((err) => {
        console.error("Failed to fetch world.geojson", err);
      });
  }, [iso3]);

  const pathStr = useMemo(() => {
    if (!feature) return "";
    try {
      // fitSize to scale the projection to the given width/height box
      const projection = geoEqualEarth().fitSize([100, 100], feature);
      const generator = geoPath().projection(projection);
      return generator(feature) || "";
    } catch (e) {
      return "";
    }
  }, [feature]);

  if (!feature || !pathStr) {
    return <div className={`w-[100px] h-[100px] ${className || ""}`} />;
  }

  return (
    <svg viewBox="0 0 100 100" className={`w-full h-full ${className || ""}`}>
      <path d={pathStr} fill="currentColor" />
    </svg>
  );
}
