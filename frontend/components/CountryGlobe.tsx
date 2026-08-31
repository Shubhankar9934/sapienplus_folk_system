"use client";

import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { useRouter } from "next/navigation";
import gsap from "gsap";
import { useIsDark } from "@/hooks/use-theme";
import { useMap } from "@/lib/api";
import type { DimCode } from "@/lib/dimensions";
import type { MapItem } from "@/lib/api";

// Dynamic import for the globe (browser-only)
import dynamic from "next/dynamic";

const GlobeGL = dynamic(() => import("react-globe.gl"), { ssr: false });

// ─── TopoJSON numeric ID → ISO3 lookup ────────────────────────────────────
// World-atlas uses numeric ISO 3166-1 codes as feature IDs.
// FOLK API uses ISO3 alpha-3 codes. This map bridges them.
// Source: https://en.wikipedia.org/wiki/ISO_3166-1
const NUMERIC_TO_ISO3: Record<number, string> = {
  4: "AFG",
  8: "ALB",
  12: "DZA",
  20: "AND",
  24: "AGO",
  32: "ARG",
  36: "AUS",
  40: "AUT",
  50: "BGD",
  56: "BEL",
  64: "BTN",
  68: "BOL",
  76: "BRA",
  100: "BGR",
  104: "MMR",
  116: "KHM",
  120: "CMR",
  124: "CAN",
  140: "CAF",
  144: "LKA",
  152: "CHL",
  156: "CHN",
  170: "COL",
  178: "COG",
  180: "COD",
  188: "CRI",
  191: "HRV",
  192: "CUB",
  196: "CYP",
  203: "CZE",
  208: "DNK",
  214: "DOM",
  218: "ECU",
  818: "EGY",
  222: "SLV",
  231: "ETH",
  246: "FIN",
  250: "FRA",
  266: "GAB",
  276: "DEU",
  288: "GHA",
  300: "GRC",
  320: "GTM",
  332: "HTI",
  340: "HND",
  348: "HUN",
  356: "IND",
  360: "IDN",
  364: "IRN",
  368: "IRQ",
  372: "IRL",
  376: "ISR",
  380: "ITA",
  388: "JAM",
  392: "JPN",
  400: "JOR",
  398: "KAZ",
  404: "KEN",
  408: "PRK",
  410: "KOR",
  414: "KWT",
  418: "LAO",
  422: "LBN",
  430: "LBR",
  434: "LBY",
  440: "LTU",
  442: "LUX",
  458: "MYS",
  466: "MLI",
  484: "MEX",
  496: "MNG",
  504: "MAR",
  508: "MOZ",
  516: "NAM",
  524: "NPL",
  528: "NLD",
  554: "NZL",
  558: "NIC",
  566: "NGA",
  578: "NOR",
  586: "PAK",
  591: "PAN",
  598: "PNG",
  600: "PRY",
  604: "PER",
  608: "PHL",
  616: "POL",
  620: "PRT",
  634: "QAT",
  642: "ROU",
  643: "RUS",
  682: "SAU",
  686: "SEN",
  694: "SLE",
  706: "SOM",
  710: "ZAF",
  724: "ESP",
  729: "SDN",
  752: "SWE",
  756: "CHE",
  760: "SYR",
  762: "TJK",
  764: "THA",
  788: "TUN",
  792: "TUR",
  800: "UGA",
  804: "UKR",
  784: "ARE",
  826: "GBR",
  840: "USA",
  858: "URY",
  860: "UZB",
  862: "VEN",
  704: "VNM",
  887: "YEM",
  894: "ZMB",
  716: "ZWE",
  51: "ARM",
  31: "AZE",
  112: "BLR",
  70: "BIH",
  84: "BLZ",
  204: "BEN",
  60: "BMU",
  72: "BWA",
  96: "BRN",
  108: "BDI",
  132: "CPV",
  136: "CYM",
  148: "TCD",
  174: "COM",
  175: "MYT",
  184: "COK",
  212: "DMA",
  232: "ERI",
  233: "EST",
  238: "FLK",
  242: "FJI",
  260: "ATF",
  270: "GMB",
  308: "GRD",
  324: "GIN",
  328: "GUY",
  336: "VAT",
  352: "ISL",
  454: "MWI",
  478: "MRT",
  480: "MUS",
  492: "MCO",
  498: "MDA",
  499: "MNE",
  520: "NRU",
  532: "ANT",
  548: "VUT",
  562: "NER",
  570: "NIU",
  585: "PLW",
  626: "TLS",
  638: "REU",
  646: "RWA",
  659: "KNA",
  662: "LCA",
  670: "VCT",
  678: "STP",
  702: "SGP",
  703: "SVK",
  705: "SVN",
  740: "SUR",
  748: "SWZ",
  768: "TGO",
  776: "TON",
  780: "TTO",
  795: "TKM",
  798: "TUV",
  834: "TZA",
  882: "WSM",
};

