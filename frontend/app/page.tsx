"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, Database, Globe2, Layers, Users } from "lucide-react";
import { useStats, useMap } from "@/lib/api";
import { Card, Stat, Spinner } from "@/components/ui";
import { WorldMap } from "@/components/WorldMap";
import { DimensionSwitcher, MapLegend } from "@/components/MapControls";
import type { DimCode } from "@/lib/dimensions";

export default function HomePage() {
  const { data: stats } = useStats();
  const { data: mapData, isLoading } = useMap();
  const [dim, setDim] = useState<DimCode>("D1");

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6">
      {/* Hero */}
      <section className="pt-16 pb-10 text-center">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-accent">
          Cultural Intelligence Platform
        </p>
        <h1 className="mt-4 text-4xl sm:text-6xl font-bold tracking-tight text-balance">
          Understand how cultures
          <br className="hidden sm:block" /> differ across the world.
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-ink-soft text-balance">
          FOLK scores every country on four cultural dimensions, then explains
          the &ldquo;why&rdquo; with evidence, specialist debate, and a full
          research trail. Not just scores &mdash; cultural intelligence.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link
            href="/explore"
            className="inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-2.5 font-medium text-bg hover:opacity-90"
          >
            Explore the map <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/world-rankings"
            className="inline-flex items-center gap-2 rounded-lg border border-line px-5 py-2.5 font-medium text-ink hover:bg-bg-hover"
          >
            World rankings
          </Link>
        </div>
      </section>

      {/* KPI cards */}
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card className="p-5">
          <div className="flex items-center gap-2 text-ink-dim mb-2">
            <Globe2 className="h-4 w-4" />
            <span className="text-xs uppercase tracking-wide">Countries</span>
          </div>
          <div className="text-3xl font-semibold">{stats?.countries ?? "—"}</div>
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-2 text-ink-dim mb-2">
            <Database className="h-4 w-4" />
            <span className="text-xs uppercase tracking-wide">Evidence sources</span>
          </div>
          <div className="text-3xl font-semibold">
            {stats?.evidence_sources ?? "—"}
          </div>
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-2 text-ink-dim mb-2">
            <Layers className="h-4 w-4" />
            <span className="text-xs uppercase tracking-wide">Frameworks</span>
          </div>
          <div className="text-3xl font-semibold">{stats?.frameworks ?? 5}</div>
          <div className="text-xs text-ink-soft mt-1">
            Hofstede &middot; GLOBE &middot; Schwartz &middot; Trompenaars &middot; WVS
          </div>
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-2 text-ink-dim mb-2">
            <Users className="h-4 w-4" />
            <span className="text-xs uppercase tracking-wide">Research council</span>
          </div>
          <div className="text-xl font-semibold mt-1">GPT · Claude · DeepSeek</div>
          <div className="text-xs text-ink-soft mt-1">
            Grade {stats?.research_grade ?? "—"} &middot; {stats?.archetype_count ?? 0} archetypes
          </div>
        </Card>
      </section>

      {/* Global map */}
      <section className="mt-12">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">The Global Map</h2>
            <p className="text-sm text-ink-soft mt-1">
              Recolor the world by any cultural dimension. Click a country to dive in.
            </p>
          </div>
          <DimensionSwitcher value={dim} onChange={setDim} />
        </div>
        {isLoading ? (
          <Spinner label="Loading map data..." />
        ) : (
          <>
            <WorldMap data={mapData ?? []} dim={dim} height={500} />
            <div className="mt-3 flex justify-center">
              <MapLegend dim={dim} />
            </div>
          </>
        )}
      </section>

      {/* 4-layer pitch */}
      <section className="mt-16 grid gap-4 sm:grid-cols-4">
        {[
          { n: "01", t: "What is this country like?", d: "Scores across Identity, Expression, Structure, and Drive." },
          { n: "02", t: "Why is it like that?", d: "Plain-language explanations grounded in evidence." },
          { n: "03", t: "What evidence supports this?", d: "Supporting and counter evidence with verified sources." },
          { n: "04", t: "How was this generated?", d: "Specialist debate, calibration, and full research traces." },
        ].map((x) => (
          <Card key={x.n} className="p-5">
            <div className="text-accent font-mono text-sm">{x.n}</div>
            <div className="mt-2 font-medium">{x.t}</div>
            <div className="mt-1 text-sm text-ink-soft">{x.d}</div>
          </Card>
        ))}
      </section>
    </div>
  );
}
