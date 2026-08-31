import { DIM_BY_CODE, colorForScore, type DimCode } from "@/lib/dimensions";
import { ordinal } from "@/lib/utils";

/** Horizontal pole track with a score marker and optional CI band. */
export function ScorePoleBar({
  code,
  score,
  ciLow,
  ciHigh,
}: {
  code: DimCode;
  score: number | null;
  ciLow?: number | null;
  ciHigh?: number | null;
}) {
  const meta = DIM_BY_CODE[code];
  const pos = (v: number) => `${((v - 3) / 94) * 100}%`;
  return (
    <div>
      <div className="mb-1 flex justify-between text-[11px] text-ink/60 dark:text-white/50">
        <span>{meta.low}</span>
        <span>{meta.high}</span>
      </div>
      <div
        className="relative h-2.5 rounded-full"
        style={{
          background: `linear-gradient(to right, ${meta.lowColor}40, #243244, ${meta.highColor}40)`,
        }}
      >
        {ciLow != null && ciHigh != null && (
          <div
            className="absolute top-0 h-full rounded-full"
            style={{
              left: pos(ciLow),
              width: `${((ciHigh - ciLow) / 94) * 100}%`,
              backgroundColor: `${meta.color}55`,
            }}
          />
        )}
        {score != null && (
          <div
            className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-bg shadow"
            style={{ left: pos(score), backgroundColor: colorForScore(code, score) }}
          />
        )}
      </div>
    </div>
  );
}

/** Percentile placement strip ("Top 20%"). */
export function DistributionStrip({
  code,
  percentile,
  rank,
  total,
}: {
  code: DimCode;
  percentile: number;
  rank: number;
  total: number;
}) {
  const meta = DIM_BY_CODE[code];
  const topPct = Math.max(1, Math.round(100 - percentile));
  return (
    <div>
      <div className="flex items-center justify-between text-[11px] text-ink-dim mb-1">
        <span>Global distribution</span>
        <span>
          Top {topPct}% &middot; {ordinal(rank)} of {total}
        </span>
      </div>
      <div className="relative h-1.5 rounded-full bg-bg-hover">
        <div
          className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border border-bg"
          style={{ left: `${percentile}%`, backgroundColor: meta.color }}
        />
      </div>
    </div>
  );
}

export function DeltaBadge({ delta }: { delta: number }) {
  const positive = delta >= 0;
  return (
    <span
      className="text-xs font-medium tabular-nums"
      style={{ color: positive ? "#34d399" : "#f87171" }}
    >
      {positive ? "+" : ""}
      {delta} vs region
    </span>
  );
}