// ─── Types ─────────────────────────────────────────────────────────────────
type CountryProps = {
  name: string;
  iso_a2?: string;
  iso_a3?: string;
  continent?: string;
  [k: string]: unknown;
};

export type CountryFeature = {
  type: "Feature";
  id?: string | number;
  geometry: { type: string; coordinates: unknown[] };
  properties: CountryProps | null;
};

export type SelectionInfo = {
  country: CountryFeature;
  neighbors: CountryFeature[];
  iso3: string | null;
};

const WORLD_TOPO_URL =
  "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

// Score → color scale
function scoreToColor(
  score: number | null | undefined,
  isDark: boolean,
): string {
  if (score === null || score === undefined) {
    // light mode: same flat salmon for no-data countries
    return isDark ? "#2a2d32" : "#F2B8AD";
  }
  const t = Math.max(0, Math.min(1, score / 100));
  if (isDark) {
    // dark mode: muted base → vivid red highlight
    const r = Math.round(58 + t * 165);
    const g = Math.round(61 + t * -37);
    const b = Math.round(66 + t * -6);
    return `rgb(${r},${g},${b})`;
  } else {
    // light mode: flat soft salmon-pink (matches reference image)
    // slight variation by score but stays in the peach-salmon range
    const r = Math.round(242 + t * -10);
    const g = Math.round(184 + t * -20);
    const b = Math.round(173 + t * -20);
    return `rgb(${r},${g},${b})`;
  }
}

// ─── Imperative handle exposed to parent ───────────────────────────────────
export interface CountryGlobeHandle {
  triggerZoomNavigate: (iso3: string) => void;
}

interface CountryGlobeProps {
  onSelect: (info: SelectionInfo | null) => void;
  selectedName: string | null;
  dim?: DimCode;
  staticMode?: boolean;
}

