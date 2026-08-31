"use client";

import { useEffect, useMemo, useRef } from "react";
import { geoMercator, geoPath } from "d3-geo";
import gsap from "gsap";
import { ChevronDown, ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import type { CountryFeature, SelectionInfo } from "./CountryGlobe";
import { useCountry } from "@/lib/api";
import type { DimCode } from "@/lib/dimensions";
import { DIMENSIONS } from "@/lib/dimensions";

// ─── Numeric → ISO3 (same map as CountryGlobe) ────────────────────────────
const NUMERIC_TO_ISO3: Record<number, string> = {
  4: "AFG", 8: "ALB", 12: "DZA", 20: "AND", 24: "AGO", 32: "ARG", 36: "AUS",
  40: "AUT", 50: "BGD", 56: "BEL", 64: "BTN", 68: "BOL", 76: "BRA", 100: "BGR",
  104: "MMR", 116: "KHM", 120: "CMR", 124: "CAN", 140: "CAF", 144: "LKA",
  152: "CHL", 156: "CHN", 170: "COL", 178: "COG", 180: "COD", 188: "CRI",
  191: "HRV", 192: "CUB", 196: "CYP", 203: "CZE", 208: "DNK", 214: "DOM",
  218: "ECU", 818: "EGY", 222: "SLV", 231: "ETH", 246: "FIN", 250: "FRA",
  266: "GAB", 276: "DEU", 288: "GHA", 300: "GRC", 320: "GTM", 332: "HTI",
  340: "HND", 348: "HUN", 356: "IND", 360: "IDN", 364: "IRN", 368: "IRQ",
  372: "IRL", 376: "ISR", 380: "ITA", 388: "JAM", 392: "JPN", 400: "JOR",
  398: "KAZ", 404: "KEN", 408: "PRK", 410: "KOR", 414: "KWT", 418: "LAO",
  422: "LBN", 430: "LBR", 434: "LBY", 440: "LTU", 442: "LUX", 458: "MYS",
  466: "MLI", 484: "MEX", 496: "MNG", 504: "MAR", 508: "MOZ", 516: "NAM",
  524: "NPL", 528: "NLD", 554: "NZL", 558: "NIC", 566: "NGA", 578: "NOR",
  586: "PAK", 591: "PAN", 598: "PNG", 600: "PRY", 604: "PER", 608: "PHL",
  616: "POL", 620: "PRT", 634: "QAT", 642: "ROU", 643: "RUS", 682: "SAU",
  686: "SEN", 694: "SLE", 706: "SOM", 710: "ZAF", 724: "ESP", 729: "SDN",
  752: "SWE", 756: "CHE", 760: "SYR", 762: "TJK", 764: "THA", 788: "TUN",
  792: "TUR", 800: "UGA", 804: "UKR", 784: "ARE", 826: "GBR", 840: "USA",
  858: "URY", 860: "UZB", 862: "VEN", 704: "VNM", 887: "YEM", 894: "ZMB",
  716: "ZWE",
};

const DIM_STYLES: Record<DimCode, { color: string }> = {
  D1: { color: "#3B82F6" }, // Identity - Blue
  D2: { color: "#EC4899" }, // Expression - Pink
  D3: { color: "#F59E0B" }, // Structure - Amber
  D4: { color: "#10B981" }, // Drive - Emerald
};

// ─── MiniMap SVG silhouette ───────────────────────────────────────────────
function MiniMap({ feature, size = 320 }: { feature: CountryFeature; size?: number }) {
  const path = useMemo(() => {
    try {
      const projection = geoMercator().fitSize([size, size * 0.8], feature as never);
      const p = geoPath(projection);
      return p(feature as never) ?? "";
    } catch {
      return "";
    }
  }, [feature, size]);

  return (
    <svg viewBox={`0 0 ${size} ${size * 0.8}`} className="h-full w-full overflow-visible">
      <path
        d={path}
        className="fill-[#D9D5CF] stroke-[#C3BFB8] dark:fill-white/20 dark:stroke-white/30 transition-colors duration-300 group-hover:fill-[#E14B3C]/20 group-hover:stroke-[#E14B3C]/50"
        strokeWidth={1}
      />
    </svg>
  );
}

// ─── Score Bar ────────────────────────────────────────────────────────────
function ScoreBar({
  label,
  score,
  color,
  low,
  high,
}: {
  label: string;
  score: number | null;
  color: string;
  low: string;
  high: string;
}) {
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!barRef.current) return;
    gsap.fromTo(
      barRef.current,
      { width: "0%" },
      {
        width: score !== null && score !== undefined ? `${Math.max(0, Math.min(100, score))}%` : "0%",
        duration: 0.8,
        ease: "power3.out",
      }
    );
  }, [score]);

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-neutral-900 dark:text-white">
          {label}
        </span>
        <span className="font-bold text-sm tabular-nums" style={{ color }}>
          {score !== null && score !== undefined ? Math.round(score) : "—"}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-white/10">
        <div
          ref={barRef}
          className="h-full rounded-full transition-all"
          style={{ width: "0%", backgroundColor: color }}
        />
      </div>
      <div className="flex justify-between text-[11px] font-medium text-neutral-400 dark:text-neutral-500">
        <span>{low}</span>
        <span>{high}</span>
      </div>
    </div>
  );
}

