"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { useCountries, useMap } from "@/lib/api";
import { NavBar } from "@/components/NavBar";
import { SiteFooter } from "@/components/SiteFooter";
import { CartographicFlatMap } from "@/components/CartographicFlatMap";
import { CountryCard } from "@/components/CountryCard";
import { Spinner, EmptyState } from "@/components/ui";
import type { DimCode } from "@/lib/dimensions";

export default function ExplorePage() {
  const { data: mapData } = useMap();
  const { data: countries, isLoading } = useCountries();
  const [dim, setDim] = useState<DimCode>("D1");
  const [q, setQ] = useState("");
  const [region, setRegion] = useState("all");
  const [confidence, setConfidence] = useState("all");
  const [grade, setGrade] = useState("all");
  const [reviewedOnly, setReviewedOnly] = useState(false);

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
    if (confidence !== "all")
      list = list.filter((c) => c.confidence[dim] === confidence);
    if (grade !== "all") list = list.filter((c) => c.research_grade === grade);
    if (reviewedOnly) list = list.filter((c) => c.requires_human_review);
    return [...list].sort((a, b) => (b.scores[dim] ?? 0) - (a.scores[dim] ?? 0));
  }, [countries, q, region, confidence, grade, reviewedOnly, dim]);

  return (
    <>
      <NavBar />
      <main className="min-h-screen bg-background text-foreground dark:bg-[#06080C] dark:text-white px-4 sm:px-6 py-8 md:px-12 md:py-12">
        <div className="mx-auto max-w-7xl">
          {/* Cartographic Flatmap */}
          <CartographicFlatMap
            data={mapData ?? []}
            dim={dim}
            onDimChange={setDim}
          />

          {/* Filters Bar */}
          <div className="mt-12 flex flex-wrap items-center gap-3 rounded-2xl border border-neutral-200 bg-white p-4 shadow-lg dark:border-white/10 dark:bg-[#0E0E10]">
            <div className="flex items-center gap-2 rounded-xl border border-neutral-200 bg-neutral-50 px-3.5 py-2 text-xs text-neutral-900 flex-1 min-w-[200px] dark:border-white/10 dark:bg-white/5 dark:text-white">
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
              className="rounded-xl border border-neutral-200 bg-neutral-50 px-3.5 py-2 text-xs font-semibold text-neutral-900 outline-none dark:border-white/10 dark:bg-white/5 dark:text-white"
            >
              <option value="all" className="bg-white text-neutral-900 dark:bg-[#0E0E10] dark:text-white">All regions</option>
              {regions.map((r) => (
                <option key={r} value={r} className="bg-white text-neutral-900 dark:bg-[#0E0E10] dark:text-white">{r}</option>
              ))}
            </select>

            <select
              value={confidence}
              onChange={(e) => setConfidence(e.target.value)}
              className="rounded-xl border border-neutral-200 bg-neutral-50 px-3.5 py-2 text-xs font-semibold text-neutral-900 outline-none dark:border-white/10 dark:bg-white/5 dark:text-white"
            >
              <option value="all" className="bg-white text-neutral-900 dark:bg-[#0E0E10] dark:text-white">Any confidence ({dim})</option>
              <option value="HIGH" className="bg-white text-neutral-900 dark:bg-[#0E0E10] dark:text-white">High</option>
              <option value="MEDIUM" className="bg-white text-neutral-900 dark:bg-[#0E0E10] dark:text-white">Medium</option>
              <option value="LOW" className="bg-white text-neutral-900 dark:bg-[#0E0E10] dark:text-white">Low</option>
            </select>

            <select
              value={grade}
              onChange={(e) => setGrade(e.target.value)}
              className="rounded-xl border border-neutral-200 bg-neutral-50 px-3.5 py-2 text-xs font-semibold text-neutral-900 outline-none dark:border-white/10 dark:bg-white/5 dark:text-white"
            >
              <option value="all" className="bg-white text-neutral-900 dark:bg-[#0E0E10] dark:text-white">Any grade</option>
              {["A", "B", "C", "D"].map((g) => (
                <option key={g} value={g} className="bg-white text-neutral-900 dark:bg-[#0E0E10] dark:text-white">Grade {g}</option>
              ))}
            </select>
          </div>

          <div className="mt-4 text-xs font-bold uppercase tracking-wider text-neutral-500 dark:text-white/50">
            {filtered.length} Countries
          </div>

          {isLoading ? (
            <div className="mt-12 flex justify-center">
              <Spinner label="Loading countries..." />
            </div>
          ) : filtered.length === 0 ? (
            <div className="mt-8">
              <EmptyState title="No matches" message="Try clearing some filters." />
            </div>
          ) : (
            <div className="mt-6 grid grid-cols-1 border border-neutral-200 bg-white overflow-hidden rounded-2xl dark:border-white/10 dark:bg-[#06080C] md:grid-cols-2 lg:grid-cols-3">
              {filtered.map((c, i) => (
                <CountryCard key={c.iso3} c={c} index={i} activeDim={dim} />
              ))}
            </div>
          )}
        </div>
      </main>
      <SiteFooter />
    </>
  );
}

