"use client";

import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { RotateCw } from "lucide-react";
import gsap from "gsap";
import Link from "next/link";
import { useStats, useMap } from "@/lib/api";
import { NavBar } from "@/components/NavBar";
import { SiteFooter } from "@/components/SiteFooter";
import { FrameworkSection } from "@/components/FrameworkSection";
import { CountryDetailSection } from "@/components/CountryDetailSection";
import { LoopMotif } from "@/components/LoopMotif";
import { GlobeSelectionCard } from "@/components/GlobeSelectionCard";
import { CartographicFlatMap } from "@/components/CartographicFlatMap";
import { WorldMap } from "@/components/WorldMap";
import { DimensionSwitcher, MapLegend } from "@/components/MapControls";
import { getSelectionInfoByIso3 } from "@/lib/geo";
import type { SelectionInfo, CountryGlobeHandle } from "@/components/CountryGlobe";
import type { DimCode } from "@/lib/dimensions";
import { DIMENSIONS } from "@/lib/dimensions";

const CountryGlobe = lazy(() =>
  import("@/components/CountryGlobe").then((m) => ({ default: m.CountryGlobe }))
);

function GlobeSkeleton() {
  return (
    <div className="flex h-full w-full items-center justify-center">
      <div className="h-72 w-72 animate-pulse rounded-full bg-muted md:h-[520px] md:w-[520px]" />
    </div>
  );
}