// ─── CountryCard ──────────────────────────────────────────────────────────
function CountryCard({
  feature,
  primary = false,
  onExplore,
}: {
  feature: CountryFeature;
  primary?: boolean;
  onExplore?: () => void;
}) {
  const name = feature.properties?.name ?? "";

  return (
    <div
      onClick={onExplore}
      className={`group relative flex flex-col justify-between overflow-hidden rounded-3xl p-5 transition-all duration-300 cursor-pointer min-h-[240px] ${
        primary
          ? "bg-white dark:bg-[#12141A] ring-2 ring-[#E14B3C] shadow-xl hover:shadow-2xl hover:-translate-y-1.5"
          : "bg-white/80 dark:bg-white/[0.04] border border-neutral-100 dark:border-white/5 shadow-md hover:shadow-xl hover:-translate-y-1.5 hover:border-neutral-200 dark:hover:border-white/20"
      }`}
    >
      <div className="relative aspect-[4/3] w-full flex items-center justify-center p-2">
        <MiniMap feature={feature} />
      </div>

      <div className="mt-4 flex items-end justify-between">
        <div>
          <h3 className="font-display text-2xl md:text-3xl font-black uppercase leading-none tracking-tight text-neutral-900 dark:text-white">
            {name}
          </h3>
          {primary && (
            <p className="mt-1 text-[11px] font-medium text-neutral-400 dark:text-neutral-500">
              Click to explore
            </p>
          )}
        </div>

        <button
          onClick={(e) => {
            e.stopPropagation();
            if (onExplore) onExplore();
          }}
          className={`flex h-9 w-9 items-center justify-center rounded-full transition-all duration-300 ${
            primary
              ? "bg-[#E14B3C] text-white shadow-md group-hover:scale-110"
              : "border border-neutral-200 dark:border-white/20 text-neutral-400 group-hover:border-[#E14B3C] group-hover:bg-[#E14B3C] group-hover:text-white"
          }`}
          aria-label={`Explore ${name}`}
        >
          <ArrowRight className="h-4 w-4" strokeWidth={2.5} />
        </button>
      </div>
    </div>
  );
}

