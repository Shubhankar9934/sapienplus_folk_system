"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { DIMENSIONS, type DimCode } from "@/lib/dimensions";
import type { CountryListItem } from "@/lib/api";

export function CountryCard({
  c,
  index = 0,
  activeDim = "D1",
}: {
  c: CountryListItem;
  index?: number;
  activeDim?: DimCode;
}) {
  const formattedIndex = String(index + 1).padStart(2, "0");
  const regionName = (c.region ?? "Region").toUpperCase();
  const grade = c.research_grade ?? "A";

  return (
    <Link href={`/country/${c.iso3}`} className="group block h-full">
      <div className="relative flex h-full flex-col justify-between overflow-hidden bg-white dark:bg-[#0A0E14] p-6 transition-colors duration-200 hover:bg-neutral-50 dark:hover:bg-white/[0.03] border-b border-r border-neutral-200 dark:border-white/10">
        {/* Top Accent / Watermark */}
        <div>
          {/* Top Row: Index/Region + Grade Watermark */}
          <div className="flex items-start justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#E14B3C]">
              {formattedIndex} / {regionName}
            </span>
            <span className="font-display text-5xl font-black text-neutral-200 dark:text-white/15 transition-colors group-hover:text-neutral-300 dark:group-hover:text-white/30 select-none leading-none">
              {grade}
            </span>
          </div>

          {/* Main Title: Country Name */}
          <h3 className="mt-2 font-display text-3xl md:text-4xl font-black uppercase tracking-tight text-neutral-900 dark:text-white transition-colors group-hover:text-[#E14B3C] leading-none">
            {c.country}
          </h3>

          {/* Subtitle: Archetype */}
          <p className="mt-2 text-xs font-medium text-neutral-500 dark:text-white/50">
            {c.archetype ?? "Cultural Cluster"}
          </p>
        </div>

        {/* Bottom Section: Divider + 2x2 Scores + CTA */}
        <div>
          {/* Divider */}
          <div className="my-4 h-px w-full bg-neutral-200 dark:bg-white/10" />

          {/* 2x2 Dimension Scores Grid */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-3">
            {DIMENSIONS.map((d) => {
              const s = c.scores[d.code];
              const isActive = d.code === activeDim;

              return (
                <div key={d.code} className="space-y-1">
                  <div className="flex items-center justify-between text-[10px]">
                    <span
                      className={`font-bold uppercase tracking-wider ${
                        isActive ? "text-[#E14B3C]" : "text-neutral-400 dark:text-white/40"
                      }`}
                    >
                      {d.code} SCORE
                    </span>
                    <span className="font-display text-base md:text-lg font-bold text-neutral-900 dark:text-white tabular-nums">
                      {s !== null && s !== undefined ? Math.round(s) : "—"}
                    </span>
                  </div>

                  {/* Horizontal Bar */}
                  <div className="h-[2px] w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-white/10">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        isActive ? "bg-[#E14B3C]" : "bg-neutral-300 dark:bg-white/20"
                      }`}
                      style={{
                        width: s !== null && s !== undefined ? `${Math.max(0, Math.min(100, s))}%` : "0%",
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* CTA Row */}
          <div className="mt-5 flex items-center justify-between pt-2">
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-neutral-500 dark:text-white/60 transition-colors group-hover:text-neutral-900 dark:group-hover:text-white">
              View Analysis
            </span>
            <ArrowRight className="h-3.5 w-3.5 text-neutral-400 dark:text-white/40 transition-all group-hover:translate-x-1 group-hover:text-neutral-900 dark:group-hover:text-white" />
          </div>
        </div>
      </div>
    </Link>
  );
}

