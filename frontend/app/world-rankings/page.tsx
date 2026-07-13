"use client";

import Link from "next/link";
import { useState } from "react";
import { useRankings, useRegionRankings, type RankingRow } from "@/lib/api";
import { Card, SectionTitle, Spinner } from "@/components/ui";
import { DimensionSwitcher } from "@/components/MapControls";
import { DIM_BY_CODE, colorForScore, type DimCode } from "@/lib/dimensions";
import { flagEmoji } from "@/lib/utils";

function RankList({ rows, title, dim }: { rows: RankingRow[]; title: string; dim: DimCode }) {
  return (
    <Card className="p-6">
      <SectionTitle title={title} />
      <ol className="space-y-1">
        {rows.map((r, i) => (
          <li key={r.iso3}>
            <Link
              href={`/country/${r.iso3}`}
              className="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-bg-hover"
            >
              <span className="w-5 text-right text-sm text-ink-dim tabular-nums">
                {i + 1}
              </span>
              <span>{flagEmoji(r.iso3)}</span>
              <span className="flex-1 truncate text-sm">{r.country}</span>
              <span className="text-xs text-ink-dim">{r.region}</span>
              <span
                className="w-10 text-right text-sm font-semibold tabular-nums"
                style={{ color: colorForScore(dim, r.score) }}
              >
                {r.score}
              </span>
            </Link>
          </li>
        ))}
        {rows.length === 0 && <p className="text-sm text-ink-dim">No data yet.</p>}
      </ol>
    </Card>
  );
}

export default function WorldRankingsPage() {
  const [dim, setDim] = useState<DimCode>("D4");
  const { data: rankings, isLoading } = useRankings(dim);
  const { data: regions } = useRegionRankings(dim);
  const meta = DIM_BY_CODE[dim];

  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-6 py-8">
      <h1 className="text-3xl font-bold tracking-tight">World Rankings</h1>
      <p className="text-ink-soft mt-1">
        Global leaderboards for each cultural dimension.
      </p>

      <div className="mt-6">
        <DimensionSwitcher value={dim} onChange={setDim} />
        <p className="mt-3 text-sm text-ink-soft">
          <span className="font-medium" style={{ color: meta.color }}>
            {meta.label}
          </span>
          : {meta.low} (low) &harr; {meta.high} (high)
        </p>
      </div>

      {isLoading ? (
        <Spinner label="Loading rankings..." />
      ) : (
        <>
          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <RankList rows={rankings?.highest ?? []} title={`Highest ${meta.label} (${meta.high})`} dim={dim} />
            <RankList rows={rankings?.lowest ?? []} title={`Lowest ${meta.label} (${meta.low})`} dim={dim} />
          </div>

          {regions && regions.regions.length > 0 && (
            <Card className="mt-6 p-6">
              <SectionTitle title={`Regions by ${meta.label}`} subtitle="Average score per region" />
              <div className="space-y-2">
                {regions.regions.map((r, i) => (
                  <div key={r.region} className="flex items-center gap-3">
                    <span className="w-5 text-right text-sm text-ink-dim tabular-nums">
                      {i + 1}
                    </span>
                    <span className="flex-1 text-sm">{r.region}</span>
                    <div className="h-2 w-40 rounded-full bg-bg-hover overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${r.average}%`,
                          backgroundColor: meta.color,
                        }}
                      />
                    </div>
                    <span className="w-10 text-right text-sm font-semibold tabular-nums">
                      {r.average}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
