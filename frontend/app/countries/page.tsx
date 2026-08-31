"use client";

import { useMemo, useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";
import { useCountries } from "@/lib/api";
import { NavBar } from "@/components/NavBar";
import { SiteFooter } from "@/components/SiteFooter";
import { CountryCard } from "@/components/CountryCard";
import { Spinner, EmptyState } from "@/components/ui";
import type { DimCode } from "@/lib/dimensions";
import { DIMENSIONS, DIM_BY_CODE } from "@/lib/dimensions";

const ITEMS_PER_PAGE = 9;

function getPageNumbers(current: number, total: number) {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  if (current <= 4) {
    return [1, 2, 3, 4, 5, "...", total];
  }
  if (current >= total - 3) {
    return [1, "...", total - 4, total - 3, total - 2, total - 1, total];
  }
  return [1, "...", current - 1, current, current + 1, "...", total];
}

function CountriesContent() {
  const searchParams = useSearchParams();
  const initialRegion = searchParams?.get("region") || "all";

  const { data: countries, isLoading } = useCountries();
  const [dim, setDim] = useState<DimCode>("D1");
  const [q, setQ] = useState("");
  const [region, setRegion] = useState("all");
  const [grade, setGrade] = useState("all");
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (initialRegion) {
      setRegion(initialRegion);
    }
  }, [initialRegion]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [q, region, grade, dim]);

  const regions = useMemo(
    () =>
      Array.from(
        new Set((countries ?? []).map((c) => c.region).filter(Boolean))
      ).sort() as string[],
    [countries]
  );

  const filtered = useMemo(() => {
    let list = countries ?? [];
    if (q.trim()) {
      const t = q.toLowerCase();
      list = list.filter(
        (c) => c.country.toLowerCase().includes(t) || c.iso3.toLowerCase().includes(t)
      );
    }
    if (region !== "all") list = list.filter((c) => c.region === region);
    if (grade !== "all") list = list.filter((c) => c.research_grade === grade);
    return [...list].sort((a, b) => (b.scores[dim] ?? 0) - (a.scores[dim] ?? 0));
  }, [countries, q, region, grade, dim]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE));
  const currentPage = Math.min(page, totalPages);

  const paginatedList = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return filtered.slice(start, start + ITEMS_PER_PAGE);
  }, [filtered, currentPage]);

  const activeDimMeta = DIM_BY_CODE[dim];

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    const gridEl = document.getElementById("country-index-grid");
    if (gridEl) {
      gridEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const startCount = filtered.length > 0 ? (currentPage - 1) * ITEMS_PER_PAGE + 1 : 0;
  const endCount = Math.min(currentPage * ITEMS_PER_PAGE, filtered.length);

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 md:py-10">
      {/* ── TOP HEADER SECTION ──────────────────────────────────────────── */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div>
          <p
            className="uppercase text-[#E14B3C] font-bold"
            style={{ fontSize: "11px", letterSpacing: "0.22em" }}
          >
            Global Cultural Directory
          </p>
          <h1 className="mt-2 font-display text-6xl md:text-8xl font-black uppercase tracking-tight text-neutral-900 dark:text-white leading-none">
            Country Index
          </h1>
        </div>

        {/* Top Right Ranking Meta */}
        <div className="flex items-center gap-3 text-xs font-bold uppercase tracking-wider text-neutral-500 dark:text-white/50">
          <span>{filtered.length} Countries</span>
          <span>—</span>
          <span>Ranked by {activeDimMeta.label}</span>
        </div>
      </div>

      {/* ── FILTERS & DIMENSION SWITCHER BAR ────────────────────────────── */}
      <div className="mt-10 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-neutral-200 bg-white p-4 shadow-xl dark:border-white/10 dark:bg-[#0E0E10]">
        {/* Dimension Switcher Pills */}
        <div className="flex flex-wrap items-center gap-1.5">
          {DIMENSIONS.map((d) => (
            <button
              key={d.code}
              onClick={() => setDim(d.code)}
              className={`rounded-lg px-3.5 py-2 text-xs font-bold uppercase tracking-wider transition-all ${
                dim === d.code
                  ? "bg-[#E14B3C] text-white shadow-md"
                  : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200 hover:text-neutral-900 dark:bg-white/5 dark:text-white/60 dark:hover:bg-white/10 dark:hover:text-white"
              }`}
            >
              {d.code}&ensp;{d.label}
            </button>
          ))}
        </div>

        {/* Search & Region Selectors */}
        <div className="flex flex-wrap items-center gap-3 flex-1 min-w-[280px] justify-end">
          <div className="flex items-center gap-2 rounded-xl border border-neutral-200 bg-neutral-50 px-3.5 py-2 text-xs text-neutral-900 flex-1 max-w-xs focus-within:border-[#E14B3C] dark:border-white/10 dark:bg-white/5 dark:text-white">
            <Search className="h-3.5 w-3.5 text-neutral-400 dark:text-white/40" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search country or ISO3..."
              className="w-full bg-transparent outline-none placeholder:text-neutral-400 dark:placeholder:text-white/40"
            />
          </div>

          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="rounded-xl border border-neutral-200 bg-neutral-50 px-3.5 py-2 text-xs font-semibold text-neutral-900 outline-none focus:border-[#E14B3C] dark:border-white/10 dark:bg-white/5 dark:text-white"
          >
            <option value="all" className="bg-white text-neutral-900 dark:bg-[#0E0E10] dark:text-white">All Regions</option>
            {regions.map((r) => (
              <option key={r} value={r} className="bg-white text-neutral-900 dark:bg-[#0E0E10] dark:text-white">
                {r}
              </option>
            ))}
          </select>

          <select
            value={grade}
            onChange={(e) => setGrade(e.target.value)}
            className="rounded-xl border border-neutral-200 bg-neutral-50 px-3.5 py-2 text-xs font-semibold text-neutral-900 outline-none focus:border-[#E14B3C] dark:border-white/10 dark:bg-white/5 dark:text-white"
          >
            <option value="all" className="bg-white text-neutral-900 dark:bg-[#0E0E10] dark:text-white">Any Grade</option>
            {["A", "B", "C", "D"].map((g) => (
              <option key={g} value={g} className="bg-white text-neutral-900 dark:bg-[#0E0E10] dark:text-white">
                Grade {g}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ── COUNTRY INDEX CARDS GRID ────────────────────────────────────── */}
      {isLoading ? (
        <div className="mt-16 flex justify-center">
          <Spinner label="Loading Country Index..." />
        </div>
      ) : filtered.length === 0 ? (
        <div className="mt-16">
          <EmptyState title="No matches found" message="Try adjusting your search criteria or filters." />
        </div>
      ) : (
        <>
          <div
            id="country-index-grid"
            className="mt-8 grid grid-cols-1 border border-neutral-200 bg-white overflow-hidden rounded-2xl dark:border-white/10 dark:bg-[#06080C] md:grid-cols-2 lg:grid-cols-3 scroll-mt-24"
          >
            {paginatedList.map((c, i) => {
              const globalIndex = (currentPage - 1) * ITEMS_PER_PAGE + i;
              return (
                <CountryCard key={c.iso3} c={c} index={globalIndex} activeDim={dim} />
              );
            })}
          </div>

          {/* ── PAGINATION CONTROLS ───────────────────────────────────────── */}
          {totalPages > 1 && (
            <div className="mt-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between rounded-2xl border border-neutral-200 bg-white p-4 shadow-md dark:border-white/10 dark:bg-[#0E0E10]">
              {/* Item Range Info */}
              <div className="text-xs font-semibold text-neutral-500 dark:text-white/60">
                Showing <strong className="text-neutral-900 dark:text-white">{startCount}–{endCount}</strong> of{" "}
                <strong className="text-neutral-900 dark:text-white">{filtered.length}</strong> countries
              </div>

              {/* Navigation Controls */}
              <div className="flex items-center gap-1.5 self-center sm:self-auto">
                {/* Previous Button */}
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="flex h-9 items-center gap-1 rounded-lg border border-neutral-200 bg-neutral-50 px-3 text-xs font-bold uppercase text-neutral-700 transition hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/10 dark:bg-white/5 dark:text-white/80 dark:hover:bg-white/10"
                >
                  <ChevronLeft className="h-4 w-4" />
                  <span>Prev</span>
                </button>

                {/* Page Number Buttons */}
                <div className="flex items-center gap-1">
                  {getPageNumbers(currentPage, totalPages).map((p, idx) =>
                    typeof p === "number" ? (
                      <button
                        key={p}
                        onClick={() => handlePageChange(p)}
                        className={`flex h-9 w-9 items-center justify-center rounded-lg text-xs font-bold transition-all ${
                          p === currentPage
                            ? "bg-[#E14B3C] text-white shadow-sm"
                            : "bg-neutral-50 text-neutral-700 hover:bg-neutral-100 dark:bg-white/5 dark:text-white/70 dark:hover:bg-white/10"
                        }`}
                      >
                        {p}
                      </button>
                    ) : (
                      <span
                        key={`dots-${idx}`}
                        className="px-1.5 text-xs text-neutral-400 dark:text-white/40 select-none"
                      >
                        …
                      </span>
                    )
                  )}
                </div>

                {/* Next Button */}
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="flex h-9 items-center gap-1 rounded-lg border border-neutral-200 bg-neutral-50 px-3 text-xs font-bold uppercase text-neutral-700 transition hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/10 dark:bg-white/5 dark:text-white/80 dark:hover:bg-white/10"
                >
                  <span>Next</span>
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function CountriesPage() {
  return (
    <>
      <NavBar />
      <main className="min-h-screen bg-background text-foreground dark:bg-[#0A0E14] dark:text-white">
        <Suspense fallback={<div className="flex justify-center py-20"><Spinner label="Loading catalog..." /></div>}>
          <CountriesContent />
        </Suspense>
      </main>
      <SiteFooter />
    </>
  );
}



