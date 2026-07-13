"use client";

import { ShieldCheck, GitCompareArrows } from "lucide-react";
import { Card, SectionTitle, EmptyState } from "@/components/ui";
import type { CountryProfile, Observation } from "@/lib/api";

function SourcesChip({ count }: { count: number }) {
  if (!count) return null;
  return (
    <span className="ml-2 inline-flex items-center gap-1 rounded-full border border-line bg-bg-soft px-2 py-0.5 text-[11px] text-ink-dim">
      <ShieldCheck className="h-3 w-3 text-pos" />
      {count} {count === 1 ? "source" : "sources"}
    </span>
  );
}

function DriverRow({ d }: { d: Observation }) {
  return (
    <li className="flex items-start gap-2 text-sm text-ink-soft leading-relaxed">
      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
      <span>
        {d.text}
        <SourcesChip count={d.sources_count} />
      </span>
    </li>
  );
}

function CompetingForces({ profile }: { profile: CountryProfile }) {
  const forces = profile.competing_forces ?? [];
  if (forces.length === 0) return null;
  return (
    <Card className="p-6">
      <SectionTitle
        title="Competing cultural forces"
        subtitle="Tensions that shape everyday choices"
      />
      <div className="space-y-3">
        {forces.map((f, i) => (
          <div
            key={i}
            className="flex flex-col gap-2 rounded-lg border border-line bg-bg-soft p-4 sm:flex-row sm:items-center"
          >
            <span className="flex-1 text-sm text-ink">{f.pulls_toward}</span>
            <GitCompareArrows className="h-4 w-4 shrink-0 text-ink-dim" />
            <span className="flex-1 text-sm text-ink sm:text-right">{f.but_also}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function WhyTab({ profile }: { profile: CountryProfile }) {
  const drivers = profile.historical_drivers ?? [];
  const hasContent = drivers.length > 0 || (profile.competing_forces ?? []).length > 0;

  if (!hasContent) {
    return (
      <EmptyState
        title="Not enough evidence yet"
        message={`No grounded historical drivers were found for ${profile.country}.`}
      />
    );
  }

  return (
    <div className="space-y-6">
      {drivers.length > 0 && (
        <Card className="p-6">
          <SectionTitle
            title={`Why ${profile.country} became this way`}
            subtitle="Historical and structural drivers, each linked to evidence"
          />
          <ul className="space-y-2.5">
            {drivers.map((d, i) => (
              <DriverRow key={i} d={d} />
            ))}
          </ul>
        </Card>
      )}
      <CompetingForces profile={profile} />
    </div>
  );
}
