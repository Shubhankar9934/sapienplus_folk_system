"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import { DIMENSIONS, type DimCode } from "@/lib/dimensions";

export interface RadarSeries {
  name: string;
  color: string;
  scores: Partial<Record<DimCode, number | null>>;
}

export function FolkRadar({
  series,
  ci,
  height = 340,
  showLegend = false,
}: {
  series: RadarSeries[];
  ci?: { low: Partial<Record<DimCode, number>>; high: Partial<Record<DimCode, number>> };
  height?: number;
  showLegend?: boolean;
}) {
  const data = DIMENSIONS.map((d) => {
    const row: Record<string, number | string | null> = { dimension: d.label };
    series.forEach((s) => {
      row[s.name] = s.scores[d.code] ?? null;
    });
    if (ci) {
      row["ci_low"] = ci.low[d.code] ?? null;
      row["ci_high"] = ci.high[d.code] ?? null;
    }
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data} outerRadius="72%">
        <PolarGrid stroke="#1e2b3a" />
        <PolarAngleAxis
          dataKey="dimension"
          tick={{ fill: "#9fb0c0", fontSize: 12 }}
        />
        <PolarRadiusAxis
          domain={[0, 100]}
          tick={{ fill: "#6b7d8f", fontSize: 10 }}
          stroke="#1e2b3a"
          angle={90}
        />
        {ci && (
          <Radar
            name="Confidence range"
            dataKey="ci_high"
            stroke="transparent"
            fill="#5b8def"
            fillOpacity={0.08}
            isAnimationActive={false}
          />
        )}
        {series.map((s) => (
          <Radar
            key={s.name}
            name={s.name}
            dataKey={s.name}
            stroke={s.color}
            fill={s.color}
            fillOpacity={0.18}
            strokeWidth={2}
            dot
          />
        ))}
        <Tooltip
          contentStyle={{
            background: "#121b27",
            border: "1px solid #1e2b3a",
            borderRadius: 8,
            color: "#e6edf3",
          }}
        />
        {showLegend && <Legend wrapperStyle={{ fontSize: 12, color: "#9fb0c0" }} />}
      </RadarChart>
    </ResponsiveContainer>
  );
}
