"use client";

import { useRef, useState } from "react";
import { toPng } from "html-to-image";
import { Download } from "lucide-react";
import { DIMENSIONS, type DimCode } from "@/lib/dimensions";
import { flagEmoji } from "@/lib/utils";
import type { CountryProfile } from "@/lib/api";

export function CulturalDnaCard({ profile }: { profile: CountryProfile }) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState(false);

  async function download() {
    if (!cardRef.current) return;
    setBusy(true);
    try {
      const url = await toPng(cardRef.current, { pixelRatio: 2, cacheBust: true });
      const a = document.createElement("a");
      a.href = url;
      a.download = `folk-${profile.iso3}-cultural-dna.png`;
      a.click();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div
        ref={cardRef}
        className="rounded-2xl p-6 w-full"
        style={{
          background: "linear-gradient(150deg, #0f1620 0%, #121b27 60%, #16202c 100%)",
          border: "1px solid #1e2b3a",
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{flagEmoji(profile.iso3)}</span>
            <div>
              <div className="font-semibold text-ink">{profile.country}</div>
              <div className="text-xs text-ink-dim">{profile.region}</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-widest text-accent">FOLK</div>
            <div className="text-[10px] text-ink-dim">Cultural DNA</div>
          </div>
        </div>

        <div className="mt-5 space-y-3">
          {DIMENSIONS.map((d) => {
            const score = profile.scores[d.code as DimCode]?.score ?? 0;
            const filled = Math.round((score / 100) * 10);
            return (
              <div key={d.code} className="flex items-center gap-3">
                <div className="w-20 text-xs text-ink-soft">{d.label}</div>
                <div className="font-mono text-sm tracking-tight" style={{ color: d.color }}>
                  {"█".repeat(filled)}
                  <span className="text-ink-dim">{"░".repeat(10 - filled)}</span>
                </div>
                <div className="ml-auto text-sm font-semibold tabular-nums">{score}</div>
              </div>
            );
          })}
        </div>

        {profile.archetype && (
          <div className="mt-5 text-center text-xs text-ink-soft">
            {profile.archetype}
          </div>
        )}
      </div>

      <button
        onClick={download}
        disabled={busy}
        className="flex w-full items-center justify-center gap-2 rounded-lg border border-line py-2 text-sm text-ink-soft hover:bg-bg-hover disabled:opacity-50"
      >
        <Download className="h-4 w-4" />
        {busy ? "Rendering..." : "Download shareable card"}
      </button>
    </div>
  );
}
