"use client";

import Link from "next/link";
import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { EmptyState } from "@/components/ui";
import { flagEmoji } from "@/lib/utils";
import {
  useSimilar,
  type CountryProfile,
  type CulturalTheme,
  type CompetingForce,
  type CommunicationSignal,
  type TransitionAxis,
  type FriendshipMap,
  type SimilarCulture,
  type LivedExperience,
  type Observation,
  type UniquenessFacet,
  type ExperienceVariation,
} from "@/lib/api";

// ─── Shared primitives ────────────────────────────────────────────────────

function EditorialHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-display text-[1.6rem] uppercase leading-[0.9] tracking-[-0.01em] text-ink dark:text-white">
      {children}
    </h2>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[9px] font-bold uppercase tracking-[0.26em] text-coral-strong dark:text-[#E14B3C]">
      {children}
    </p>
  );
}

function Hairline() {
  return <div className="h-px w-full bg-ink/10 dark:bg-white/8" />;
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

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-sm border border-ink/20 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.1em] text-ink/60 dark:border-white/15 dark:text-white/50">
      {children}
    </span>
  );
}

function BulletRow({ text }: { text: string }) {
  return (
    <li className="flex items-start gap-3 text-[13px] leading-relaxed text-ink/70 dark:text-white/60">
      <span className="mt-[0.4em] h-1 w-1 shrink-0 rounded-full bg-coral-strong dark:bg-[#E14B3C]" />
      <span>{text}</span>
    </li>
  );
}

function ObsRow({ obs }: { obs: Observation }) {
  return <BulletRow text={obs.text} />;
}

// ─── Good For tags ────────────────────────────────────────────────────────

function GoodFor({ items }: { items: string[] }) {
  if (!items?.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-ink/35 dark:text-white/30">
        Good for
      </span>
      {items.map((x) => (
        <Tag key={x}>{x}</Tag>
      ))}
    </div>
  );
}

// ─── Theme card (editorial row style) ────────────────────────────────────