export default function HomePage() {
  const [globeSelection, setGlobeSelection] = useState<SelectionInfo | null>(null);
  const [flatMapSelection, setFlatMapSelection] = useState<SelectionInfo | null>(null);
  const [mounted, setMounted] = useState(false);
  const [dim, setDim] = useState<DimCode>("D1");
  const titleRef = useRef<HTMLHeadingElement>(null);
  const globeWrapRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<CountryGlobeHandle>(null);
  const { data: stats } = useStats();
  const { data: mapData } = useMap();

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!titleRef.current) return;
    gsap.fromTo(
      titleRef.current,
      { y: 40, opacity: 0 },
      { y: 0, opacity: 1, duration: 1.1, ease: "power4.out", delay: 0.2 },
    );
  }, []);

  const displayName = globeSelection?.country.properties?.name ?? "The World";

  const handleCloseGlobeCard = () => {
    setGlobeSelection(null);
  };

  const handleZoomNavigate = (iso3: string) => {
    globeRef.current?.triggerZoomNavigate(iso3);
  };

  const handleFlatMapSelect = async (iso3: string) => {
    const info = await getSelectionInfoByIso3(iso3);
    if (info) {
      setFlatMapSelection(info);
    }
  };

  return (
    <>
      <NavBar />
      <main className="relative w-full bg-background text-foreground dark:bg-[#0E0E10] dark:text-white">
      {/* ── FRAMEWORK SECTION (1ST SECTION) ────────────────────────────── */}
      <FrameworkSection />

      {/* ── GLOBE HERO SECTION (2ND SECTION - FULL SCREEN HEIGHT) ─────── */}
      <section
        id="globe"
        className="relative h-screen min-h-[650px] w-full overflow-hidden bg-background dark:bg-[#0E0E10] dark:text-white"
      >
        {/* Faint loop motif — dark-mode only */}
        <div className="hidden dark:block">
          <LoopMotif className="-right-40 top-10 h-[520px] w-[520px] text-white" />
        </div>

        {/* Eyebrow */}
        <div className="pointer-events-none absolute inset-x-0 top-6 z-20 flex justify-center">
          <p
            className="uppercase text-foreground/70 dark:text-[#E14B3C]"
            style={{ fontSize: "13px", fontWeight: 600, letterSpacing: "0.08em" }}
          >
            Where does culture meet the world?
          </p>
        </div>

        {/* Big title */}
        <div className="pointer-events-none absolute inset-x-0 top-12 z-10 flex justify-center md:top-16">
          <h1
            ref={titleRef}
            className="font-display text-center text-[16vw] leading-[0.82] text-ink dark:text-white md:text-[13vw] lg:text-[11rem]"
          >
            {displayName}
          </h1>
        </div>

        {/* Stats counter — top right */}
        <div className="pointer-events-none absolute right-6 top-6 z-20 hidden text-right md:block">
          <p className="text-xs text-foreground/70 dark:text-white/70">
            Countries indexed:{" "}
            <span className="ml-1 rounded-sm bg-coral/40 px-2 py-1 text-base font-semibold text-coral-strong dark:bg-[#E14B3C]/20 dark:text-[#E14B3C]">
              {stats?.countries ?? "—"}
            </span>
          </p>
          <p className="mt-1 text-[10px] text-coral-strong/80 dark:text-[#E14B3C]/80">
            across 4 dimensions
          </p>
        </div>

        {/* Dimension pill switcher */}
        <div className="absolute left-6 top-6 z-20 hidden gap-1 md:flex">
          {DIMENSIONS.map((d) => (
            <button
              key={d.code}
              onClick={() => setDim(d.code)}
              className={`rounded-sm px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider transition-colors ${
                dim === d.code
                  ? "text-white"
                  : "bg-ink/5 text-ink/50 hover:bg-ink/10 dark:bg-white/5 dark:text-white/40 dark:hover:bg-white/10"
              }`}
              style={dim === d.code ? { backgroundColor: d.color } : {}}
            >
              {d.code} {d.label}
            </button>
          ))}
        </div>

        {/* Globe */}
        <div
          ref={globeWrapRef}
          className="absolute inset-x-0 top-[6vw] bottom-0 z-20 md:top-[4vw]"
        >
          {mounted && (
            <Suspense fallback={<GlobeSkeleton />}>
              <CountryGlobe
                ref={globeRef}
                selectedName={globeSelection?.country.properties?.name ?? null}
                onSelect={setGlobeSelection}
                dim={dim}
              />
            </Suspense>
          )}
          {!mounted && <GlobeSkeleton />}
        </div>

        {/* Floating Globe Selection Card — shows ONLY on globe click */}
        {globeSelection && (
          <div className="pointer-events-none absolute inset-0 z-30 flex items-center justify-end pr-8 md:pr-14">
            <div className="pointer-events-auto">
              <GlobeSelectionCard
                selection={globeSelection}
                dim={dim}
                onClose={handleCloseGlobeCard}
                onZoomNavigate={handleZoomNavigate}
              />
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="absolute bottom-8 left-6 z-30 md:bottom-14 md:left-14">
          <div className="flex items-center gap-3 text-xs text-muted-foreground dark:text-white/60">
            <span className="flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full bg-muted dark:bg-white/20" />
              No data
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full bg-coral" />
              Low score
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full bg-coral-strong" />
              High score
            </span>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <a
              href="#explore-map"
              className="rounded-sm bg-ink px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white transition hover:opacity-90 dark:bg-white dark:text-[#0E0E10]"
            >
              Explore Map
            </a>
            <Link
              href="/world-rankings"
              className="rounded-sm border border-ink/20 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-ink transition hover:border-ink/40 dark:border-white/20 dark:text-white dark:hover:border-white/40"
            >
              Rankings
            </Link>
          </div>
        </div>

        {/* Rotate hint */}
        <div className="absolute bottom-8 right-6 z-30 hidden items-center gap-3 md:bottom-14 md:right-14 md:flex">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-ink text-background dark:bg-white dark:text-[#0E0E10]">
            <RotateCw className="h-4 w-4" strokeWidth={2.5} />
          </div>
          <span className="text-sm text-foreground dark:text-white">Drag to rotate</span>
        </div>
      </section>

      {/* ── EXPLORE FLATMAP SECTION (3RD SECTION RIGHT AFTER GLOBE) ──────── */}
      <section
        id="explore-map"
        className="relative w-full border-t border-neutral-200 bg-white px-6 py-16 dark:border-white/10 dark:bg-[#06080C] md:px-16 md:py-24"
      >
        <div className="mx-auto max-w-7xl">
          <CartographicFlatMap
            data={mapData ?? []}
            dim={dim}
            onDimChange={setDim}
            onSelect={handleFlatMapSelect}
          />
        </div>
      </section>

      {/* ── COUNTRY DETAIL SECTION (SHOWS ONLY WHEN CLICKING ON THE FLAT MAP) ─────── */}
      {flatMapSelection && (
        <div id="flatmap-detail" className="relative w-full">
          <CountryDetailSection selection={flatMapSelection} />
        </div>
      )}

      {/* ── STATS BAND ────────────────────────────────────────────────── */}
      <section className="border-t border-ink/8 bg-background px-6 py-16 dark:border-white/8 dark:bg-[#0E0E10] md:px-16">
        <div className="mx-auto max-w-5xl">
          <p
            className="uppercase text-ink/60 dark:text-[#E14B3C]"
            style={{ fontSize: "11px", fontWeight: 600, letterSpacing: "0.22em" }}
          >
            Platform Stats
          </p>
          <div className="mt-8 grid grid-cols-2 gap-8 md:grid-cols-4">
            {[
              { label: "Countries", value: stats?.countries ?? "—" },
              { label: "Frameworks", value: stats?.frameworks ?? 5 },
              { label: "Evidence Sources", value: stats?.evidence_sources ?? "—" },
              { label: "Research Grade", value: stats?.research_grade ?? "A" },
            ].map((s) => (
              <div key={s.label}>
                <div className="font-display text-4xl text-ink dark:text-white md:text-5xl">
                  {s.value}
                </div>
                <div
                  className="mt-2 uppercase text-ink/60 dark:text-white/50"
                  style={{ fontSize: "11px", letterSpacing: "0.15em" }}
                >
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
    <SiteFooter />
    </>
  );
}


