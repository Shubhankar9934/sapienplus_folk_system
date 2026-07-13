"use client";

import Link from "next/link";
import {
  ChevronDown,
  ShieldCheck,
  Sparkles,
  Star,
  Quote,
  TrendingUp,
  TrendingDown,
  Eye,
  Users2,
  MessageSquare,
  Crown,
  GitCompareArrows,
  Scale,
  ListChecks,
  Heart,
  Fingerprint,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { Card, SectionTitle, EmptyState } from "@/components/ui";
import { evidenceRating, confidenceMeta, type ConfidenceLabel } from "@/lib/dimensions";
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

function SourcesChip({ count }: { count: number }) {
  if (!count) return null;
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-line bg-bg-soft px-2 py-0.5 text-[11px] text-ink-dim">
      <ShieldCheck className="h-3 w-3 text-pos" />
      Supported by {count} {count === 1 ? "source" : "sources"}
    </span>
  );
}

function ObservationRow({ obs }: { obs: Observation }) {
  return (
    <li className="flex items-start gap-2 text-sm text-ink-soft leading-relaxed">
      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
      <span>
        {obs.text}
        {obs.sources_count > 0 && (
          <span className="ml-2 align-middle">
            <SourcesChip count={obs.sources_count} />
          </span>
        )}
      </span>
    </li>
  );
}

function ConfidenceBar({
  label,
  value,
  band,
}: {
  label: string;
  value: number;
  band: string;
}) {
  const color = confidenceMeta(band as ConfidenceLabel).color;
  return (
    <div className="flex items-center gap-2">
      <span className="w-28 shrink-0 text-[10px] uppercase tracking-wide text-ink-dim">
        {label}
      </span>
      <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-bg-soft">
        <span
          className="block h-full rounded-full"
          style={{ width: `${Math.max(0, Math.min(100, value))}%`, backgroundColor: color }}
        />
      </span>
      <span
        className="w-16 shrink-0 text-right text-[10px] font-medium"
        style={{ color }}
      >
        {band}
      </span>
    </div>
  );
}

