import Link from "next/link";
import { DIMENSIONS } from "@/lib/dimensions";
import { colorForScore } from "@/lib/dimensions";
import { flagEmoji } from "@/lib/utils";
import { Card } from "./ui";
import type { CountryListItem } from "@/lib/api";

export function CountryCard({ c }: { c: CountryListItem }) {
  return (
    <Link href={`/country/${c.iso3}`}>
      <Card className="p-4 hover:border-accent/50 hover:bg-bg-hover transition-colors h-full">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-xl">{flagEmoji(c.iso3)}</span>
            <div className="min-w-0">
              <div className="font-medium truncate">{c.country}</div>
              <div className="text-xs text-ink-dim">{c.region ?? "—"}</div>
            </div>
          </div>
          {c.research_grade && (
            <span className="text-xs text-ink-dim border border-line rounded px-1.5 py-0.5">
              {c.research_grade}
            </span>
          )}
        </div>

        <div className="mt-3 grid grid-cols-4 gap-1.5">
          {DIMENSIONS.map((d) => {
            const s = c.scores[d.code];
            return (
              <div key={d.code} className="text-center">
                <div
                  className="h-1 rounded-full mb-1"
                  style={{ backgroundColor: colorForScore(d.code, s) }}
                />
                <div className="text-sm font-semibold tabular-nums">
                  {s ?? "—"}
                </div>
                <div className="text-[10px] text-ink-dim">{d.code}</div>
              </div>
            );
          })}
        </div>

        {c.archetype && (
          <div className="mt-3 text-xs text-ink-soft truncate">{c.archetype}</div>
        )}
      </Card>
    </Link>
  );
}
