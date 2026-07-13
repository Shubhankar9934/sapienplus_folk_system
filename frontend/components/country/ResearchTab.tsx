"use client";

import { Card, SectionTitle, Meter, Spinner, Badge } from "@/components/ui";
import { DIMENSIONS, DIM_BY_CODE, type DimCode } from "@/lib/dimensions";
import { useDimension, type CountryProfile, type CouncilView } from "@/lib/api";

function verdictColor(v: string | null) {
  if (!v) return "#9fb0c0";
  if (v.includes("Strong")) return "#34d399";
  if (v.includes("Moderate")) return "#f0b429";
  return "#f87171";
}

function CouncilReasoning({ profile }: { profile: CountryProfile }) {
  const views = profile.council_views ?? {};
  const hasAny = DIMENSIONS.some((d) => (views[d.code] ?? []).length > 0);
  if (!hasAny) return null;
  return (
    <Card className="p-6">
      <SectionTitle
        title="How the council read each dimension"
        subtitle="Each specialist's reasoning — before the score they proposed"
      />
      <div className="space-y-6">
        {DIMENSIONS.map((d) => {
          const list: CouncilView[] = views[d.code] ?? [];
          if (list.length === 0) return null;
          return (
            <div key={d.code}>
              <div className="text-sm font-medium mb-2" style={{ color: d.color }}>
                {d.label}
              </div>
              <div className="space-y-2">
                {list.map((v, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-line bg-bg-soft p-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <span className="text-sm text-ink-soft leading-relaxed">
                        <span className="font-medium text-ink">{v.specialist}:</span>{" "}
                        {v.reasoning}
                      </span>
                      <span
                        className="shrink-0 rounded-md border border-line px-2 py-1 text-xs tabular-nums text-ink"
                      >
                        {v.suggested_score}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function CouncilAgreementVisual({ profile }: { profile: CountryProfile }) {
  const a = profile.council_agreement;
  if (a.overall == null) return null;
  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <SectionTitle title="Council agreement" subtitle="Did the specialists agree?" className="mb-0" />
        <div className="text-right">
          <div className="text-2xl font-bold tabular-nums" style={{ color: verdictColor(a.verdict) }}>
            {a.overall}%
          </div>
          <div className="text-xs" style={{ color: verdictColor(a.verdict) }}>
            {a.verdict}
          </div>
        </div>
      </div>
      <div className="space-y-3">
        {DIMENSIONS.map((d) => {
          const dim = a.per_dimension[d.code];
          if (!dim) return null;
          return (
            <div key={d.code}>
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-ink-soft">{d.label}</span>
                <span className="tabular-nums text-ink-dim">{dim.agreement}% agreement</span>
              </div>
              <Meter value={dim.agreement} color={d.color} />
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function ConfidenceBreakdown({
  breakdown,
}: {
  breakdown: { coverage?: number; agreement?: number; evidence?: number; stability?: number; final?: number };
}) {
  const rows: [string, number | undefined][] = [
    ["Coverage", breakdown.coverage],
    ["Agreement", breakdown.agreement],
    ["Evidence", breakdown.evidence],
    ["Stability", breakdown.stability],
  ];
  if (rows.every(([, v]) => v == null)) return null;
  return (
    <div className="rounded-lg border border-line bg-bg-soft p-4">
      <div className="text-sm font-medium mb-3">Confidence breakdown</div>
      <div className="space-y-2.5">
        {rows.map(([label, v]) => (
          <div key={label} className="grid grid-cols-[90px_1fr_40px] items-center gap-3">
            <span className="text-xs text-ink-soft">{label}</span>
            <Meter value={v ?? 0} />
            <span className="text-xs tabular-nums text-ink-dim text-right">
              {v != null ? Math.round(v) : "—"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CouncilImpact({
  impact,
}: {
  impact: { baseline?: number | null; final?: number | null; change?: number | null; adjustment_type?: string | null; reason?: string | null };
}) {
  if (impact.baseline == null && impact.final == null) return null;
  const change = impact.change ?? 0;
  return (
    <div className="rounded-lg border border-line bg-bg-soft p-4">
      <div className="text-sm font-medium mb-3">Score formation</div>
      <div className="flex items-center gap-4">
        <div className="text-center">
          <div className="text-xs text-ink-dim">Baseline</div>
          <div className="text-xl font-semibold tabular-nums">{impact.baseline ?? "—"}</div>
        </div>
        <div className="text-ink-dim">&rarr;</div>
        <div className="text-center">
          <div className="text-xs text-ink-dim">Final</div>
          <div className="text-xl font-semibold tabular-nums">{impact.final ?? "—"}</div>
        </div>
        <div className="text-center">
          <div className="text-xs text-ink-dim">Change</div>
          <div
            className="text-xl font-semibold tabular-nums"
            style={{ color: change >= 0 ? "#34d399" : "#f87171" }}
          >
            {change > 0 ? "+" : ""}
            {change}
          </div>
        </div>
        {impact.adjustment_type && (
          <span className="ml-auto text-xs text-ink-dim border border-line rounded px-2 py-1">
            {impact.adjustment_type}
          </span>
        )}
      </div>
      {impact.reason && (
        <p className="mt-3 text-xs text-ink-soft leading-relaxed">{impact.reason}</p>
      )}
    </div>
  );
}

function DimensionMethodology({ iso3, code }: { iso3: string; code: DimCode }) {
  const { data, isLoading } = useDimension(iso3, code);
  const meta = DIM_BY_CODE[code];
  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">
          {meta.label}{" "}
          <span className="tabular-nums" style={{ color: meta.color }}>
            {data?.score ?? ""}
          </span>
        </h3>
        <span className="text-xs text-ink-dim">
          {meta.low} &harr; {meta.high}
        </span>
      </div>
      {isLoading ? (
        <Spinner />
      ) : !data ? (
        <p className="text-sm text-ink-dim mt-3">No methodology available.</p>
      ) : (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <ConfidenceBreakdown breakdown={data.confidence_breakdown} />
          <CouncilImpact impact={data.council_impact} />
        </div>
      )}
    </Card>
  );
}

function CalibrationAnchors({ profile }: { profile: CountryProfile }) {
  const anchors = profile.anchor_positions ?? [];
  if (anchors.length === 0) return null;
  return (
    <Card className="p-6">
      <SectionTitle title="Anchor calibration" subtitle="Position relative to fixed global reference points" />
      <div className="space-y-2">
        {anchors.map((a, i) => {
          const dimMeta = DIM_BY_CODE[a.dimension as keyof typeof DIM_BY_CODE];
          return (
            <div key={i} className="flex items-center gap-3 text-sm">
              <Badge color={dimMeta?.color}>{dimMeta?.label ?? a.dimension}</Badge>
              <span className="text-ink-soft">{a.reason}</span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export function ResearchTab({ profile }: { profile: CountryProfile }) {
  return (
    <div className="space-y-6">
      <CouncilReasoning profile={profile} />
      <CouncilAgreementVisual profile={profile} />
      <div className="space-y-6">
        {DIMENSIONS.map((d) => (
          <DimensionMethodology key={d.code} iso3={profile.iso3} code={d.code} />
        ))}
      </div>
      <CalibrationAnchors profile={profile} />
    </div>
  );
}
