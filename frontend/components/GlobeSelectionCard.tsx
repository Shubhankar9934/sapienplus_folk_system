"use client";

import { useEffect, useRef } from "react";
import { ArrowRight, X } from "lucide-react";
import gsap from "gsap";
import type { SelectionInfo } from "./CountryGlobe";
import { useMap, useCountry, useCountries } from "@/lib/api";
import type { DimCode } from "@/lib/dimensions";
import { DIMENSIONS } from "@/lib/dimensions";

interface GlobeSelectionCardProps {
  selection: SelectionInfo;
  dim: DimCode;
  onClose: () => void;
  onZoomNavigate: (iso3: string) => void;
}

const DIM_STYLES: Record<DimCode, { color: string }> = {
  D1: { color: "#3B82F6" }, // Blue - IDENTITY
  D2: { color: "#EC4899" }, // Pink - EXPRESSION
  D3: { color: "#F59E0B" }, // Gold/Amber - STRUCTURE
  D4: { color: "#10B981" }, // Emerald/Green - DRIVE
};

export function GlobeSelectionCard({
  selection,
  dim,
  onClose,
  onZoomNavigate,
}: GlobeSelectionCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const barsRef = useRef<(HTMLDivElement | null)[]>([]);
  const iso3 = selection.iso3;
  const name = selection.country.properties?.name ?? "";

  const { data: mapData } = useMap();
  const { data: profile } = useCountry(iso3 ?? "");
  const { data: countries } = useCountries();

  const entry = mapData?.find((m) => m.iso3 === iso3) ?? null;
  const countryListItem = countries?.find((c) => c.iso3 === iso3) ?? null;

  const regionName = profile?.region ?? countryListItem?.region ?? "Region";
  const archetype =
    profile?.cultural_archetype?.title ??
    profile?.archetype ??
    countryListItem?.archetype ??
    "RESERVED COLLECTIVISTS II";

  const rawSummary =
    profile?.executive_summary ??
    profile?.cultural_archetype?.summary ??
    (profile?.culture_at_a_glance && profile.culture_at_a_glance.length > 0
      ? profile.culture_at_a_glance[0]
      : null);

  const summaryText =
    rawSummary ??
    `In ${name}, tribe and community shape social and political life, giving a strong sense of belonging and cultural identity.`;

  const scores = DIMENSIONS.map((d) => ({
    ...d,
    score: entry?.scores[d.code] ?? null,
    style: DIM_STYLES[d.code],
  }));

  // Slide-in + bar animations on country change
  useEffect(() => {
    if (!cardRef.current) return;
    gsap.fromTo(
      cardRef.current,
      { x: 36, opacity: 0, scale: 0.96 },
      { x: 0, opacity: 1, scale: 1, duration: 0.45, ease: "power4.out" },
    );

    barsRef.current.forEach((bar, i) => {
      if (!bar) return;
      const score = scores[i].score;
      gsap.fromTo(
        bar,
        { width: "0%" },
        {
          width: score !== null ? `${Math.max(0, Math.min(100, score))}%` : "0%",
          duration: 0.8,
          delay: 0.15 + i * 0.08,
          ease: "power3.out",
        },
      );
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selection.country]);

  const handleZoom = () => {
    if (!iso3) return;
    if (cardRef.current) {
      gsap.to(cardRef.current, {
        x: 36,
        opacity: 0,
        scale: 0.96,
        duration: 0.25,
        ease: "power2.in",
        onComplete: () => onZoomNavigate(iso3),
      });
    } else {
      onZoomNavigate(iso3);
    }
  };

  return (
    <div
      ref={cardRef}
      className="relative w-[340px] md:w-[360px] select-none rounded-3xl border border-neutral-100 bg-white p-6 shadow-[0_20px_50px_rgba(0,0,0,0.15)] dark:border-white/10 dark:bg-[#12141A] dark:shadow-[0_24px_60px_rgba(0,0,0,0.7)]"
    >
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute right-5 top-5 flex h-7 w-7 items-center justify-center rounded-full bg-neutral-100 text-neutral-400 transition hover:bg-neutral-200 hover:text-neutral-700 dark:bg-white/10 dark:text-white/40 dark:hover:bg-white/20 dark:hover:text-white"
        aria-label="Close card"
      >
        <X className="h-3.5 w-3.5" strokeWidth={2.5} />
      </button>

      {/* ── Top Row: Dot + Region & Archetype ────────────────────────────── */}
      <div className="flex items-center justify-between pr-8">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-[#E14B3C]" />
          <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400">
            {regionName}
          </span>
        </div>
        <span className="text-[10px] font-bold uppercase tracking-wider text-[#E14B3C] dark:text-[#F87171]">
          {archetype}
        </span>
      </div>

      {/* ── Title: Country Name ──────────────────────────────────────────── */}
      <h2 className="mt-3 font-display text-4xl md:text-5xl font-black uppercase tracking-tight text-neutral-900 dark:text-white leading-none">
        {name}
      </h2>

      {/* ── Summary Paragraph ────────────────────────────────────────────── */}
      <p className="mt-3.5 text-xs md:text-sm leading-relaxed text-neutral-600 dark:text-neutral-300 font-normal line-clamp-3">
        {summaryText}
      </p>

      {/* ── Dimension Progress Bars ──────────────────────────────────────── */}
      <div className="mt-6 space-y-4">
        {scores.map((d, i) => (
          <div key={d.code} className="space-y-1">
            {/* Header: Name + Score */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-neutral-900 dark:text-white">
                {d.label}
              </span>
              <span
                className="font-bold text-sm tabular-nums"
                style={{ color: d.style.color }}
              >
                {d.score !== null ? Math.round(d.score) : "—"}
              </span>
            </div>

            {/* Bar Track */}
            <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-white/10">
              <div
                ref={(el) => {
                  barsRef.current[i] = el;
                }}
                className="h-full rounded-full transition-all"
                style={{
                  width: "0%",
                  backgroundColor: d.style.color,
                }}
              />
            </div>

            {/* Poles line */}
            <div className="flex justify-between text-[11px] font-medium text-neutral-400 dark:text-neutral-500">
              <span>{d.low}</span>
              <span>{d.high}</span>
            </div>
          </div>
        ))}
      </div>

      {/* ── Footer CTA ─────────────────────────────────────────────────── */}
      <div className="mt-6 border-t border-neutral-100 pt-4 dark:border-white/10">
        <button
          onClick={handleZoom}
          disabled={!iso3}
          className="group flex w-full items-center justify-between rounded-xl bg-neutral-900 px-5 py-3 text-xs font-bold uppercase tracking-wider text-white transition hover:bg-[#E14B3C] dark:bg-white dark:text-[#0E0E10] dark:hover:bg-[#E14B3C] dark:hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          <span>Explore Country Profile</span>
          <ArrowRight
            className="h-4 w-4 transition-transform group-hover:translate-x-1"
            strokeWidth={2.5}
          />
        </button>
      </div>
    </div>
  );
}