function ThemeCard({ theme }: { theme: CulturalTheme }) {
  const rating = evidenceRating(theme.confidence.evidence_strength);
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-lg font-semibold text-ink">{theme.title}</h3>
        <div className="flex flex-col items-end">
          <div className="flex items-center gap-0.5">
            {[1, 2, 3].map((i) => (
              <Star
                key={i}
                className="h-3.5 w-3.5"
                style={{ color: i <= rating.stars ? rating.color : "#2a3949" }}
                fill={i <= rating.stars ? rating.color : "none"}
              />
            ))}
          </div>
          <span className="mt-0.5 text-[11px]" style={{ color: rating.color }}>
            {rating.label}
          </span>
        </div>
      </div>

      <div className="mt-3 space-y-1.5 rounded-lg border border-line/60 bg-bg-soft/40 p-3">
        <ConfidenceBar
          label="Evidence"
          value={theme.confidence.evidence_strength}
          band={theme.confidence.evidence_strength_label}
        />
        <ConfidenceBar
          label="Expert agreement"
          value={theme.confidence.expert_agreement}
          band={theme.confidence.expert_agreement_label}
        />
        <ConfidenceBar
          label="Framework agreement"
          value={theme.confidence.framework_agreement}
          band={theme.confidence.framework_agreement_label}
        />
        {theme.confidence.confidence_explanation && (
          <p className="pt-1 text-[11px] leading-relaxed text-ink-dim">
            {theme.confidence.confidence_explanation}
          </p>
        )}
      </div>

      <ul className="mt-4 space-y-2.5">
        {theme.observations.map((o, i) => (
          <ObservationRow key={i} obs={o} />
        ))}
      </ul>

      {theme.historical_roots.length > 0 && (
        <div className="mt-4 border-t border-line/60 pt-3">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-dim mb-2">
            Why this exists
          </div>
          <ul className="space-y-2">
            {theme.historical_roots.map((r, i) => (
              <ObservationRow key={i} obs={r} />
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

function CulturalThemes({ profile }: { profile: CountryProfile }) {
  const themes = [...(profile.cultural_themes ?? [])].sort(
    (a, b) => b.confidence.evidence_strength - a.confidence.evidence_strength
  );
  return (
    <div>
      <SectionTitle
        title="What defines this culture"
        subtitle={`The themes that emerge from the evidence on ${profile.country}`}
      />
      {themes.length === 0 ? (
        <EmptyState
          title="Not enough evidence yet"
          message="No cultural themes met the evidence bar for this country."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {themes.map((t, i) => (
            <ThemeCard key={i} theme={t} />
          ))}
        </div>
      )}
    </div>
  );
}

function GoodFor({ items }: { items: string[] }) {
  if (!items?.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs uppercase tracking-wide text-ink-dim">Good for</span>
      {items.map((x) => (
        <span
          key={x}
          className="rounded-full border border-accent/40 bg-accent/10 px-3 py-1 text-xs font-medium text-accent"
        >
          {x}
        </span>
      ))}
    </div>
  );
}

// "What you would experience" — the four lived-experience buckets.
const EXPERIENCE_SECTIONS: { key: keyof LivedExperience; label: string }[] = [
  { key: "daily_life", label: "Daily life" },
  { key: "workplace_norms", label: "Work" },
  { key: "friendship_social", label: "Relationships" },
  { key: "society", label: "Society" },
];

function ExperienceSection({ profile }: { profile: CountryProfile }) {
  const lived = profile.lived_experience;
  const sections = EXPERIENCE_SECTIONS.filter((s) => (lived?.[s.key]?.length ?? 0) > 0);
  if (sections.length === 0) return null;
  return (
    <div>
      <SectionTitle
        title="What you would experience"
        subtitle={`If you moved to ${profile.country} tomorrow, here is what daily reality looks like`}
      />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {sections.map((s) => (
          <Card key={s.key} className="p-5">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-ink-dim">
              {s.label}
            </h3>
            <ul className="mt-3 space-y-2.5">
              {lived[s.key].map((o, i) => (
                <ObservationRow key={i} obs={o} />
              ))}
            </ul>
          </Card>
        ))}
      </div>
    </div>
  );
}

function ContradictionsSection({ forces }: { forces: CompetingForce[] }) {
  const items = (forces ?? []).filter((f) => f.pulls_toward && f.but_also);
  if (items.length === 0) return null;
  return (
    <div>
      <SectionTitle
        title="Cultural contradictions"
        subtitle="Tensions this culture holds at once"
      />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {items.map((f, i) => (
          <Card key={i} className="p-5">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <span className="rounded-md bg-accent/10 px-2 py-1 text-accent">
                {f.pulls_toward}
              </span>
              <span className="text-ink-dim">but</span>
              <span className="rounded-md bg-[#e879a6]/10 px-2 py-1 text-[#e879a6]">
                {f.but_also}
              </span>
            </div>
            {f.explanation && (
              <p className="mt-3 text-sm leading-relaxed text-ink-soft">{f.explanation}</p>
            )}
            {f.sources_count > 0 && (
              <div className="mt-3">
                <SourcesChip count={f.sources_count} />
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

function ObservationListSection({
  title,
  subtitle,
  icon,
  items,
}: {
  title: string;
  subtitle: string;
  icon: ReactNode;
  items: Observation[];
}) {
  if (!items?.length) return null;
  return (
    <Card className="p-6">
      <div className="flex items-center gap-2">
        {icon}
        <SectionTitle title={title} subtitle={subtitle} />
      </div>
      <ul className="mt-4 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {items.map((o, i) => (
          <ObservationRow key={i} obs={o} />
        ))}
      </ul>
    </Card>
  );
}

function SuccessFailureSection({ profile }: { profile: CountryProfile }) {
  const success = profile.success_factors ?? [];
  const failure = profile.failure_factors ?? [];
  const mistakes = profile.lived_experience?.social_mistakes_to_avoid ?? [];
  const failureItems = [...failure, ...mistakes];
  if (success.length === 0 && failureItems.length === 0) return null;
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {success.length > 0 && (
        <Card className="p-6">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-pos" />
            <SectionTitle title="How to succeed here" subtitle="What gets people ahead" />
          </div>
          <ul className="mt-4 space-y-2.5">
            {success.map((o, i) => (
              <ObservationRow key={i} obs={o} />
            ))}
          </ul>
        </Card>
      )}
      {failureItems.length > 0 && (
        <Card className="p-6">
          <div className="flex items-center gap-2">
            <TrendingDown className="h-4 w-4 text-neg" />
            <SectionTitle title="What creates friction" subtitle="Mistakes to avoid" />
          </div>
          <ul className="mt-4 space-y-2.5">
            {failureItems.map((o, i) => (
              <ObservationRow key={i} obs={o} />
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

const FRIENDSHIP_FACETS: { key: keyof FriendshipMap; label: string }[] = [
  { key: "making_friends", label: "Making friends" },
  { key: "friendship_depth", label: "Friendship depth" },
  { key: "circle_size", label: "Circle size" },
  { key: "trust_formation", label: "Trust formation" },
  { key: "work_personal_mixing", label: "Work / personal mixing" },
];

function FriendshipMapSection({ map }: { map: FriendshipMap | null }) {
  if (!map) return null;
  const facets = FRIENDSHIP_FACETS.filter((f) => map[f.key]?.label);
  if (facets.length === 0) return null;
  return (
    <Card className="p-6">
      <div className="flex items-center gap-2">
        <Users2 className="h-4 w-4 text-accent" />
        <SectionTitle title="Friendship map" subtitle="How relationships work here" />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {facets.map((f) => {
          const facet = map[f.key];
          return (
            <div
              key={f.key}
              className="rounded-lg border border-line bg-bg-soft p-3 text-center"
            >
              <div className="text-[11px] uppercase tracking-wide text-ink-dim">
                {f.label}
              </div>
              <div className="mt-1 text-lg font-semibold text-ink">{facet.label}</div>
              {facet.detail && (
                <div className="mt-1 text-[11px] text-ink-dim">{facet.detail}</div>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}

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
    <Card className="p-6">
      <div className="flex items-center gap-2">
        <MessageSquare className="h-4 w-4 text-accent" />
        <SectionTitle
          title="Communication decoder"
          subtitle="What people say vs what they mean"
        />
      </div>
      {decoder.length > 0 && (
        <div className="mt-4 space-y-3">
          {decoder.map((s, i) => (
            <div
              key={i}
              className="grid grid-cols-1 gap-1 rounded-lg border border-line bg-bg-soft p-4 sm:grid-cols-[1fr_auto_1fr] sm:items-center sm:gap-3"
            >
              <div className="text-sm italic text-ink">&ldquo;{s.phrase}&rdquo;</div>
              <GitCompareArrows className="hidden h-4 w-4 text-ink-dim sm:block" />
              <div className="text-sm font-medium text-ink-soft">{s.meaning}</div>
            </div>
          ))}
        </div>
      )}
      {comms.length > 0 && (
        <ul className="mt-4 space-y-2.5">
          {comms.map((o, i) => (
            <ObservationRow key={i} obs={o} />
          ))}
        </ul>
      )}
    </Card>
  );
}

function StatusSignalsSection({ items }: { items: Observation[] }) {
  if (!items?.length) return null;
  return (
    <Card className="p-6">
      <div className="flex items-center gap-2">
        <Crown className="h-4 w-4 text-[#f0b429]" />
        <SectionTitle title="Status signals" subtitle="What earns respect here" />
      </div>
      <ul className="mt-4 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {items.map((o, i) => (
          <ObservationRow key={i} obs={o} />
        ))}
      </ul>
    </Card>
  );
}

function TransitionSection({ axes }: { axes: TransitionAxis[] }) {
  const items = (axes ?? []).filter((a) => a.axis && (a.older || a.younger));
  if (items.length === 0) return null;
  return (
    <Card className="p-6">
      <div className="flex items-center gap-2">
        <Scale className="h-4 w-4 text-accent" />
        <SectionTitle
          title="Culture in transition"
          subtitle="How norms are shifting across generations and places"
        />
      </div>
      <div className="mt-4 space-y-3">
        {items.map((a, i) => (
          <div key={i} className="rounded-lg border border-line bg-bg-soft p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-dim">
              {a.axis}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
              <span className="rounded-md bg-bg-hover px-2 py-1 text-ink-soft">{a.older}</span>
              <TrendingUp className="h-4 w-4 rotate-45 text-ink-dim" />
              <span className="rounded-md bg-accent/10 px-2 py-1 text-accent">{a.younger}</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function SimilarCulturesSection({
  profile,
}: {
  profile: CountryProfile;
}) {
  const cultures: SimilarCulture[] = profile.similar_cultures ?? [];
  if (cultures.length === 0) return <SimilarityPanel iso3={profile.iso3} />;
  return (
    <Card className="p-6">
      <SectionTitle
        title="Similar cultures, explained"
        subtitle={`Why these countries feel close to ${profile.country} — and how it differs`}
      />
      <div className="mt-4 space-y-3">
        {cultures.map((c) => (
          <div key={c.iso3} className="rounded-lg border border-line bg-bg-soft p-4">
            <Link
              href={`/country/${c.iso3}`}
              className="flex items-center justify-between hover:opacity-80"
            >
              <span className="flex items-center gap-2 text-sm font-medium">
                <span>{flagEmoji(c.iso3)}</span>
                {c.country}
              </span>
              {c.similarity > 0 && (
                <span className="text-xs tabular-nums text-ink-soft">{c.similarity}% similar</span>
              )}
            </Link>
            {c.explanation && (
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">{c.explanation}</p>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

function WhatMakesUnique({ profile }: { profile: CountryProfile }) {
  const lines = profile.regional_distinctiveness ?? [];
  if (lines.length === 0) return null;
  return (
    <Card className="p-6">
      <SectionTitle
        title={`What makes ${profile.country} distinct`}
        subtitle="Relative to its neighbours"
      />
      <div className="flex flex-wrap gap-2">
        {lines.map((l, i) => (
          <span
            key={i}
            className="rounded-lg border border-line bg-bg-soft px-3 py-1.5 text-sm text-ink-soft"
          >
            {l.text}
          </span>
        ))}
      </div>
    </Card>
  );
}

function SimilarityPanel({ iso3 }: { iso3: string }) {
  const { data } = useSimilar(iso3);
  if (!data || !data.ready) return null;
  const Row = ({ c }: { c: { iso3: string; country: string; similarity: number } }) => (
    <Link
      href={`/country/${c.iso3}`}
      className="flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-bg-hover"
    >
      <span className="flex items-center gap-2 text-sm">
        <span>{flagEmoji(c.iso3)}</span>
        {c.country}
      </span>
      <span className="text-sm tabular-nums text-ink-soft">{c.similarity}%</span>
    </Link>
  );
  return (
    <Card className="p-6">
      <SectionTitle title="Closest & most different cultures" />
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div>
          <div className="text-xs uppercase tracking-wide text-pos mb-1">Most similar</div>
          {data.most_similar.map((c) => <Row key={c.iso3} c={c} />)}
        </div>
        <div>
          <div className="text-xs uppercase tracking-wide text-neg mb-1">Most different</div>
          {data.most_different.map((c) => <Row key={c.iso3} c={c} />)}
        </div>
      </div>
    </Card>
  );
}

function CultureAtAGlance({ items }: { items: string[] }) {
  const bullets = (items ?? []).filter(Boolean);
  if (bullets.length === 0) return null;
  return (
    <Card className="p-6">
      <div className="flex items-center gap-2">
        <ListChecks className="h-4 w-4 text-accent" />
        <SectionTitle title="Culture at a glance" subtitle="The essentials, in a few lines" />
      </div>
      <ul className="mt-4 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {bullets.map((b, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-ink-soft leading-relaxed">
            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
            <span>{b}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function LifeFeelsLike({ profile }: { profile: CountryProfile }) {
  const life = profile.life_feels_like;
  if (!life || !life.text) return null;
  return (
    <Card className="p-6">
      <div className="flex items-center gap-2">
        <Heart className="h-4 w-4 text-[#e879a6]" />
        <SectionTitle
          title={`What life feels like in ${profile.country}`}
          subtitle="The daily texture of being here"
        />
      </div>
      <p className="mt-4 text-[15px] leading-relaxed text-ink-soft">{life.text}</p>
      {life.sources_count > 0 && (
        <div className="mt-4">
          <SourcesChip count={life.sources_count} />
        </div>
      )}
    </Card>
  );
}

function ExperienceVariationsSection({ items }: { items: ExperienceVariation[] }) {
  const variations = (items ?? []).filter((v) => v.group_a && v.group_b && v.difference);
  if (variations.length === 0) return null;
  return (
    <Card className="p-6">
      <div className="flex items-center gap-2">
        <Users2 className="h-4 w-4 text-accent" />
        <SectionTitle
          title="How different groups experience this country"
          subtitle="Why there is no single version of this culture"
        />
      </div>
      <div className="mt-4 space-y-3">
        {variations.map((v, i) => (
          <div key={i} className="rounded-lg border border-line bg-bg-soft p-4">
            <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">
              <span className="rounded-md bg-accent/10 px-2 py-1 text-accent">{v.group_a}</span>
              <span className="text-ink-dim">vs</span>
              <span className="rounded-md bg-[#e879a6]/10 px-2 py-1 text-[#e879a6]">
                {v.group_b}
              </span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-ink-soft">{v.difference}</p>
            {v.sources_count > 0 && (
              <div className="mt-3">
                <SourcesChip count={v.sources_count} />
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

function CountryUniquenessSection({ profile }: { profile: CountryProfile }) {
  const facets: UniquenessFacet[] = (profile.country_uniqueness ?? []).filter(
    (f) => f.title && f.explanation
  );
  if (facets.length === 0) return null;
  return (
    <div>
      <div className="flex items-center gap-2">
        <Fingerprint className="h-4 w-4 text-accent" />
        <SectionTitle
          title={`What makes ${profile.country} unique`}
          subtitle="How it stands apart from its nearest neighbours"
        />
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {facets.map((f, i) => (
          <Card key={i} className="p-5">
            <h3 className="text-sm font-semibold text-ink">{f.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-soft">{f.explanation}</p>
            {f.sources_count > 0 && (
              <div className="mt-3">
                <SourcesChip count={f.sources_count} />
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

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
    <Card className="p-6">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between"
      >
        <span className="flex items-center gap-2 font-medium">
          <ShieldCheck className="h-4 w-4 text-pos" />
          Why you should trust this
        </span>
        <ChevronDown
          className={`h-4 w-4 text-ink-dim transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <ul className="mt-4 space-y-2 animate-fade-in">
          {items.map((x, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-ink-soft">
              <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />
              {x}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function OverviewTab({ profile }: { profile: CountryProfile }) {
  return (
    <div className="space-y-6">
      {profile.executive_summary && (
        <Card className="p-6">
          <div className="flex items-start gap-3">
            <Quote className="h-5 w-5 shrink-0 text-accent" />
            <p className="text-ink-soft leading-relaxed text-[15px]">
              {profile.executive_summary}
            </p>
          </div>
          {(profile.good_for ?? profile.best_for)?.length > 0 && (
            <div className="mt-5 border-t border-line/60 pt-4">
              <GoodFor items={profile.good_for ?? profile.best_for} />
            </div>
          )}
        </Card>
      )}

      <CultureAtAGlance items={profile.culture_at_a_glance} />
      <LifeFeelsLike profile={profile} />
      <CulturalThemes profile={profile} />
      <ContradictionsSection forces={profile.competing_forces} />
      <ExperienceSection profile={profile} />
      <ObservationListSection
        title="What newcomers notice first"
        subtitle="The immediate impressions on arrival"
        icon={<Eye className="h-4 w-4 text-accent" />}
        items={profile.newcomer_first_impressions}
      />
      <SuccessFailureSection profile={profile} />
      <FriendshipMapSection map={profile.friendship_map} />
      <CommunicationDecoderSection
        signals={profile.communication_decoder}
        communication={profile.lived_experience?.communication_style ?? []}
      />
      <StatusSignalsSection items={profile.lived_experience?.status_signals ?? []} />
      <TransitionSection axes={profile.culture_in_transition} />
      <ExperienceVariationsSection items={profile.experience_variations} />
      <CountryUniquenessSection profile={profile} />
      <SimilarCulturesSection profile={profile} />
      <WhatMakesUnique profile={profile} />
      <TrustSection profile={profile} />
    </div>
  );
}
