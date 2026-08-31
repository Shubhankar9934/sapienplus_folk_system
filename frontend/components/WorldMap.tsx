"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import { useRouter } from "next/navigation";
import { colorForScore, type DimCode } from "@/lib/dimensions";
import type { MapItem } from "@/lib/api";
import { useIsDark } from "@/hooks/use-theme";

function createGraticuleGeoJSON() {
  const features: any[] = [];
  // Latitude lines every 30 degrees
  for (let lat = -60; lat <= 60; lat += 30) {
    const coords: [number, number][] = [];
    for (let lng = -180; lng <= 180; lng += 5) {
      coords.push([lng, lat]);
    }
    features.push({
      type: "Feature",
      geometry: { type: "LineString", coordinates: coords },
    });
  }
  // Longitude lines every 30 degrees
  for (let lng = -150; lng <= 150; lng += 30) {
    const coords: [number, number][] = [];
    for (let lat = -85; lat <= 85; lat += 5) {
      coords.push([lng, lat]);
    }
    features.push({
      type: "Feature",
      geometry: { type: "LineString", coordinates: coords },
    });
  }
  return { type: "FeatureCollection", features };
}

export function WorldMap({
  data,
  dim,
  height = 560,
  onSelect,
}: {
  data: MapItem[];
  dim: DimCode;
  height?: number;
  onSelect?: (iso3: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const loadedRef = useRef(false);
  const router = useRouter();
  const isDark = useIsDark();

  const dataRef = useRef(data);
  const dimRef = useRef(dim);
  const isDarkRef = useRef(isDark);

  dataRef.current = data;
  dimRef.current = dim;
  isDarkRef.current = isDark;

  function applyColors() {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;

    try {
      map.setPaintProperty("bg", "background-color", isDarkRef.current ? "#06080c" : "#f8fafc");
      map.setPaintProperty("country-line", "line-color", isDarkRef.current ? "#06080c" : "#ffffff");
      map.setPaintProperty("graticule-line", "line-color", isDarkRef.current ? "#ffffff" : "#000000");
    } catch {}

    for (const item of dataRef.current) {
      const score = item.scores[dimRef.current];
      try {
        map.setFeatureState(
          { source: "countries", id: item.iso3 },
          { color: colorForScore(dimRef.current, score), hasData: score != null }
        );
      } catch {
        /* feature not present in geometry */
      }
    }
  }

  useEffect(() => {
    if (mapRef.current || !containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {},
        layers: [
          { id: "bg", type: "background", paint: { "background-color": isDark ? "#06080c" : "#f8fafc" } },
        ],
      },
      center: [12, 28],
      zoom: 1.1,
      minZoom: 0.6,
      maxZoom: 6,
      attributionControl: false,
      dragRotate: false,
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");

    map.on("load", async () => {
      // Add Graticule Grid Lines
      map.addSource("graticules", {
        type: "geojson",
        data: createGraticuleGeoJSON() as any,
      });

      map.addLayer({
        id: "graticule-line",
        type: "line",
        source: "graticules",
        paint: {
          "line-color": isDark ? "#ffffff" : "#000000",
          "line-opacity": isDark ? 0.08 : 0.12,
          "line-width": 1,
          "line-dasharray": [2, 2],
        },
      });

      map.addSource("countries", {
        type: "geojson",
        data: "/world.geojson",
        promoteId: "ISO_A3_EH",
      });

      map.addLayer({
        id: "country-fill",
        type: "fill",
        source: "countries",
        paint: {
          "fill-color": [
            "coalesce",
            ["feature-state", "color"],
            isDark ? "#374151" : "#cbd5e1",
          ],
          "fill-opacity": 0.9,
        },
      });

      map.addLayer({
        id: "country-line",
        type: "line",
        source: "countries",
        paint: { "line-color": isDark ? "#06080c" : "#ffffff", "line-width": 0.5 },
      });

      map.addLayer({
        id: "country-hover",
        type: "line",
        source: "countries",
        paint: { "line-color": isDark ? "#ffffff" : "#000000", "line-width": 1.5 },
        filter: ["==", ["get", "ISO_A3_EH"], ""],
      });

      loadedRef.current = true;
      applyColors();

      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
      });

      map.on("mousemove", "country-fill", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        const iso = (f.properties?.ISO_A3_EH as string) ?? "";
        map.setFilter("country-hover", ["==", ["get", "ISO_A3_EH"], iso]);
        const item = dataRef.current.find((d) => d.iso3 === iso);
        if (item) {
          const score = item.scores[dimRef.current];
          popup
            .setLngLat(e.lngLat)
            .setHTML(
              `<div style="font-size:12px; padding:2px"><strong>${item.country}</strong><br/>${
                dimRef.current
              }: ${score !== null && score !== undefined ? Math.round(score) : "—"}</div>`
            )
            .addTo(map);
        } else {
          popup.remove();
        }
      });

      map.on("mouseleave", "country-fill", () => {
        map.getCanvas().style.cursor = "";
        map.setFilter("country-hover", ["==", ["get", "ISO_A3_EH"], ""]);
        popup.remove();
      });

      map.on("click", "country-fill", (e) => {
        const iso = (e.features?.[0]?.properties?.ISO_A3_EH as string) ?? "";
        const item = dataRef.current.find((d) => d.iso3 === iso);
        if (!item) return;
        if (onSelect) onSelect(iso);
        else router.push(`/country/${iso}`);
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Recolor when data, dimension, or theme changes.
  useEffect(() => {
    applyColors();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, dim, isDark]);

  return (
    <div
      ref={containerRef}
      style={{ height }}
      className="w-full overflow-hidden rounded-2xl"
    />
  );
}

