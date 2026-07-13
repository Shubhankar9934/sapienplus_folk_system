"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Fingerprint, Gauge, Users } from "lucide-react";
import { useCountry, type CountryProfile } from "@/lib/api";
import { Card, Spinner, Badge, GradeBadge, Meter, SectionTitle } from "@/components/ui";
import { Tabs } from "@/components/Tabs";
import { FolkRadar } from "@/components/FolkRadar";
import { OverviewTab } from "@/components/country/Overview";
import { WhyTab } from "@/components/country/WhyTab";
import { EvidenceTab } from "@/components/country/EvidenceTab";
import { ResearchTab } from "@/components/country/ResearchTab";
import { CulturalDnaCard } from "@/components/country/CulturalDnaCard";
import { ScorePoleBar } from "@/components/country/bits";
import { DIMENSIONS, DIM_BY_CODE, type DimCode } from "@/lib/dimensions";
import { flagEmoji } from "@/lib/utils";

const TABS = [
  { id: "overview", label: "Profile" },
  { id: "why", label: "Why it became this way" },
  { id: "evidence", label: "Evidence" },
  { id: "research", label: "Research & Methodology" },
];

function CulturalFingerprint({ profile }: { profile: CountryProfile }) {
  const radarScores: Partial<Record<DimCode, number | null>> = {};
  const ciLow: Partial<Record<DimCode, number>> = {};
  const ciHigh: Partial<Record<DimCode, number>> = {};
  DIMENSIONS.forEach((d) => {
    const s = profile.scores[d.code];
    radarScores[d.code] = s?.score ?? null;
    if (s?.ci_low != null) ciLow[d.code] = s.ci_low;
    if (s?.ci_high != null) ciHigh[d.code] = s.ci_high;
  });
  const readingFor = (code: DimCode) =>
    (profile.snapshot ?? []).find((s) => s.dimension === code)?.reading ?? "";
  const explanationFor = (code: DimCode) => {
    const row = (profile.snapshot ?? []).find((s) => s.dimension === code);
    const explanation = row?.explanation ?? "";
    // Only show the explanation when it adds something beyond the short reading.
    return explanation && explanation !== row?.reading ? explanation : "";
  };

  return (
    <Card className="p-6">
      <SectionTitle
        title="Cultural fingerprint"
        subtitle="The four dimensions that define this culture"
      />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[340px_1fr]">
        <div>
          <FolkRadar
            series={[{ name: profile.country, color: "#5b8def", scores: radarScores }]}
            ci={{ low: ciLow, high: ciHigh }}
          />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {DIMENSIONS.map((d) => {
            const s = profile.scores[d.code];
            return (
              <div key={d.code} className="rounded-lg border border-line bg-bg-soft p-4">
                <div className="flex items-baseline justify-between">
                  <span className="text-sm text-ink-soft">{DIM_BY_CODE[d.code].label}</span>
                  <span
                    className="text-2xl font-bold tabular-nums"
                    style={{ color: d.color }}
                  >
                    {s?.score ?? "—"}
                  </span>
                </div>
                <div className="text-sm font-medium text-ink mb-1">{readingFor(d.code)}</div>
                {explanationFor(d.code) && (
                  <p className="text-xs leading-relaxed text-ink-dim mb-3">
                    {explanationFor(d.code)}
                  </p>
                )}
                <ScorePoleBar
                  code={d.code}
                  score={s?.score ?? null}
                  ciLow={s?.ci_low}
                  ciHigh={s?.ci_high}
                />
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

function verdictColor(v: string | null) {
  if (!v) return "#9fb0c0";
  if (v.includes("Strong")) return "#34d399";
  if (v.includes("Moderate")) return "#f0b429";
  return "#f87171";
}

export default function CountryPage() {
  const params = useParams();
  const iso3 = String(params.iso3 ?? "").toUpperCase();
  const { data: profile, isLoading, isError } = useCountry(iso3);

  if (isLoading) return <Spinner label="Loading country profile..." />;
  if (isError || !profile)
    return (
      <div className="mx-auto max-w-3xl px-6 py-20 text-center">
        <p className="text-lg font-medium">Country not found</p>
        <Link href="/explore" className="text-accent text-sm mt-2 inline-block">
          Back to explore
        </Link>
      </div>
    );

  const ca = profile.council_agreement;
  const uniqueness = profile.uniqueness;

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 py-8">
      <Link
        href="/explore"
        className="inline-flex items-center gap-1.5 text-sm text-ink-dim hover:text-ink"
      >
        <ArrowLeft className="h-4 w-4" /> Explore
      </Link>

      {/* Header */}
      <div className="mt-4 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-4xl">{flagEmoji(profile.iso3)}</span>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">{profile.country}</h1>
              <p className="text-ink-soft">{profile.region}</p>
            </div>
          </div>

          {profile.cultural_archetype?.title && (
            <div className="mt-3">
              <p className="text-xl font-semibold text-accent">
                {profile.cultural_archetype.title}
              </p>
              {profile.cultural_archetype.summary && (
                <p className="mt-0.5 text-sm text-ink-soft">
                  {profile.cultural_archetype.summary}
                </p>
              )}
            </div>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            {profile.archetype && (
              <Badge color="#5b8def">
                <Fingerprint className="h-3 w-3" />
                {profile.archetype}
              </Badge>
            )}
            <GradeBadge grade={profile.research_grade} />
            {ca.overall != null && (
              <Badge color={verdictColor(ca.verdict)}>
                <Users className="h-3 w-3" />
                Council {ca.overall}% &middot; {ca.verdict}
              </Badge>
            )}
            {uniqueness != null && (
              <Badge color="#e879a6">
                <Gauge className="h-3 w-3" />
                Uniqueness {uniqueness}/100
              </Badge>
            )}
            {profile.requires_human_review && (
              <Badge color="#f0b429">Flagged for human review</Badge>
            )}
          </div>

          {profile.evidence_strength.overall != null && (
            <div className="mt-5 max-w-md">
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-ink-soft">Evidence strength</span>
                <span className="tabular-nums text-ink-soft">
                  {profile.evidence_strength.overall}/100
                </span>
              </div>
              <Meter value={profile.evidence_strength.overall} color="#34d399" />
            </div>
          )}
        </div>

        {/* DNA card */}
        <Card className="p-4">
          <CulturalDnaCard profile={profile} />
        </Card>
      </div>

      {/* Cultural fingerprint — always visible, above the fold */}
      <div className="mt-8">
        <CulturalFingerprint profile={profile} />
      </div>

      {/* Tabs */}
      <div className="mt-8">
        <Tabs tabs={TABS}>
          {(active) => (
            <>
              {active === "overview" && <OverviewTab profile={profile} />}
              {active === "why" && <WhyTab profile={profile} />}
              {active === "evidence" && <EvidenceTab iso3={profile.iso3} />}
              {active === "research" && <ResearchTab profile={profile} />}
            </>
          )}
        </Tabs>
      </div>
    </div>
  );
}
