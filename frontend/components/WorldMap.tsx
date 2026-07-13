"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import { useRouter } from "next/navigation";
import { colorForScore, type DimCode } from "@/lib/dimensions";
import type { MapItem } from "@/lib/api";

const EMPTY_COLOR = "#16202c";

export function WorldMap({
  data,
  dim,
  height = 460,
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
  const dataRef = useRef(data);
  const dimRef = useRef(dim);
  dataRef.current = data;
  dimRef.current = dim;

  // Apply per-country feature-state colors for the active dimension.
  function applyColors() {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    for (const item of dataRef.current) {
      const score = item.scores[dimRef.current];
      try {
        map.setFeatureState(
          { source: "countries", id: item.iso3 },
          { color: colorForScore(dimRef.current, score), hasData: score != null }
        );
      } catch {
        /* feature not present in geometry; ignore */
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
          { id: "bg", type: "background", paint: { "background-color": "#0a0e14" } },
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
            EMPTY_COLOR,
          ],
          "fill-opacity": 0.9,
        },
      });
      map.addLayer({
        id: "country-line",
        type: "line",
        source: "countries",
        paint: { "line-color": "#0a0e14", "line-width": 0.5 },
      });
      map.addLayer({
        id: "country-hover",
        type: "line",
        source: "countries",
        paint: { "line-color": "#e6edf3", "line-width": 1.5 },
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
              `<div style="font-size:12px"><strong>${item.country}</strong><br/>${
                dimRef.current
              }: ${score ?? "—"}</div>`
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

  // Recolor when the data or dimension changes.
  useEffect(() => {
    applyColors();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, dim]);

  return (
    <div
      ref={containerRef}
      style={{ height }}
      className="w-full overflow-hidden rounded-xl border border-line"
    />
  );
}
