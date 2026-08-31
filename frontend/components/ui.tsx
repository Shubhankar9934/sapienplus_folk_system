import * as React from "react";
import { cn } from "@/lib/utils";
import { CONFIDENCE_COLORS } from "@/lib/dimensions";

export function Card({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-xl border border-ink/10 bg-white dark:border-white/10 dark:bg-[#1a1d21]",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function SectionTitle({
  title,
  subtitle,
  className,
}: {
  title: string;
  subtitle?: string;
  className?: string;
}) {
  return (
    <div className={cn("mb-6", className)}>
      <h2 className="font-display text-2xl uppercase tracking-tight text-ink dark:text-white">{title}</h2>
      {subtitle && <p className="mt-1 text-sm text-ink/60 dark:text-white/50">{subtitle}</p>}
    </div>
  );
}

export function Badge({
  children,
  className,
  color,
}: {
  children: React.ReactNode;
  className?: string;
  color?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        className,
      )}
      style={
        color
          ? { borderColor: `${color}55`, color, backgroundColor: `${color}14` }
          : undefined
      }
    >
      {children}
    </span>
  );
}

export function ConfidenceBadge({ level }: { level: string | null }) {
  if (!level) return null;
  const color = CONFIDENCE_COLORS[level.toUpperCase()] ?? "#9fb0c0";
  return (
    <Badge color={color}>
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: color }}
      />
      {level} confidence
    </Badge>
  );
}

export function GradeBadge({ grade }: { grade: string | null }) {
  if (!grade) return null;
  const color =
    grade === "A"
      ? "#34d399"
      : grade === "B"
        ? "#f0b429"
        : grade === "C"
          ? "#fb923c"
          : "#f87171";
  return <Badge color={color}>Research grade {grade}</Badge>;
}

export function Meter({
  value,
  max = 100,
  color = "#5b8def",
  className,
}: {
  value: number | null | undefined;
  max?: number;
  color?: string;
  className?: string;
}) {
  const pct =
    value == null ? 0 : Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div
      className={cn(
        "h-2 w-full rounded-full bg-bg-hover overflow-hidden",
        className,
      )}
    >
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  );
}

export function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-ink-dim">
        {label}
      </div>
      <div className="text-2xl font-semibold text-ink mt-0.5">{value}</div>
      {hint && <div className="text-xs text-ink-soft mt-0.5">{hint}</div>}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-ink-soft">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-line border-t-accent" />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}

export function EmptyState({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <Card className="p-8 text-center">
      <p className="font-medium text-ink dark:text-white">{title}</p>
      <p className="mt-1 text-sm text-ink/60 dark:text-white/50">{message}</p>
    </Card>
  );
}
