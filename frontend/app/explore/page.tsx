"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { useCountries, useMap } from "@/lib/api";
import { WorldMap } from "@/components/WorldMap";
import { DimensionSwitcher, MapLegend } from "@/components/MapControls";
import { CountryCard } from "@/components/CountryCard";
import { Card, Spinner, EmptyState } from "@/components/ui";
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
    return [...list].sort((a, b) => a.country.localeCompare(b.country));
  }, [countries, q, region, confidence, grade, reviewedOnly, dim]);

  const selectClass =
    "rounded-lg border border-line bg-bg-soft px-3 py-2 text-sm text-ink outline-none focus:border-accent";

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-8">
      <h1 className="text-3xl font-bold tracking-tight">Explore</h1>
      <p className="text-ink-soft mt-1">
        Recolor the world by dimension, then browse and filter every country.
      </p>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <DimensionSwitcher value={dim} onChange={setDim} />
        <MapLegend dim={dim} />
      </div>

      <div className="mt-4">
        <WorldMap data={mapData ?? []} dim={dim} height={460} />
      </div>

      {/* Filters */}
      <div className="mt-10 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 rounded-lg border border-line bg-bg-soft px-3 py-2 flex-1 min-w-[200px]">
          <Search className="h-4 w-4 text-ink-dim" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search countries..."
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-ink-dim"
          />
        </div>
        <select value={region} onChange={(e) => setRegion(e.target.value)} className={selectClass}>
          <option value="all">All regions</option>
          {regions.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <select value={confidence} onChange={(e) => setConfidence(e.target.value)} className={selectClass}>
          <option value="all">Any confidence ({dim})</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>
        <select value={grade} onChange={(e) => setGrade(e.target.value)} className={selectClass}>
          <option value="all">Any grade</option>
          {["A", "B", "C", "D"].map((g) => (
            <option key={g} value={g}>Grade {g}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-ink-soft cursor-pointer">
          <input
            type="checkbox"
            checked={reviewedOnly}
            onChange={(e) => setReviewedOnly(e.target.checked)}
            className="accent-accent"
          />
          Human-reviewed
        </label>
      </div>

      <div className="mt-2 text-sm text-ink-dim">{filtered.length} countries</div>

      {isLoading ? (
        <Spinner label="Loading countries..." />
      ) : filtered.length === 0 ? (
        <div className="mt-4">
          <EmptyState title="No matches" message="Try clearing some filters." />
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.map((c) => (
            <CountryCard key={c.iso3} c={c} />
          ))}
        </div>
      )}
    </div>
  );
}
