"use client";

import { ExternalLink } from "lucide-react";
import { Card, SectionTitle, Meter, Spinner, EmptyState } from "@/components/ui";
import { useSources, type SourceEntry } from "@/lib/api";

function SourceReliability({ iso3 }: { iso3: string }) {
  const { data } = useSources(iso3);
  if (!data) return null;
  return (
    <Card className="p-6">
      <SectionTitle title="Source reliability" subtitle="What the evidence is built on" />
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div className="space-y-2">
          {data.by_type.map((t) => (
            <div key={t.type} className="flex items-center justify-between text-sm">
              <span className="text-ink-soft">{t.type}</span>
              <span className="tabular-nums font-medium">{t.count}</span>
            </div>
          ))}
          {data.by_type.length === 0 && (
            <p className="text-sm text-ink-dim">No catalogued sources.</p>
          )}
        </div>
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-ink-soft">Average source quality</span>
              <span className="tabular-nums font-medium">
                {data.average_quality != null ? `${data.average_quality}/100` : "—"}
              </span>
            </div>
            <Meter value={data.average_quality ?? 0} color="#34d399" />
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-ink-soft">Verified sources</span>
            <span className="tabular-nums font-medium">
              {data.verified}/{data.total_sources} ({data.verified_pct}%)
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}

function SourceCard({ s }: { s: SourceEntry }) {
  const isLink = s.url?.startsWith("http");
  return (
    <a
      href={isLink ? s.url! : undefined}
      target="_blank"
      rel="noreferrer"
      className="block rounded-lg border border-line bg-bg-soft p-3 hover:border-accent/50"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-medium text-ink leading-snug">{s.title}</span>
        {isLink && <ExternalLink className="h-3.5 w-3.5 shrink-0 text-ink-dim" />}
      </div>
      <div className="mt-1 text-xs text-ink-dim">
        {s.author}
        {s.publication_year ? ` · ${s.publication_year}` : ""}
      </div>
      {s.excerpt && (
        <p className="mt-2 text-xs text-ink-soft leading-relaxed line-clamp-3">{s.excerpt}</p>
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
    <Card className="p-6">
      <SectionTitle
        title="Evidence sources"
        subtitle="The sources behind the cultural observations"
      />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {sources.map((s, i) => (
          <SourceCard key={`${s.source_id}-${i}`} s={s} />
        ))}
      </div>
    </Card>
  );
}

export function EvidenceTab({ iso3 }: { iso3: string }) {
  return (
    <div className="space-y-6">
      <SourceReliability iso3={iso3} />
      <SourcesGrid iso3={iso3} />
    </div>
  );
}
