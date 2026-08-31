"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { WorldMap } from "./WorldMap";
import type { MapItem } from "@/lib/api";
import { DIMENSIONS, DIM_BY_CODE, type DimCode } from "@/lib/dimensions";

export function CartographicFlatMap({
  data,
  dim,
  onDimChange,
  onSelect,
}: {
  data: MapItem[];
  dim: DimCode;
  onDimChange: (dim: DimCode) => void;
  onSelect?: (iso3: string) => void;
}) {
  const activeDimMeta = DIM_BY_CODE[dim];

  return (
    <div className="w-full">
      {/* ── TOP HEADER SECTION ──────────────────────────────────────────── */}
      <div className="mb-10 flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.22em] text-[#E14B3C]">
            <span className="h-px w-4 bg-[#E14B3C]" />
            <span>Explore The Index</span>
          </div>
          <h2 className="mt-3 font-display text-5xl md:text-8xl font-black uppercase tracking-tight text-neutral-900 dark:text-white leading-[0.88]">
            The World,
          </h2>
          <h2 className="font-display text-5xl md:text-8xl font-black uppercase tracking-tight leading-[0.88]">
            <span
              className="text-transparent"
              style={{
                WebkitTextStroke: "2px currentColor",
                color: "transparent",
              }}
            >
              <span className="text-neutral-900 dark:text-white">
                Recoloured
              </span>
            </span>
          </h2>
        </div>

        {/* Top Right Cartographic Badge / Card */}
        <div className="relative rounded-2xl border border-neutral-200 bg-neutral-50/60 p-6 dark:border-white/10 dark:bg-white/[0.03] min-w-[280px] max-w-xs overflow-hidden shadow-sm">
          <span className="absolute -right-2 -top-4 font-display text-8xl font-black text-neutral-200 dark:text-white/10 select-none leading-none">
            04
          </span>
          <div className="relative z-10">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-neutral-400 dark:text-white/40">
              Cartographic Plate / 01
            </p>
            <p className="mt-2 text-xs leading-relaxed text-neutral-600 dark:text-white/60">
              Read cultural orientation as geography. Shift dimensions to see the world redraw itself.
            </p>
          </div>
        </div>
      </div>

      {/* ── MAIN CARTOGRAPHIC FRAME CONTAINER ───────────────────────────── */}
      <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-2xl dark:border-white/10 dark:bg-[#06080C] relative">
        {/* ── DIMENSION TAB BAR (ABOVE MAP FRAME) ────────────────────── */}
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between border-b border-neutral-100 pb-4 dark:border-white/10">
          <div className="flex flex-wrap items-center gap-4 md:gap-8">
            {DIMENSIONS.map((d) => {
              const isActive = dim === d.code;
              const polesText = `${d.low.toUpperCase()}–${d.high.toUpperCase()}`;
              return (
                <button
                  key={d.code}
                  onClick={() => onDimChange(d.code)}
                  className="group relative text-left py-1"
                >
                  <div className="flex items-baseline gap-2">
                    <span
                      className={`font-display text-xl font-black uppercase tracking-tight transition-colors ${
                        isActive
                          ? "text-neutral-900 dark:text-white"
                          : "text-neutral-400 dark:text-white/40 group-hover:text-neutral-700 dark:group-hover:text-white/70"
                      }`}
                    >
                      {d.label}
                    </span>
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider transition-colors ${
                        isActive ? "text-[#E14B3C]" : "text-neutral-400 dark:text-white/40"
                      }`}
                    >
                      {d.code} · {polesText}
                    </span>
                  </div>
                  {isActive && (
                    <span className="absolute bottom-0 left-0 h-0.5 w-full bg-[#E14B3C]" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Gradient Legend (Right) */}
          <div className="flex items-center gap-3 text-[10px] font-bold uppercase tracking-wider text-neutral-400 dark:text-white/40">
            <span>{activeDimMeta.low}</span>
            <div className="h-1.5 w-28 md:w-36 rounded-full bg-gradient-to-r from-slate-400 via-slate-600 to-[#E14B3C] dark:from-slate-700 dark:to-[#E14B3C]" />
            <span>{activeDimMeta.high}</span>
          </div>
        </div>

        {/* ── MAP FRAME VIEWPORT ────────────────────────────────────────── */}
        <div className="relative rounded-2xl border border-neutral-200 bg-slate-50 dark:border-white/10 dark:bg-[#080B10] p-4">
          {/* Frame Top Header */}
          <div className="mb-2 flex items-center justify-between text-[10px] font-bold uppercase tracking-[0.2em] text-neutral-400 dark:text-white/40 px-1">
            <span>— Global Cultural Atlas</span>
            <span>90°N — 90°S</span>
          </div>

          {/* Map Viewport */}
          <div className="overflow-hidden rounded-xl border border-neutral-200 dark:border-white/10">
            <WorldMap
              data={data}
              dim={dim}
              height={560}
              onSelect={onSelect}
            />
          </div>

          {/* Frame Bottom Footer */}
          <div className="mt-2 flex items-center justify-between text-[10px] font-bold uppercase tracking-[0.2em] text-neutral-400 dark:text-white/40 px-1">
            <span>Natural Earth / 1:110M</span>
            <span>Equal Earth —</span>
          </div>
        </div>

        {/* ── BOTTOM META & ACTION ROW ───────────────────────────────── */}
        <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between pt-2">
          <span className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500 dark:text-white/40">
            {data.length > 0 ? data.length : 177} Countries · Coloured by {activeDimMeta.label}
          </span>

          <Link
            href="/countries"
            className="group flex items-center gap-3 self-start sm:self-auto rounded-full border border-neutral-200 bg-white px-5 py-2 text-xs font-bold uppercase tracking-wider text-neutral-900 shadow-sm transition hover:bg-[#E14B3C] hover:border-[#E14B3C] hover:text-white dark:border-white/10 dark:bg-white/5 dark:text-white dark:hover:bg-[#E14B3C] dark:hover:border-[#E14B3C]"
          >
            <span>Browse Every Profile</span>
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-neutral-100 text-neutral-900 transition-colors group-hover:bg-white group-hover:text-[#E14B3C] dark:bg-white/10 dark:text-white">
              <ArrowRight className="h-3.5 w-3.5" strokeWidth={2.5} />
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
