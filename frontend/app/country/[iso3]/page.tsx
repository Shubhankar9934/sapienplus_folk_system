"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useCountry, type CountryProfile } from "@/lib/api";
import { Spinner } from "@/components/ui";
import { CountryGlobe } from "@/components/CountryGlobe";
import { CountryShape } from "@/components/CountryShape";
import { DIMENSIONS, DIM_BY_CODE, type DimCode } from "@/lib/dimensions";
import { OverviewTab } from "@/components/country/Overview";
import { WhyTab } from "@/components/country/WhyTab";
import { EvidenceTab } from "@/components/country/EvidenceTab";
import { ResearchTab } from "@/components/country/ResearchTab";
import { NavBar } from "@/components/NavBar";
import { useState } from "react";

type TabId = "overview" | "why" | "evidence" | "research";

const TABS: { id: TabId; label: string }[] = [
  { id: "overview", label: "Profile" },
  { id: "why", label: "Why it became this way" },
  { id: "evidence", label: "Evidence" },
  { id: "research", label: "Research" },
];

function DimensionRow({
  profile,
  code,
}: {
  profile: CountryProfile;
  code: DimCode;
}) {
  const dim = DIM_BY_CODE[code];
  const score = profile.scores[code]?.score ?? null;
  const explanation =
    (profile.snapshot ?? []).find((s) => s.dimension === code)?.explanation ??
    (profile.snapshot ?? []).find((s) => s.dimension === code)?.reading ??
    "";
  const markerPos = score !== null ? `${score}%` : "50%";

  return (
    <div className="border-t border-ink/10 pt-6 pb-5 dark:border-white/10">
      <div className="flex items-baseline justify-between">
        <span className="text-[13px] font-semibold uppercase tracking-[0.1em] text-ink dark:text-white">
          {dim.label}
        </span>
        <span className="font-display text-5xl tabular-nums leading-none text-ink dark:text-white">
          {score ?? "—"}
        </span>
      </div>
      {explanation && (
        <p className="mt-3 max-w-[34ch] text-[12px] leading-relaxed text-ink/50 dark:text-white/45">
          {explanation}
        </p>
      )}
      <div className="mt-5">
        <div className="relative h-px w-full bg-ink/18 dark:bg-white/18">
          {score !== null && (
            <div
              className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-ink ring-[3px] ring-coral-strong/30 dark:bg-white dark:ring-[#E14B3C]/35"
              style={{ left: markerPos }}
            />
          )}
        </div>
        <div className="mt-2 flex items-center justify-between text-[9px] uppercase tracking-[0.18em] text-ink/38 dark:text-white/32">
          <span>{dim.low}</span>
          <span>{dim.high}</span>
        </div>
      </div>
    </div>
  );
}

export default function CountryPage() {
  const params = useParams();
  const router = useRouter();
  const iso3 = String(params.iso3 ?? "").toUpperCase();
  const { data: profile, isLoading, isError } = useCountry(iso3);
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  if (isLoading) return <Spinner label="Loading country profile..." />;
  if (isError || !profile)
    return (
      <div className="mx-auto max-w-3xl px-6 py-20 text-center">
        <p className="text-lg font-medium">Country not found</p>
        <Link href="/explore" className="mt-2 inline-block text-sm text-accent">
          Back to explore
        </Link>
      </div>
    );

  const displayName = profile.country;
  const evidenceScore = profile.evidence_strength.overall || 0;
  const consensusScore = profile.council_agreement.overall || 0;
  const grade = profile.research_grade || "A";


  return (
    <div className="min-h-screen bg-white dark:bg-[#0E0E10]">
      {/* NAV — shared site navbar with SideMenu */}
      <NavBar />

      {/* Back button */}
      <div className="px-6 pt-4 md:px-10">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-sm text-ink/55 transition hover:text-ink dark:text-white/45 dark:hover:text-white"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-full border border-ink/18 dark:border-white/18">
            <ArrowLeft className="h-3.5 w-3.5" />
          </span>
          <span className="hidden md:inline">Back</span>
        </button>
      </div>

      {/* MASTHEAD */}
      <section className="px-6 pb-0 pt-4 text-center md:px-10">
        <p className="text-[9px] uppercase tracking-[0.22em] text-ink/45 dark:text-white/40">
          {profile.cultural_archetype?.title?.toUpperCase() || "RESERVED COLLECTIVISTS"}
        </p>

        <div className="relative mt-1 inline-block">
          <h1
            className="font-display uppercase leading-[0.85] tracking-[-0.02em] text-ink dark:text-white"
            style={{ fontSize: "clamp(4rem, 13vw, 10.5rem)" }}
          >
            {displayName.toUpperCase()}
          </h1>
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="pointer-events-auto w-[150px] h-[150px] translate-y-12">
              <CountryGlobe onSelect={() => {}} selectedName={displayName} staticMode />
            </div>
          </div>
        </div>

        <p className="mx-auto mt-4 max-w-sm text-[13px] leading-relaxed text-ink/50 dark:text-white/45">
          {profile.cultural_archetype?.summary || profile.region}
        </p>
      </section>

      {/* HEADLINE STATS */}
      <section className="mx-auto mt-10 max-w-[860px] px-6 md:px-10">
        <div className="grid grid-cols-1 border-t border-ink/12 dark:border-white/12 md:grid-cols-[1fr_1.5fr]">
          {/* Evidence Strength */}
          <div className="border-b border-ink/12 py-8 dark:border-white/12 md:border-b-0 md:pr-12">
            <p className="text-[9px] uppercase tracking-[0.22em] text-ink/42 dark:text-white/38">
              Evidence Strength
            </p>
            <div className="mt-2.5 flex items-end gap-3">
              <span className="font-display leading-none tabular-nums text-ink dark:text-white" style={{ fontSize: "4.5rem" }}>
                {evidenceScore}
              </span>
              <span className="mb-2 text-2xl font-light text-ink/28 dark:text-white/28">/ 100</span>
            </div>
            <p className="mt-3 max-w-[30ch] text-[12px] leading-relaxed text-ink/48 dark:text-white/42">
              How strong the underlying research base is for this country, based on sample coverage, recency and method quality.
            </p>
          </div>

          {/* Council Consensus */}
          <div className="relative py-8 md:pl-12 flex items-center justify-between min-h-[220px]">
            {/* Background Map */}
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <CountryShape iso3={profile.iso3} className="text-ink opacity-[0.03] dark:text-white dark:opacity-[0.05] w-[140%] h-[140%] max-h-[350px] -translate-y-4" />
            </div>

            <div className="relative z-10 flex items-center gap-6 w-full">
              {/* Black circle */}
              <div className="shrink-0 inline-flex h-14 w-14 items-center justify-center rounded-full bg-ink text-white dark:bg-white dark:text-[#0E0E10]">
                <span className="font-display text-xl font-bold">{grade}</span>
              </div>

              {/* Text block */}
              <div className="flex-1">
                <p className="text-[9px] uppercase tracking-[0.22em] text-ink/42 dark:text-white/38">
                  Council Consensus
                </p>
                <div className="mt-1 flex items-end gap-2">
                  <span className="font-display leading-none tabular-nums text-ink dark:text-white" style={{ fontSize: "4.5rem" }}>
                    {consensusScore}
                  </span>
                  <span className="mb-2 text-2xl font-light text-ink/28 dark:text-white/28">%</span>
                </div>
                <p className="mt-3 max-w-[30ch] text-[12px] leading-relaxed text-ink/48 dark:text-white/42">
                  How closely independent reviewers agree on the placement of this culture across the four dimensions.
                </p>
              </div>

              {/* Red circle */}
              <div className="shrink-0 inline-flex h-14 w-14 items-center justify-center rounded-full bg-coral-strong text-white dark:bg-[#E14B3C]">
                <span className="font-display text-xl font-bold">
                  {profile.council_agreement.verdict?.charAt(0) || "S"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CULTURAL FINGERPRINT */}
      <section className="mx-auto mt-4 max-w-[860px] px-6 pb-16 md:px-10">
        <div className="grid gap-8 md:grid-cols-[180px_1fr]">
          <div className="md:sticky md:top-8 md:self-start md:pt-6">
            <p className="text-[9px] uppercase tracking-[0.2em] text-ink/38 dark:text-white/32">
              {displayName.toUpperCase()}
            </p>
            <h2 className="mt-2 font-display text-[2.1rem] uppercase leading-[0.88] tracking-[-0.01em] text-ink dark:text-white">
              Cultural<br />Fingerprint
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-x-10 sm:grid-cols-2">
            {DIMENSIONS.map((d) => (
              <DimensionRow key={d.code} profile={profile} code={d.code} />
            ))}
          </div>
        </div>
      </section>

      {/* EDITORIAL READER */}
      <section className="border-t border-ink/10 bg-[#F4F4F2] px-6 py-20 dark:border-white/10 dark:bg-[#141518] md:px-10">
        <div className="mx-auto max-w-[860px]">
          <div className="text-center">
            <p className="text-[9px] uppercase tracking-[0.22em] text-ink/42 dark:text-white/38">
              Understand {displayName}
            </p>
            <h2
              className="mt-3 font-display uppercase leading-[0.88] tracking-[-0.02em] text-ink dark:text-white"
              style={{ fontSize: "clamp(2.4rem, 6vw, 5rem)" }}
            >
              What life feels like
              <br />
              inside the culture
            </h2>
          </div>

          <div className="mt-10 overflow-x-auto">
            <div className="flex flex-nowrap justify-center gap-8 border-b border-ink/12 dark:border-white/12">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`whitespace-nowrap pb-3 text-[11px] uppercase tracking-[0.12em] font-medium transition ${
                    activeTab === tab.id
                      ? "-mb-px border-b-2 border-ink text-ink dark:border-white dark:text-white"
                      : "text-ink/38 hover:text-ink dark:text-white/38 dark:hover:text-white"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-12">
            {activeTab === "overview" && (
              <div className="mx-auto max-w-5xl">
                <OverviewTab profile={profile} />
              </div>
            )}
            {activeTab === "why" && (
              <div className="mx-auto max-w-5xl">
                <WhyTab profile={profile} />
              </div>
            )}
            {activeTab === "evidence" && (
              <div className="mx-auto max-w-5xl">
                <EvidenceTab iso3={profile.iso3} />
              </div>
            )}
            {activeTab === "research" && (
              <div className="mx-auto max-w-5xl">
                <ResearchTab profile={profile} />
              </div>
            )}
          </div>

          <div className="mt-16 text-center">
            <Link
              href="/compare"
              className="inline-flex items-center gap-2 border-b border-ink/28 pb-0.5 text-[12px] uppercase tracking-[0.12em] font-medium text-ink transition hover:border-ink dark:border-white/28 dark:text-white dark:hover:border-white"
            >
              Compare with other countries
              <ArrowLeft className="h-3 w-3 rotate-180" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}


