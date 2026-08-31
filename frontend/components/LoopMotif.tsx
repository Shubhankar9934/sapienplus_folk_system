/**
 * Faint intertwined-loop motif — echoes the hero linework.
 * Rendered as white outlines at 8% opacity for dark section continuity.
 */
export function LoopMotif({ className = "" }: { className?: string }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 600 600"
      className={`pointer-events-none absolute ${className}`}
      style={{ opacity: 0.08 }}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.2"
    >
      <ellipse cx="240" cy="300" rx="180" ry="180" />
      <ellipse cx="360" cy="300" rx="180" ry="180" />
      <ellipse cx="300" cy="240" rx="180" ry="180" />
      <ellipse cx="300" cy="360" rx="180" ry="180" />
      <circle cx="300" cy="300" r="80" />
    </svg>
  );
}
