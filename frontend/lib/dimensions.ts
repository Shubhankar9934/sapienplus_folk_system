export type DimCode = "D1" | "D2" | "D3" | "D4";

export interface DimMeta {
  code: DimCode;
  label: string;
  low: string;
  high: string;
  color: string;
  lowColor: string;
  highColor: string;
}

export const DIMENSIONS: DimMeta[] = [
  {
    code: "D1", label: "Identity", low: "Social", high: "Self",
    color: "#5b8def", lowColor: "#2f6df0", highColor: "#ef4444",
  },
  {
    code: "D2", label: "Expression", low: "Restrained", high: "Open",
    color: "#e879a6", lowColor: "#64748b", highColor: "#e879a6",
  },
  {
    code: "D3", label: "Structure", low: "Fluid", high: "Certain",
    color: "#f0b429", lowColor: "#22d3ee", highColor: "#f0b429",
  },
  {
    code: "D4", label: "Drive", low: "Accepting", high: "Striving",
    color: "#34d399", lowColor: "#94a3b8", highColor: "#34d399",
  },
];

export const DIM_BY_CODE: Record<DimCode, DimMeta> = Object.fromEntries(
  DIMENSIONS.map((d) => [d.code, d])
) as Record<DimCode, DimMeta>;

const MID_COLOR = "#243244";

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

function rgbToHex(rgb: [number, number, number]): string {
  return (
    "#" +
    rgb
      .map((c) => Math.max(0, Math.min(255, Math.round(c))).toString(16).padStart(2, "0"))
      .join("")
  );
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function mix(c1: string, c2: string, t: number): string {
  const a = hexToRgb(c1);
  const b = hexToRgb(c2);
  return rgbToHex([lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)]);
}

/** Diverging color for a score (3-97) within a dimension's poles. */
export function colorForScore(code: DimCode, score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) return "#1a2533";
  const dim = DIM_BY_CODE[code];
  const t = Math.max(0, Math.min(1, (score - 3) / 94));
  if (t < 0.5) return mix(dim.lowColor, MID_COLOR, t * 2);
  return mix(MID_COLOR, dim.highColor, (t - 0.5) * 2);
}

/** Short pole-leaning interpretation label for a score. */
export function poleLabel(code: DimCode, score: number | null | undefined): string {
  if (score === null || score === undefined) return "No data";
  const dim = DIM_BY_CODE[code];
  if (score >= 65) return `${dim.high} (high)`;
  if (score >= 55) return `Leans ${dim.high}`;
  if (score > 45) return "Balanced";
  if (score > 35) return `Leans ${dim.low}`;
  return `${dim.low} (high)`;
}

export const CONFIDENCE_COLORS: Record<string, string> = {
  HIGH: "#34d399",
  MEDIUM: "#f0b429",
  LOW: "#f87171",
};

// Five-band confidence scheme (mirrors backend confidence_label):
// Contested (<30) / Low (<50) / Moderate (<70) / High (<85) / Very High (>=85).
export const CONFIDENCE_LABELS = [
  "Contested",
  "Low",
  "Moderate",
  "High",
  "Very High",
] as const;
export type ConfidenceLabel = (typeof CONFIDENCE_LABELS)[number];

/** Map a 0-100 score onto a confidence band label. */
export function confidenceLabel(score: number | null | undefined): ConfidenceLabel {
  if (score == null) return "Contested";
  if (score >= 85) return "Very High";
  if (score >= 70) return "High";
  if (score >= 50) return "Moderate";
  if (score >= 30) return "Low";
  return "Contested";
}

const CONFIDENCE_META: Record<ConfidenceLabel, { stars: number; color: string }> = {
  "Very High": { stars: 3, color: "#34d399" },
  High: { stars: 3, color: "#34d399" },
  Moderate: { stars: 2, color: "#f0b429" },
  Low: { stars: 1, color: "#9fb0c0" },
  Contested: { stars: 1, color: "#f87171" },
};

/** Stars + color for a confidence band label. */
export function confidenceMeta(label: ConfidenceLabel): { stars: number; color: string } {
  return CONFIDENCE_META[label] ?? CONFIDENCE_META.Contested;
}

/** Evidence rating for a theme confidence. Accepts either a precomputed band
 *  label (preferred, from the backend) or a raw 0-100 score. */
export function evidenceRating(input: number | ConfidenceLabel | null | undefined): {
  label: ConfidenceLabel;
  stars: number;
  color: string;
} {
  const label: ConfidenceLabel =
    typeof input === "string" ? input : confidenceLabel(input);
  return { label, ...confidenceMeta(label) };
}