export const CountryGlobe = forwardRef<CountryGlobeHandle, CountryGlobeProps>(
  function CountryGlobe(
    {
      onSelect,
      selectedName,
      dim = "D1",
      staticMode = false,
    }: CountryGlobeProps,
    ref,
  ) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<{
    pointOfView: (pov: object, ms: number) => void;
    controls: () => {
      autoRotate: boolean;
      autoRotateSpeed: number;
      enableZoom: boolean;
    };
  } | null>(null);
  const [features, setFeatures] = useState<CountryFeature[]>([]);
  const [neighborsMap, setNeighborsMap] = useState<Map<number, number[]>>(
    new Map(),
  );
  const [size, setSize] = useState({ w: 800, h: 800 });
  const [hovered, setHovered] = useState<CountryFeature | null>(null);
  const [mouse, setMouse] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [zooming, setZooming] = useState(false);
  const isDark = useIsDark();
  const router = useRouter();

  // FOLK real map data
  const { data: mapData } = useMap();
  const scoreByIso3 = useMemo(() => {
    if (!mapData) return new Map<string, number | null>();
    return new Map(
      mapData.map((item: MapItem) => [item.iso3, item.scores[dim] ?? null]),
    );
  }, [mapData, dim]);

  // Load topology
  useEffect(() => {
    let mounted = true;
    fetch(WORLD_TOPO_URL)
      .then((r) => r.json())
      .then(async (topo) => {
        if (!mounted) return;
        const { feature, neighbors } = await import("topojson-client");
        const geo = topo.objects.countries;
        const fc = feature(topo, geo) as unknown as {
          features: CountryFeature[];
        };
        const nbrs = neighbors(geo.geometries as never[]);
        const map = new Map<number, number[]>();
        nbrs.forEach((arr: number[], i: number) => map.set(i, arr));
        setFeatures(fc.features);
        setNeighborsMap(map);
      })
      .catch((e) => console.error("Failed to load world atlas", e));
    return () => {
      mounted = false;
    };
  }, []);

  // Resize observer
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const r = el.getBoundingClientRect();
      setSize({ w: r.width, h: r.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Config globe on mount + GSAP intro
  useEffect(() => {
    const g = globeRef.current;
    if (!g || features.length === 0) return;
    const controls = g.controls() as any;
    controls.autoRotate = !staticMode;
    controls.autoRotateSpeed = 0.5;
    controls.enableZoom = false;
    if (staticMode && controls) controls.enableRotate = false;
    g.pointOfView({ lat: 20, lng: 20, altitude: 2.2 }, 0);
    gsap.fromTo(
      wrapRef.current,
      { opacity: 0, scale: 0.92 },
      { opacity: 1, scale: 1, duration: 1.2, ease: "power3.out" },
    );
  }, [features.length, staticMode]);

  // Fly to selected country
  useEffect(() => {
    const g = globeRef.current;
    if (!g || !selectedName) return;
    const feat = features.find((f) => f.properties?.name === selectedName);
    if (!feat) return;
    const centroid = getCentroid(feat);
    if (!centroid) return;
    // zoom in closer if static mode, and do it instantly or quickly
    g.pointOfView(
      { lat: centroid[1], lng: centroid[0], altitude: staticMode ? 1.5 : 1.7 },
      staticMode ? 0 : 1400,
    );
  }, [selectedName, features]);

  const selectedFeature = useMemo(
    () => features.find((f) => f.properties?.name === selectedName) ?? null,
    [features, selectedName],
  );

  const neighborNames = useMemo(() => {
    if (!selectedFeature) return new Set<string>();
    const idx = features.indexOf(selectedFeature);
    const nb = neighborsMap.get(idx) ?? [];
    return new Set(
      nb.map((i) => features[i]?.properties?.name).filter(Boolean) as string[],
    );
  }, [selectedFeature, features, neighborsMap]);

  // Color each country by its real FOLK score
  const capColor = (f: object) => {
    const feat = f as CountryFeature;
    const name = feat.properties?.name;
    if (name && name === selectedName) return isDark ? "#ffffff" : "#0e1420";
    if (name && neighborNames.has(name)) return isDark ? "#E14B3C" : "#e58877";
    if (feat === hovered) return isDark ? "#E14B3C" : "#eaa294";
    // Look up real score via numeric ID → iso3
    const numId =
      typeof feat.id === "string" ? parseInt(feat.id) : (feat.id as number);
    const iso3 = NUMERIC_TO_ISO3[numId];
    const score = iso3 ? scoreByIso3.get(iso3) : undefined;
    return scoreToColor(score, isDark);
  };

  const SIDE_COLOR = isDark ? "#1a1c20" : "#b8bfc2";
  const STROKE_COLOR = isDark ? "#0E0E10" : "#eef1f2";
  const ATMO_COLOR = isDark ? "#E14B3C" : "#e4e8ea";

  // Real Three.js material — matches world-blend's approach exactly
  const globeMaterial = useMemo(
    () =>
      new THREE.MeshPhongMaterial({
        color: new THREE.Color(isDark ? "#1a1c20" : "#cfd6d9"),
        shininess: isDark ? 8 : 4,
        specular: new THREE.Color(isDark ? "#2a2d32" : "#ffffff"),
      }),
    [isDark],
  );

  // ── Click: select only (zoom globe to country, highlight neighbors, no navigation) ──
  const handlePolygonClick = (d: object) => {
    const feat = d as CountryFeature;
    const name = feat.properties?.name;
    if (!name) return;
    const idx = features.indexOf(feat);
    const nbIdx = neighborsMap.get(idx) ?? [];
    const nbFeatures = nbIdx.map((i) => features[i]).filter(Boolean);
    const g = globeRef.current;
    const centroid = getCentroid(feat);

    // Resolve ISO3
    const numId =
      typeof feat.id === "string" ? parseInt(feat.id) : (feat.id as number);
    const iso3 = NUMERIC_TO_ISO3[numId] ?? null;

    // Select country (highlights it, shows card)
    onSelect({ country: feat, neighbors: nbFeatures, iso3 });

    // Zoom globe to center on country — no page navigation
    if (g) {
      const controls = g.controls();
      controls.autoRotate = false;
      if (centroid) {
        g.pointOfView(
          { lat: centroid[1], lng: centroid[0], altitude: 1.7 },
          1200,
        );
      }
    }
  };

  // ── Imperative handle: parent card button calls this to trigger zoom + navigate ──
  useImperativeHandle(ref, () => ({
    triggerZoomNavigate: (iso3: string) => {
      const g = globeRef.current;
      const feat = features.find((f) => f.properties?.name === selectedName);
      const centroid = feat ? getCentroid(feat) : null;

      if (g && centroid) {
        const controls = g.controls();
        controls.autoRotate = false;
        setZooming(true);
        g.pointOfView(
          { lat: centroid[1], lng: centroid[0], altitude: 0.35 },
          900,
        );
        gsap.to(wrapRef.current, {
          scale: 1.4,
          opacity: 0,
          duration: 1.0,
          delay: 0.3,
          ease: "power3.in",
          onComplete: () => {
            router.push(`/country/${iso3}`);
          },
        });
      } else {
        router.push(`/country/${iso3}`);
      }
    },
  }), [features, selectedName, router]);

  // Hover score for tooltip
  const hoveredIso3 = useMemo(() => {
    if (!hovered) return null;
    const numId =
      typeof hovered.id === "string"
        ? parseInt(hovered.id)
        : (hovered.id as number);
    return NUMERIC_TO_ISO3[numId] ?? null;
  }, [hovered]);
  const hoveredScore = hoveredIso3 ? scoreByIso3.get(hoveredIso3) : undefined;

  return (
    <div
      ref={wrapRef}
      className="absolute inset-0"
      onMouseMove={(e) => {
        const rect = wrapRef.current?.getBoundingClientRect();
        if (!rect) return;
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        setMouse({ x: mx, y: my });

        if (staticMode) return;
        const g = globeRef.current;
        if (!g) return;
        const controls = g.controls();
        if (!controls) return;

        const cx = size.w / 2;
        const cy = size.h / 2;
        const dist = Math.hypot(mx - cx, my - cy);
        const globeRadius = Math.min(size.w, size.h) * 0.32;
        const isOverGlobe = dist <= globeRadius || hovered !== null;

        controls.enableZoom = isOverGlobe;
      }}
      onMouseLeave={() => {
        setHovered(null);
        const g = globeRef.current;
        if (g) {
          const controls = g.controls();
          if (controls) {
            controls.enableZoom = false;
            controls.autoRotate = !zooming;
          }
        }
      }}
    >
      <GlobeGL
        ref={globeRef as never}
        width={size.w}
        height={size.h}
        backgroundColor="rgba(0,0,0,0)"
        showAtmosphere={!staticMode}
        atmosphereColor={ATMO_COLOR}
        atmosphereAltitude={0.15}
        globeMaterial={globeMaterial}
        showGraticules={false}
        polygonsData={features}
        polygonAltitude={(d) =>
          (d as CountryFeature).properties?.name === selectedName ? 0.02 : (staticMode ? 0.001 : 0.006)
        }
        polygonCapColor={capColor}
        polygonSideColor={() => SIDE_COLOR}
        polygonStrokeColor={() => STROKE_COLOR}
        onPolygonHover={(d) => {
          if (staticMode) return;
          const feat = (d as CountryFeature) ?? null;
          if (feat) setHovered(feat);
          else setHovered(null);
          const controls = globeRef.current?.controls();
          if (controls) {
            controls.autoRotate = !feat && !zooming;
            if (feat) controls.enableZoom = true;
          }
          if (wrapRef.current)
            wrapRef.current.style.cursor = d ? "pointer" : "grab";
        }}
        onPolygonClick={(d) => {
          if (staticMode) return;
          handlePolygonClick(d);
        }}
      />
      {hovered && hovered.properties?.name !== selectedName && (
        <div
          className="absolute z-50 w-52 -translate-x-1/2 -translate-y-[calc(100%+14px)] pointer-events-none rounded-md bg-ink p-3 text-white shadow-xl"
          style={{ left: mouse.x, top: mouse.y }}
        >
          <p className="font-display text-base leading-none">
            {(hovered.properties?.name ?? "").toUpperCase()}
          </p>
          {hovered.properties?.continent && (
            <p className="mt-1 text-[10px] uppercase tracking-wider text-white/60">
              {hovered.properties.continent as string}
            </p>
          )}
          <div className="mt-2 flex items-center justify-between text-[10px] text-white/70">
            <span className="uppercase tracking-wider">{dim} Score</span>
            <span className="font-semibold text-[#E14B3C]">
              {hoveredScore !== null && hoveredScore !== undefined
                ? hoveredScore.toFixed(0)
                : "—"}
            </span>
          </div>
          <p className="mt-1.5 text-[10px] leading-snug text-white/55">
            Click to select
          </p>
        </div>
      )}
    </div>
  );
});

// Simple centroid: average of first ring for polygon or largest polygon of multi.
function getCentroid(feat: CountryFeature): [number, number] | null {
  const g = feat.geometry;
  let ring: number[][] | null = null;
  if (g.type === "Polygon") ring = (g.coordinates as number[][][])[0];
  else if (g.type === "MultiPolygon") {
    let best: number[][] = [];
    for (const poly of g.coordinates as number[][][][]) {
      if (poly[0].length > best.length) best = poly[0];
    }
    ring = best;
  }
  if (!ring || ring.length === 0) return null;
  let lng = 0,
    lat = 0;
  for (const [x, y] of ring) {
    lng += x;
    lat += y;
  }
  return [lng / ring.length, lat / ring.length];
}