function ThemeCard({ theme, index }: { theme: CulturalTheme; index: number }) {
  const ev = theme.confidence.evidence_strength ?? 0;
  const ag = theme.confidence.expert_agreement ?? 0;

  return (
    <div className="py-5 first:pt-0">
      {/* Title row */}
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-[15px] font-semibold leading-snug text-ink dark:text-white">
          {theme.title}
        </h3>
        <span className="shrink-0 text-[10px] font-bold uppercase tracking-[0.16em] text-coral-strong dark:text-[#E14B3C]">
          {theme.confidence.evidence_strength_label ?? ""}
        </span>
      </div>

      {/* Score bars */}
      <div className="mt-3 space-y-2">
        <div className="flex items-center gap-3">
          <span className="w-32 shrink-0 text-[9px] font-bold uppercase tracking-[0.16em] text-ink/35 dark:text-white/30">
            Evidence
          </span>
          <ScoreBar value={ev} />
          <span className="w-6 shrink-0 text-right text-[10px] tabular-nums text-ink/50 dark:text-white/40">
            {Math.round(ev)}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="w-32 shrink-0 text-[9px] font-bold uppercase tracking-[0.16em] text-ink/35 dark:text-white/30">
            Expert Agreement
          </span>
          <ScoreBar value={ag} />
          <span className="w-6 shrink-0 text-right text-[10px] tabular-nums text-ink/50 dark:text-white/40">
            {Math.round(ag)}
          </span>
        </div>
      </div>

      {/* Observations */}
      {theme.observations.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {theme.observations.map((o, i) => (
            <ObsRow key={i} obs={o} />
          ))}
        </ul>
      )}

      {/* Historical roots */}
      {theme.historical_roots.length > 0 && (
        <div className="mt-3 border-t border-ink/8 pt-3 dark:border-white/8">
          <p className="mb-2 text-[9px] font-bold uppercase tracking-[0.2em] text-ink/35 dark:text-white/30">
            Why this exists
          </p>
          <ul className="space-y-1.5">
            {theme.historical_roots.map((r, i) => (
              <ObsRow key={i} obs={r} />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function CulturalThemes({ profile }: { profile: CountryProfile }) {
  const themes = [...(profile.cultural_themes ?? [])].sort(
    (a, b) => b.confidence.evidence_strength - a.confidence.evidence_strength,
  );
  if (themes.length === 0) return null;

  return (
    <div>
      {/* Section heading */}
      <div className="mb-1 flex items-baseline justify-between">
        <EditorialHeading>What defines this culture</EditorialHeading>
        <span className="text-[11px] text-ink/40 dark:text-white/30">
          Themes emerging from the evidence on {profile.country}
        </span>
      </div>
      <Hairline />

      {/* Two-column grid */}
      <div className="mt-0 grid grid-cols-1 gap-x-12 lg:grid-cols-2">
        {themes.map((t, i) => (
          <div key={i}>
            <ThemeCard theme={t} index={i + 1} />
            <Hairline />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Culture at a glance ─────────────────────────────────────────────────

function CultureAtAGlance({ items }: { items: string[] }) {
  const bullets = (items ?? []).filter(Boolean);
  if (bullets.length === 0) return null;
  return (
    <div>
      <div className="mb-4">
        <SectionLabel>The Essentials</SectionLabel>
        <EditorialHeading>
          Culture at
          <br />
          a Glance
        </EditorialHeading>
      </div>
      <Hairline />
      <div className="mt-4 grid grid-cols-1 gap-x-16 gap-y-0 sm:grid-cols-2">
        {bullets.map((b, i) => (
          <div key={i} className="py-3 border-b border-ink/8 dark:border-white/8">
            <div className="flex items-start gap-3">
              <span className="shrink-0 text-[10px] font-bold tabular-nums text-coral-strong dark:text-[#E14B3C] mt-0.5">
                {String(i + 1).padStart(2, "0")}
              </span>
              <p className="text-[13px] leading-relaxed text-ink/70 dark:text-white/60">{b}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Life feels like ─────────────────────────────────────────────────────

function LifeFeelsLike({ profile }: { profile: CountryProfile }) {
  const life = profile.life_feels_like;
  if (!life || !life.text) return null;
  return (
    <div>
      <p className="text-[15px] leading-[1.75] text-ink/70 dark:text-white/60">
        {life.text}
      </p>
      {life.sources_count > 0 && (
        <p className="mt-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-ink/30 dark:text-white/25">
          Based on {life.sources_count} sources
        </p>
      )}
    </div>
  );
}

// ─── Executive summary ────────────────────────────────────────────────────

function ExecutiveSummary({ profile }: { profile: CountryProfile }) {
  if (!profile.executive_summary) return null;
  return (
    <div>
      <p className="text-[15px] leading-[1.75] text-ink/70 dark:text-white/60">
        {profile.executive_summary}
      </p>
      {(profile.good_for ?? profile.best_for)?.length > 0 && (
        <div className="mt-4 pt-4 border-t border-ink/8 dark:border-white/8">
          <GoodFor items={profile.good_for ?? profile.best_for} />
        </div>
      )}
    </div>
  );
}

// ─── Contradictions ───────────────────────────────────────────────────────

function ContradictionsSection({ forces }: { forces: CompetingForce[] }) {
  const items = (forces ?? []).filter((f) => f.pulls_toward && f.but_also);
  if (items.length === 0) return null;
  return (
    <div>
      <EditorialHeading>Cultural contradictions</EditorialHeading>
      <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">Tensions this culture holds at once</p>
      <Hairline />
      <div className="mt-0 divide-y divide-ink/8 dark:divide-white/8">
        {items.map((f, i) => (
          <div key={i} className="py-5 grid grid-cols-[1fr_auto_1fr] items-start gap-4">
            <p className="text-[13px] leading-relaxed text-ink/75 dark:text-white/65">{f.pulls_toward}</p>
            <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink/25 dark:text-white/20 pt-0.5">
              but
            </span>
            <p className="text-[13px] leading-relaxed text-ink/75 dark:text-white/65 text-right">{f.but_also}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Lived experience sections ────────────────────────────────────────────

const EXPERIENCE_SECTIONS: { key: keyof LivedExperience; label: string }[] = [
  { key: "daily_life", label: "Daily life" },
  { key: "workplace_norms", label: "Work" },
  { key: "friendship_social", label: "Relationships" },
  { key: "society", label: "Society" },
];

function ExperienceSection({ profile }: { profile: CountryProfile }) {
  const lived = profile.lived_experience;
  const sections = EXPERIENCE_SECTIONS.filter(
    (s) => (lived?.[s.key]?.length ?? 0) > 0,
  );
  if (sections.length === 0) return null;
  return (
    <div>
      <EditorialHeading>What you would experience</EditorialHeading>
      <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">
        If you moved to {profile.country} tomorrow
      </p>
      <Hairline />
      <div className="mt-4 grid grid-cols-1 gap-x-16 sm:grid-cols-2">
        {sections.map((s) => (
          <div key={s.key} className="py-4 border-b border-ink/8 dark:border-white/8">
            <p className="mb-3 text-[9px] font-bold uppercase tracking-[0.22em] text-ink/40 dark:text-white/35">
              {s.label}
            </p>
            <ul className="space-y-2">
              {lived[s.key].map((o, i) => (
                <ObsRow key={i} obs={o} />
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Success / failure ────────────────────────────────────────────────────

function SuccessFailureSection({ profile }: { profile: CountryProfile }) {
  const success = profile.success_factors ?? [];
  const failure = profile.failure_factors ?? [];
  const mistakes = profile.lived_experience?.social_mistakes_to_avoid ?? [];
  const failureItems = [...failure, ...mistakes];
  if (success.length === 0 && failureItems.length === 0) return null;
  return (
    <div className="grid grid-cols-1 gap-x-16 sm:grid-cols-2">
      {success.length > 0 && (
        <div>
          <p className="mb-3 text-[9px] font-bold uppercase tracking-[0.22em] text-ink/40 dark:text-white/35">
            How to succeed here
          </p>
          <ul className="space-y-2">
            {success.map((o, i) => (
              <ObsRow key={i} obs={o} />
            ))}
          </ul>
        </div>
      )}
      {failureItems.length > 0 && (
        <div>
          <p className="mb-3 text-[9px] font-bold uppercase tracking-[0.22em] text-coral-strong dark:text-[#E14B3C]">
            What creates friction
          </p>
          <ul className="space-y-2">
            {failureItems.map((o, i) => (
              <ObsRow key={i} obs={o} />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ─── Friendship map ───────────────────────────────────────────────────────

const FRIENDSHIP_FACETS: { key: keyof FriendshipMap; label: string }[] = [
  { key: "making_friends", label: "Making friends" },
  { key: "friendship_depth", label: "Depth" },
  { key: "circle_size", label: "Circle size" },
  { key: "trust_formation", label: "Trust" },
  { key: "work_personal_mixing", label: "Work / personal" },
];

function FriendshipMapSection({ map }: { map: FriendshipMap | null }) {
  if (!map) return null;
  const facets = FRIENDSHIP_FACETS.filter((f) => map[f.key]?.label);
  if (facets.length === 0) return null;
  return (
    <div>
      <EditorialHeading>Friendship map</EditorialHeading>
      <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">How relationships work here</p>
      <Hairline />
      <div className="mt-4 grid grid-cols-2 gap-px bg-ink/8 dark:bg-white/8 sm:grid-cols-3 lg:grid-cols-5">
        {facets.map((f) => {
          const facet = map[f.key];
          return (
            <div key={f.key} className="bg-background px-4 py-4 dark:bg-[#0E0E10]">
              <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-ink/35 dark:text-white/30">
                {f.label}
              </p>
              <p className="mt-1.5 text-[13px] font-semibold text-ink dark:text-white">
                {facet.label}
              </p>
              {facet.detail && (
                <p className="mt-1 text-[11px] leading-snug text-ink/50 dark:text-white/40">
                  {facet.detail}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Communication decoder ────────────────────────────────────────────────

function CommunicationDecoderSection({
  signals,
  communication,
}: {
  signals: CommunicationSignal[];
  communication: Observation[];
}) {
  const decoder = (signals ?? []).filter((s) => s.phrase && s.meaning);
  const comms = communication ?? [];
  if (decoder.length === 0 && comms.length === 0) return null;
  return (
    <div>
      <EditorialHeading>Communication decoder</EditorialHeading>
      <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">What people say vs what they mean</p>
      <Hairline />
      {decoder.length > 0 && (
        <div className="mt-0 divide-y divide-ink/8 dark:divide-white/8">
          {decoder.map((s, i) => (
            <div key={i} className="grid grid-cols-[1fr_auto_1fr] items-start gap-6 py-4">
              <p className="text-[13px] italic text-ink/70 dark:text-white/60">
                &ldquo;{s.phrase}&rdquo;
              </p>
              <span className="text-[9px] font-bold uppercase tracking-[0.14em] text-ink/25 dark:text-white/20 pt-1">→</span>
              <p className="text-[13px] text-ink/70 dark:text-white/60">{s.meaning}</p>
            </div>
          ))}
        </div>
      )}
      {comms.length > 0 && (
        <ul className="mt-4 space-y-2">
          {comms.map((o, i) => (
            <ObsRow key={i} obs={o} />
          ))}
        </ul>
      )}
    </div>
  );
}

// ─── Status signals ───────────────────────────────────────────────────────

function StatusSignalsSection({ items }: { items: Observation[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <EditorialHeading>Status signals</EditorialHeading>
      <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">What earns respect here</p>
      <Hairline />
      <div className="mt-4 grid grid-cols-1 gap-x-16 sm:grid-cols-2">
        {items.map((o, i) => (
          <div key={i} className="py-2 border-b border-ink/8 dark:border-white/8">
            <ObsRow obs={o} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Culture in transition ────────────────────────────────────────────────

function TransitionSection({ axes }: { axes: TransitionAxis[] }) {
  const items = (axes ?? []).filter((a) => a.axis && (a.older || a.younger));
  if (items.length === 0) return null;
  return (
    <div>
      <EditorialHeading>Culture in transition</EditorialHeading>
      <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">
        How norms are shifting across generations
      </p>
      <Hairline />
      <div className="mt-0 divide-y divide-ink/8 dark:divide-white/8">
        {items.map((a, i) => (
          <div key={i} className="py-4">
            <p className="mb-2 text-[9px] font-bold uppercase tracking-[0.18em] text-ink/40 dark:text-white/30">
              {a.axis}
            </p>
            <div className="flex flex-wrap items-center gap-3 text-[13px]">
              <span className="text-ink/55 dark:text-white/50">{a.older}</span>
              <span className="text-[10px] text-ink/25 dark:text-white/20">→</span>
              <span className="font-medium text-ink dark:text-white">{a.younger}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Experience variations ────────────────────────────────────────────────

function ExperienceVariationsSection({ items }: { items: ExperienceVariation[] }) {
  const variations = (items ?? []).filter(
    (v) => v.group_a && v.group_b && v.difference,
  );
  if (variations.length === 0) return null;
  return (
    <div>
      <EditorialHeading>How different groups experience this</EditorialHeading>
      <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">Why there is no single version of this culture</p>
      <Hairline />
      <div className="mt-0 divide-y divide-ink/8 dark:divide-white/8">
        {variations.map((v, i) => (
          <div key={i} className="py-4">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="text-[12px] font-semibold text-ink dark:text-white">{v.group_a}</span>
              <span className="text-[9px] text-ink/30 dark:text-white/25">vs</span>
              <span className="text-[12px] font-semibold text-ink/55 dark:text-white/50">{v.group_b}</span>
            </div>
            <p className="text-[13px] leading-relaxed text-ink/65 dark:text-white/55">{v.difference}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── What makes unique ────────────────────────────────────────────────────

function WhatMakesUnique({ profile }: { profile: CountryProfile }) {
  const lines = profile.regional_distinctiveness ?? [];
  if (lines.length === 0) return null;
  return (
    <div>
      <EditorialHeading>What makes {profile.country} distinct</EditorialHeading>
      <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">Relative to its neighbours</p>
      <Hairline />
      <div className="mt-4 flex flex-wrap gap-2">
        {lines.map((l, i) => (
          <Tag key={i}>{l.text}</Tag>
        ))}
      </div>
    </div>
  );
}

// ─── Country uniqueness ───────────────────────────────────────────────────

function CountryUniquenessSection({ profile }: { profile: CountryProfile }) {
  const facets: UniquenessFacet[] = (profile.country_uniqueness ?? []).filter(
    (f) => f.title && f.explanation,
  );
  if (facets.length === 0) return null;
  return (
    <div>
      <EditorialHeading>What makes {profile.country} unique</EditorialHeading>
      <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">How it stands apart from its nearest neighbours</p>
      <Hairline />
      <div className="mt-0 grid grid-cols-1 gap-x-16 lg:grid-cols-2 divide-y divide-ink/8 dark:divide-white/8 lg:divide-y-0">
        {facets.map((f, i) => (
          <div key={i} className="py-5">
            <p className="text-[13px] font-semibold text-ink dark:text-white">{f.title}</p>
            <p className="mt-2 text-[13px] leading-relaxed text-ink/65 dark:text-white/55">
              {f.explanation}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Similar cultures ─────────────────────────────────────────────────────

function SimilarityPanel({ iso3 }: { iso3: string }) {
  const { data } = useSimilar(iso3);
  if (!data || !data.ready) return null;
  return (
    <div>
      <EditorialHeading>Closest &amp; most different cultures</EditorialHeading>
      <Hairline />
      <div className="mt-4 grid grid-cols-1 gap-x-16 sm:grid-cols-2">
        <div>
          <p className="mb-3 text-[9px] font-bold uppercase tracking-[0.2em] text-ink/40 dark:text-white/30">
            Most similar
          </p>
          {data.most_similar.map((c) => (
            <Link
              key={c.iso3}
              href={`/country/${c.iso3}`}
              className="flex items-center justify-between py-2 border-b border-ink/8 dark:border-white/8 hover:opacity-70 transition"
            >
              <span className="flex items-center gap-2 text-[13px] text-ink dark:text-white">
                <span>{flagEmoji(c.iso3)}</span> {c.country}
              </span>
              <span className="text-[11px] tabular-nums text-ink/40 dark:text-white/35">
                {c.similarity}%
              </span>
            </Link>
          ))}
        </div>
        <div>
          <p className="mb-3 text-[9px] font-bold uppercase tracking-[0.2em] text-coral-strong dark:text-[#E14B3C]">
            Most different
          </p>
          {data.most_different.map((c) => (
            <Link
              key={c.iso3}
              href={`/country/${c.iso3}`}
              className="flex items-center justify-between py-2 border-b border-ink/8 dark:border-white/8 hover:opacity-70 transition"
            >
              <span className="flex items-center gap-2 text-[13px] text-ink dark:text-white">
                <span>{flagEmoji(c.iso3)}</span> {c.country}
              </span>
              <span className="text-[11px] tabular-nums text-ink/40 dark:text-white/35">
                {c.similarity}%
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

function SimilarCulturesSection({ profile }: { profile: CountryProfile }) {
  const cultures: SimilarCulture[] = profile.similar_cultures ?? [];
  if (cultures.length === 0) return <SimilarityPanel iso3={profile.iso3} />;
  return (
    <div>
      <EditorialHeading>Similar cultures, explained</EditorialHeading>
      <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">
        Why these countries feel close to {profile.country}
      </p>
      <Hairline />
      <div className="mt-0 divide-y divide-ink/8 dark:divide-white/8">
        {cultures.map((c) => (
          <div key={c.iso3} className="py-4">
            <Link
              href={`/country/${c.iso3}`}
              className="flex items-center justify-between hover:opacity-70 transition"
            >
              <span className="flex items-center gap-2 text-[13px] font-medium text-ink dark:text-white">
                <span>{flagEmoji(c.iso3)}</span> {c.country}
              </span>
              {c.similarity > 0 && (
                <span className="text-[11px] tabular-nums text-ink/40 dark:text-white/35">
                  {c.similarity}% similar
                </span>
              )}
            </Link>
            {c.explanation && (
              <p className="mt-2 text-[13px] leading-relaxed text-ink/60 dark:text-white/50">
                {c.explanation}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Newcomer impressions ─────────────────────────────────────────────────

function NewcomerSection({ items }: { items: Observation[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <EditorialHeading>What newcomers notice first</EditorialHeading>
      <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">The immediate impressions on arrival</p>
      <Hairline />
      <div className="mt-4 grid grid-cols-1 gap-x-16 sm:grid-cols-2">
        {items.map((o, i) => (
          <div key={i} className="py-2 border-b border-ink/8 dark:border-white/8">
            <ObsRow obs={o} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Trust accordion ──────────────────────────────────────────────────────

function TrustSection({ profile }: { profile: CountryProfile }) {
  const [open, setOpen] = useState(false);
  const t = profile.trust;
  const items = [
    `${t.framework_count} cultural frameworks (${t.frameworks.join(", ")})`,
    `${t.specialist_count} independent AI specialists researched and debated`,
    "Every observation is linked to underlying evidence sources",
    t.calibration_passed === null
      ? "Calibration checks applied"
      : `Calibration checks ${t.calibration_passed ? "passed" : "flagged"}`,
    t.human_reviewed
      ? "Flagged for human review (extra scrutiny)"
      : "Cleared the human-review pipeline",
  ];
  return (
    <div className="border-t border-ink/10 dark:border-white/8 pt-6">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between text-left"
      >
        <span className="text-[11px] font-bold uppercase tracking-[0.2em] text-ink/40 dark:text-white/30">
          Why you should trust this
        </span>
        <ChevronDown
          className={`h-3.5 w-3.5 text-ink/30 dark:text-white/25 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <ul className="mt-4 space-y-2">
          {items.map((x, i) => (
            <li key={i} className="text-[12px] text-ink/55 dark:text-white/45 flex items-start gap-2">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-ink/20 dark:bg-white/20" />
              {x}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ─── Root export ──────────────────────────────────────────────────────────

export function OverviewTab({ profile }: { profile: CountryProfile }) {
  return (
    <div className="space-y-14">
      <ExecutiveSummary profile={profile} />
      <CultureAtAGlance items={profile.culture_at_a_glance} />
      <LifeFeelsLike profile={profile} />
      <CulturalThemes profile={profile} />
      <ContradictionsSection forces={profile.competing_forces} />
      <ExperienceSection profile={profile} />
      <NewcomerSection items={profile.newcomer_first_impressions} />
      <SuccessFailureSection profile={profile} />
      <FriendshipMapSection map={profile.friendship_map} />
      <CommunicationDecoderSection
        signals={profile.communication_decoder}
        communication={profile.lived_experience?.communication_style ?? []}
      />
      <StatusSignalsSection
        items={profile.lived_experience?.status_signals ?? []}
      />
      <TransitionSection axes={profile.culture_in_transition} />
      <ExperienceVariationsSection items={profile.experience_variations} />
      <CountryUniquenessSection profile={profile} />
      <SimilarCulturesSection profile={profile} />
      <WhatMakesUnique profile={profile} />
      <TrustSection profile={profile} />
    </div>
  );
}