// ─── CountryDetailSection ─────────────────────────────────────────────────
export function CountryDetailSection({ selection }: { selection: SelectionInfo }) {
  const ref = useRef<HTMLElement>(null);
  const router = useRouter();
  const name = selection.country.properties?.name ?? "Unknown";

  const numId =
    typeof selection.country.id === "string"
      ? parseInt(selection.country.id)
      : (selection.country.id as number);
  const iso3 = NUMERIC_TO_ISO3[numId] ?? selection.iso3 ?? "";

  const { data: profile } = useCountry(iso3);

  const regionName =
    profile?.region ??
    (selection.country.properties?.continent as string | undefined) ??
    (selection.country.properties?.subregion as string | undefined) ??
    "Region";

  const archetypeText =
    profile?.cultural_archetype?.title ??
    profile?.archetype ??
    "CULTURAL CLUSTER";

  const summaryText =
    profile?.executive_summary ??
    profile?.cultural_archetype?.summary ??
    (profile?.culture_at_a_glance && profile.culture_at_a_glance.length > 0
      ? profile.culture_at_a_glance[0]
      : `In ${name}, cultural dynamics shape social structures, identity, and community interaction.`);

  useEffect(() => {
    if (!ref.current) return;
    ref.current.scrollIntoView({ behavior: "smooth", block: "start" });
    gsap.fromTo(
      ref.current.querySelectorAll("[data-anim]"),
      { y: 30, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.7, ease: "power3.out", stagger: 0.06 }
    );
  }, [selection]);

  const goToCountry = (targetIso3: string) => {
    router.push(`/country/${targetIso3}`);
  };

  const neighbors = selection.neighbors;

  return (
    <section
      ref={ref}
      className="relative min-h-screen w-full bg-background px-6 py-12 dark:bg-[#0E0E10] md:px-10 md:py-16"
    >
      <div className="mx-auto max-w-7xl grid grid-cols-1 gap-10 lg:grid-cols-[360px_minmax(0,1fr)]">
        {/* LEFT — Profile Card (Sticky & Stylish) */}
        <div data-anim className="lg:sticky lg:top-8 lg:self-start">
          <div className="rounded-3xl border border-neutral-100 bg-white p-6 shadow-[0_20px_50px_rgba(0,0,0,0.12)] dark:border-white/10 dark:bg-[#12141A] dark:shadow-[0_24px_60px_rgba(0,0,0,0.7)]">
            {/* Header: Dot + Region & Archetype */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-[#E14B3C]" />
                <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400">
                  {regionName}
                </span>
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#E14B3C] dark:text-[#F87171]">
                {archetypeText}
              </span>
            </div>

            {/* Title: Country Name */}
            <h2 className="mt-3 font-display text-4xl md:text-5xl font-black uppercase tracking-tight text-neutral-900 dark:text-white leading-none">
              {name}
            </h2>

            {/* Summary Paragraph */}
            <p className="mt-3.5 text-xs md:text-sm leading-relaxed text-neutral-600 dark:text-neutral-300 font-normal line-clamp-4">
              {summaryText}
            </p>

            {/* 4 Colored Dimension Bars */}
            <div className="mt-6 space-y-4">
              {DIMENSIONS.map((dim) => {
                const s = profile?.scores ? profile.scores[dim.code]?.score : null;
                const color = DIM_STYLES[dim.code].color;
                return (
                  <ScoreBar
                    key={dim.code}
                    label={dim.label}
                    score={s ?? null}
                    color={color}
                    low={dim.low}
                    high={dim.high}
                  />
                );
              })}
            </div>

            {/* Footer CTA */}
            <div className="mt-6 border-t border-neutral-100 pt-4 dark:border-white/10">
              <button
                onClick={() => iso3 && goToCountry(iso3)}
                className="group flex w-full items-center justify-between rounded-xl bg-neutral-900 px-5 py-3 text-xs font-bold uppercase tracking-wider text-white transition hover:bg-[#E14B3C] dark:bg-white dark:text-[#0E0E10] dark:hover:bg-[#E14B3C] dark:hover:text-white"
              >
                <span>Explore Country Profile</span>
                <ArrowRight
                  className="h-4 w-4 transition-transform group-hover:translate-x-1"
                  strokeWidth={2.5}
                />
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT — Countries Shapes Grid */}
        <div className="flex flex-col gap-6">
          {/* Header Controls / Fingerprint Bar */}
          <div data-anim className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3 rounded-full border border-neutral-200 bg-white px-5 py-2.5 shadow-sm dark:border-white/10 dark:bg-white/[0.06]">
              <span className="h-2.5 w-2.5 rounded-full bg-[#E14B3C]" />
              <span className="font-display text-lg font-bold uppercase text-neutral-900 dark:text-white">
                {name}
              </span>
              <ChevronDown className="h-4 w-4 text-neutral-400" />
            </div>

            <div className="text-xs text-neutral-500 dark:text-neutral-400">
              <p className="font-bold uppercase tracking-wider text-neutral-900 dark:text-white">
                Cultural Fingerprint
              </p>
              <div className="mt-1 flex items-center gap-4">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-[#E14B3C]" />
                  Selected
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-neutral-400 dark:bg-neutral-600" />
                  Neighbours
                </span>
              </div>
            </div>
          </div>

          {/* Cards Grid */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {/* Selected Country Card */}
            <div data-anim>
              <CountryCard
                feature={selection.country}
                primary
                onExplore={() => iso3 && goToCountry(iso3)}
              />
            </div>

            {/* Neighbour Cards */}
            {neighbors.map((n) => {
              const nNumId = typeof n.id === "string" ? parseInt(n.id) : (n.id as number);
              const nIso3 = NUMERIC_TO_ISO3[nNumId] ?? "";
              return (
                <div data-anim key={n.properties?.name}>
                  <CountryCard
                    feature={n}
                    onExplore={() => nIso3 && goToCountry(nIso3)}
                  />
                </div>
              );
            })}

            {neighbors.length === 0 && (
              <div className="col-span-full rounded-2xl border border-dashed border-neutral-200 p-8 text-center text-sm text-neutral-500 dark:border-white/10">
                No shared land borders — an island or isolated territory.
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

