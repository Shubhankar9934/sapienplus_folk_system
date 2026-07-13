"use client";

import { DIMENSIONS, DIM_BY_CODE, type DimCode } from "@/lib/dimensions";
import { cn } from "@/lib/utils";

export function DimensionSwitcher({
  value,
  onChange,
}: {
  value: DimCode;
  onChange: (d: DimCode) => void;
}) {
  return (
    <div className="inline-flex flex-wrap gap-1 rounded-lg border border-line bg-bg-soft p-1">
      {DIMENSIONS.map((d) => (
        <button
          key={d.code}
          onClick={() => onChange(d.code)}
          className={cn(
            "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            value === d.code
              ? "text-bg"
              : "text-ink-soft hover:text-ink"
          )}
          style={
            value === d.code
              ? { backgroundColor: d.color, color: "#0a0e14" }
              : undefined
          }
        >
          {d.label}
        </button>
      ))}
    </div>
  );
}

export function MapLegend({ dim }: { dim: DimCode }) {
  const meta = DIM_BY_CODE[dim];
  return (
    <div className="flex items-center gap-3 text-xs text-ink-soft">
      <span>{meta.low}</span>
      <div
        className="h-2 w-40 rounded-full"
        style={{
          background: `linear-gradient(to right, ${meta.lowColor}, #243244, ${meta.highColor})`,
        }}
      />
      <span>{meta.high}</span>
    </div>
  );
}
