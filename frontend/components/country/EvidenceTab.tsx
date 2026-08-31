"use client";

import { ExternalLink } from "lucide-react";
import { Spinner, EmptyState } from "@/components/ui";
import { useSources, type SourceEntry } from "@/lib/api";

function Hairline() {
  return <div className="h-px w-full bg-ink/10 dark:bg-white/8" />;
}

function EditorialHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-display text-[1.6rem] uppercase leading-[0.9] tracking-[-0.01em] text-ink dark:text-white">
      {children}
    </h2>
  );
}

function ScoreBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="relative h-px w-full bg-ink/12 dark:bg-white/10">
      <div
        className="absolute left-0 top-0 h-full bg-coral-strong dark:bg-[#E14B3C]"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function SourceReliability({ iso3 }: { iso3: string }) {
  const { data } = useSources(iso3);
  if (!data) return null;
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <EditorialHeading>Source reliability</EditorialHeading>
        <span className="text-[11px] text-ink/40 dark:text-white/30">
          What the evidence is built on
        </span>
      </div>
      <Hairline />
      <div className="mt-6 grid grid-cols-1 gap-x-16 sm:grid-cols-2">
        {/* Source types */}
        <div className="divide-y divide-ink/8 dark:divide-white/8">
          {data.by_type.map((t) => (
            <div key={t.type} className="flex items-center justify-between py-3">
              <span className="text-[13px] text-ink/65 dark:text-white/55">{t.type}</span>
              <span className="text-[13px] tabular-nums font-semibold text-ink dark:text-white">
                {t.count}
              </span>
            </div>
          ))}
          {data.by_type.length === 0 && (
            <p className="py-3 text-[13px] text-ink/40 dark:text-white/30">
              No catalogued sources.
            </p>
          )}
        </div>

        {/* Quality metrics */}
        <div className="space-y-5 pt-4 sm:pt-0">
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-ink/35 dark:text-white/30">
                Avg. source quality
              </span>
              <span className="text-[13px] tabular-nums font-semibold text-ink dark:text-white">
                {data.average_quality != null ? data.average_quality : "—"}
              </span>
            </div>
            <ScoreBar value={data.average_quality ?? 0} />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-ink/35 dark:text-white/30">
              Verified sources
            </span>
            <span className="text-[13px] tabular-nums font-semibold text-ink dark:text-white">
              {data.verified}/{data.total_sources}{" "}
              <span className="text-ink/40 dark:text-white/35 font-normal">
                ({data.verified_pct}%)
              </span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SourceCard({ s }: { s: SourceEntry }) {
  const isLink = s.url?.startsWith("http");
  return (
    <a
      href={isLink ? s.url! : undefined}
      target="_blank"
      rel="noreferrer"
      className="block border-b border-ink/8 dark:border-white/8 py-4 hover:opacity-70 transition"
    >
      <div className="flex items-start justify-between gap-3">
        <span className="text-[13px] font-medium leading-snug text-ink dark:text-white">
          {s.title}
        </span>
        {isLink && (
          <ExternalLink className="h-3 w-3 shrink-0 text-ink/30 dark:text-white/25 mt-0.5" />
        )}
      </div>
      <div className="mt-1 text-[11px] text-ink/40 dark:text-white/30">
        {s.author}
        {s.publication_year ? ` · ${s.publication_year}` : ""}
      </div>
      {s.excerpt && (
        <p className="mt-2 text-[12px] leading-relaxed text-ink/55 dark:text-white/45 line-clamp-3">
          {s.excerpt}
        </p>
      )}
    </a>
  );
}

function SourcesGrid({ iso3 }: { iso3: string }) {
  const { data, isLoading } = useSources(iso3);
  if (isLoading) return <Spinner label="Loading sources..." />;
  const sources = data?.sources ?? [];
  if (sources.length === 0) {
    return (
      <EmptyState
        title="No linked sources yet"
        message="The grounded observations did not resolve to catalogued sources."
      />
    );
  }
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <EditorialHeading>Evidence sources</EditorialHeading>
        <span className="text-[11px] text-ink/40 dark:text-white/30">
          {sources.length} sources
        </span>
      </div>
      <Hairline />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
        {sources.map((s, i) => (
          <SourceCard key={`${s.source_id}-${i}`} s={s} />
        ))}
      </div>
    </div>
  );
}

export function EvidenceTab({ iso3 }: { iso3: string }) {
  return (
    <div className="space-y-14">
      <SourceReliability iso3={iso3} />
      <SourcesGrid iso3={iso3} />
    </div>
  );
}
