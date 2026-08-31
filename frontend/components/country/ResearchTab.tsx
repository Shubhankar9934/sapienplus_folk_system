"use client";

import { Spinner } from "@/components/ui";
import { DIMENSIONS, DIM_BY_CODE, type DimCode } from "@/lib/dimensions";
import { useDimension, type CountryProfile, type CouncilView } from "@/lib/api";

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

function CouncilReasoning({ profile }: { profile: CountryProfile }) {
  const views = profile.council_views ?? {};
  const hasAny = DIMENSIONS.some((d) => (views[d.code] ?? []).length > 0);
  if (!hasAny) return null;
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <EditorialHeading>How the council read each dimension</EditorialHeading>
        <span className="text-[11px] text-ink/40 dark:text-white/30 hidden sm:block">
          Each specialist&apos;s reasoning
        </span>
      </div>
      <Hairline />
      <div className="mt-0 space-y-8 divide-y divide-ink/8 dark:divide-white/8">
        {DIMENSIONS.map((d) => {
          const list: CouncilView[] = views[d.code] ?? [];
          if (list.length === 0) return null;
          return (
            <div key={d.code} className="pt-6 first:pt-4">
              <p className="mb-4 text-[9px] font-bold uppercase tracking-[0.24em] text-ink/40 dark:text-white/30">
                {d.code} · {d.label}
              </p>
              <div className="space-y-4">
                {list.map((v, i) => (
                  <div key={i} className="flex items-start justify-between gap-6">
                    <p className="text-[13px] leading-relaxed text-ink/70 dark:text-white/60">
                      <span className="font-semibold text-ink dark:text-white">
                        {v.specialist}:
                      </span>{" "}
                      {v.reasoning}
                    </p>
                    <span className="shrink-0 border border-ink/18 dark:border-white/15 px-2.5 py-1 text-[12px] tabular-nums font-semibold text-ink dark:text-white rounded-sm">
                      {v.suggested_score}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function CouncilAgreementVisual({ profile }: { profile: CountryProfile }) {
  const a = profile.council_agreement;
  if (a.overall == null) return null;
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <EditorialHeading>Council agreement</EditorialHeading>
        <span className="font-display text-[2rem] tabular-nums leading-none text-coral-strong dark:text-[#E14B3C]">
          {a.overall}%
        </span>
      </div>
      {a.verdict && (
        <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">{a.verdict}</p>
      )}
      <Hairline />
      <div className="mt-0 divide-y divide-ink/8 dark:divide-white/8">
        {DIMENSIONS.map((d) => {
          const dim = a.per_dimension[d.code];
          if (!dim) return null;
          return (
            <div key={d.code} className="py-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-[9px] font-bold uppercase tracking-[0.18em] text-ink/40 dark:text-white/30">
                  {d.code} · {d.label}
                </span>
                <span className="text-[12px] tabular-nums font-semibold text-ink dark:text-white">
                  {dim.agreement}%
                </span>
              </div>
              <ScoreBar value={dim.agreement} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ConfidenceBreakdown({
  breakdown,
}: {
  breakdown: {
    coverage?: number;
    agreement?: number;
    evidence?: number;
    stability?: number;
  };
}) {
  const rows: [string, number | undefined][] = [
    ["Coverage", breakdown.coverage],
    ["Agreement", breakdown.agreement],
    ["Evidence", breakdown.evidence],
    ["Stability", breakdown.stability],
  ];
  if (rows.every(([, v]) => v == null)) return null;
  return (
    <div>
      <p className="mb-3 text-[9px] font-bold uppercase tracking-[0.2em] text-ink/35 dark:text-white/30">
        Confidence breakdown
      </p>
      <div className="space-y-3">
        {rows.map(([label, v]) => (
          <div key={label}>
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-[0.12em] text-ink/40 dark:text-white/30">
                {label}
              </span>
              <span className="text-[11px] tabular-nums text-ink/55 dark:text-white/45">
                {v != null ? Math.round(v) : "—"}
              </span>
            </div>
            <ScoreBar value={v ?? 0} />
          </div>
        ))}
      </div>
    </div>
  );
}

function CouncilImpact({
  impact,
}: {
  impact: {
    baseline?: number | null;
    final?: number | null;
    change?: number | null;
    adjustment_type?: string | null;
    reason?: string | null;
  };
}) {
  if (impact.baseline == null && impact.final == null) return null;
  const change = impact.change ?? 0;
  return (
    <div>
      <p className="mb-3 text-[9px] font-bold uppercase tracking-[0.2em] text-ink/35 dark:text-white/30">
        Score formation
      </p>
      <div className="flex items-end gap-6">
        <div>
          <p className="text-[9px] uppercase tracking-[0.14em] text-ink/30 dark:text-white/25">
            Baseline
          </p>
          <p className="font-display text-2xl tabular-nums text-ink dark:text-white">
            {impact.baseline ?? "—"}
          </p>
        </div>
        <span className="mb-1 text-[11px] text-ink/25 dark:text-white/20">→</span>
        <div>
          <p className="text-[9px] uppercase tracking-[0.14em] text-ink/30 dark:text-white/25">
            Final
          </p>
          <p className="font-display text-2xl tabular-nums text-ink dark:text-white">
            {impact.final ?? "—"}
          </p>
        </div>
        <div>
          <p className="text-[9px] uppercase tracking-[0.14em] text-ink/30 dark:text-white/25">
            Change
          </p>
          <p
            className="font-display text-2xl tabular-nums"
            style={{
              color: change >= 0 ? "#34d399" : "#f87171",
            }}
          >
            {change > 0 ? "+" : ""}
            {change}
          </p>
        </div>
      </div>
      {impact.reason && (
        <p className="mt-3 text-[12px] leading-relaxed text-ink/55 dark:text-white/45">
          {impact.reason}
        </p>
      )}
    </div>
  );
}

function DimensionMethodology({ iso3, code }: { iso3: string; code: DimCode }) {
  const { data, isLoading } = useDimension(iso3, code);
  const meta = DIM_BY_CODE[code];
  return (
    <div className="py-6 border-b border-ink/8 dark:border-white/8">
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <p className="text-[9px] font-bold uppercase tracking-[0.22em] text-ink/35 dark:text-white/30">
            {meta.code}
          </p>
          <h3 className="font-display text-xl uppercase text-ink dark:text-white">
            {meta.label}
          </h3>
        </div>
        {data?.score != null && (
          <span className="font-display text-[2rem] tabular-nums leading-none text-coral-strong dark:text-[#E14B3C]">
            {data.score}
          </span>
        )}
      </div>
      <p className="mb-4 text-[10px] uppercase tracking-[0.14em] text-ink/35 dark:text-white/30">
        {meta.low} ↔ {meta.high}
      </p>
      {isLoading ? (
        <Spinner />
      ) : !data ? (
        <p className="text-[13px] text-ink/40 dark:text-white/30">
          No methodology available.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-2">
          <ConfidenceBreakdown breakdown={data.confidence_breakdown} />
          <CouncilImpact impact={data.council_impact} />
        </div>
      )}
    </div>
  );
}

function CalibrationAnchors({ profile }: { profile: CountryProfile }) {
  const anchors = profile.anchor_positions ?? [];
  if (anchors.length === 0) return null;
  return (
    <div>
      <EditorialHeading>Anchor calibration</EditorialHeading>
      <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">
        Position relative to fixed global reference points
      </p>
      <Hairline />
      <div className="mt-0 divide-y divide-ink/8 dark:divide-white/8">
        {anchors.map((a, i) => {
          const dimMeta =
            DIM_BY_CODE[a.dimension as keyof typeof DIM_BY_CODE];
          return (
            <div key={i} className="flex items-start gap-4 py-4">
              <span className="shrink-0 text-[9px] font-bold uppercase tracking-[0.18em] text-ink/40 dark:text-white/30 pt-0.5 w-14">
                {dimMeta?.label ?? a.dimension}
              </span>
              <p className="text-[13px] leading-relaxed text-ink/65 dark:text-white/55">
                {a.reason}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function ResearchTab({ profile }: { profile: CountryProfile }) {
  return (
    <div className="space-y-14">
      <CouncilReasoning profile={profile} />
      <CouncilAgreementVisual profile={profile} />
      <div>
        <EditorialHeading>Dimension methodology</EditorialHeading>
        <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">
          How each score was formed
        </p>
        <Hairline />
        <div>
          {DIMENSIONS.map((d) => (
            <DimensionMethodology key={d.code} iso3={profile.iso3} code={d.code} />
          ))}
        </div>
      </div>
      <CalibrationAnchors profile={profile} />
    </div>
  );
}
