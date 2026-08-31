import { ArrowRight } from "lucide-react";
import type { ComponentPropsWithoutRef } from "react";

type Props = ComponentPropsWithoutRef<"button"> & {
  label: string;
};

/**
 * Shared circular coral-stroke arrow CTA — reused across all sections
 * so every call-to-action reads the same way.
 */
export function ArrowCta({ label, className = "", ...rest }: Props) {
  return (
    <button
      {...rest}
      className={`group flex items-center gap-3 text-sm text-ink transition-colors dark:text-white ${className}`}
    >
      <span className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-coral-strong text-coral-strong transition-transform group-hover:translate-x-0.5">
        <ArrowRight className="h-4 w-4" />
      </span>
      {label}
    </button>
  );
}
