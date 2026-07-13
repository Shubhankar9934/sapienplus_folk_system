"use client";

import { useMemo, useState } from "react";
import { X, Plus } from "lucide-react";
import { useCountries, useCompare } from "@/lib/api";
import { Card, SectionTitle, EmptyState } from "@/components/ui";
import { FolkRadar, type RadarSeries } from "@/components/FolkRadar";
import { DIMENSIONS, type DimCode } from "@/lib/dimensions";
import { flagEmoji } from "@/lib/utils";

const PALETTE = ["#5b8def", "#34d399", "#e879a6", "#f0b429"];
const MAX = 4;

export default function ComparePage() {
  const { data: countries } = useCountries();
  const [selected, setSelected] = useState<string[]>([]);
  const [picker, setPicker] = useState("");

  const { data: compare } = useCompare(selected);

  const available = useMemo(() => {
    const list = (countries ?? []).filter((c) => !selected.includes(c.iso3));
    if (!picker.trim()) return list.slice(0, 0);
    const t = picker.toLowerCase();
    return list
      .filter((c) => c.country.toLowerCase().includes(t) || c.iso3.toLowerCase().includes(t))
      .slice(0, 6);
  }, [countries, selected, picker]);

  function add(iso: string) {
    if (selected.length >= MAX) return;
    setSelected((s) => [...s, iso]);
    setPicker("");
  }

  const series: RadarSeries[] =
    compare?.countries.map((c, i) => ({
      name: c.country,
      color: PALETTE[i % PALETTE.length],
      scores: c.scores,
    })) ?? [];

  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-6 py-8">
      <h1 className="text-3xl font-bold tracking-tight">Compare</h1>
      <p className="text-ink-soft mt-1">
        Overlay cultural fingerprints for up to {MAX} countries.
      </p>

      {/* Selected chips + picker */}
      <div className="mt-6 flex flex-wrap items-center gap-2">
        {compare?.countries.map((c, i) => (
          <span
            key={c.iso3}
            className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm"
            style={{ borderColor: `${PALETTE[i % PALETTE.length]}66` }}
          >
            <span>{flagEmoji(c.iso3)}</span>
            {c.country}
            <button onClick={() => setSelected((s) => s.filter((x) => x !== c.iso3))}>
              <X className="h-3.5 w-3.5 text-ink-dim hover:text-ink" />
            </button>
          </span>
        ))}
        {selected.length < MAX && (
          <div className="relative">
            <div className="inline-flex items-center gap-2 rounded-full border border-line px-3 py-1.5 text-sm">
              <Plus className="h-3.5 w-3.5 text-ink-dim" />
              <input
                value={picker}
                onChange={(e) => setPicker(e.target.value)}
                placeholder="Add country..."
                className="bg-transparent outline-none placeholder:text-ink-dim w-32"
              />
            </div>
            {available.length > 0 && (
              <div className="absolute z-10 mt-1 w-56 rounded-lg border border-line bg-bg-card p-1 shadow-xl">
                {available.map((c) => (
                  <button
                    key={c.iso3}
                    onClick={() => add(c.iso3)}
                    className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-bg-hover"
                  >
                    <span>{flagEmoji(c.iso3)}</span>
                    {c.country}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {selected.length === 0 ? (
        <div className="mt-8">
          <EmptyState
            title="Pick countries to compare"
            message="Add two or more countries to overlay their radars and scores."
          />
        </div>
      ) : (
        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card className="p-6">
            <SectionTitle title="Radar overlay" />
            <FolkRadar series={series} height={380} showLegend />
          </Card>
          <Card className="p-6 overflow-x-auto">
            <SectionTitle title="Score table" />
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-ink-dim border-b border-line">
                  <th className="py-2 pr-4 font-medium">Country</th>
                  {DIMENSIONS.map((d) => (
                    <th key={d.code} className="py-2 px-3 font-medium text-center">
                      {d.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {compare?.countries.map((c) => (
                  <tr key={c.iso3} className="border-b border-line/50">
                    <td className="py-2.5 pr-4">
                      <span className="mr-1.5">{flagEmoji(c.iso3)}</span>
                      {c.country}
                    </td>
                    {DIMENSIONS.map((d) => (
                      <td key={d.code} className="py-2.5 px-3 text-center tabular-nums">
                        {c.scores[d.code as DimCode] ?? "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {compare && compare.countries.some((c) => c.archetype) && (
              <div className="mt-4 space-y-1">
                {compare.countries.map((c) => (
                  <div key={c.iso3} className="text-xs text-ink-dim">
                    {c.country}: {c.archetype ?? "—"}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
