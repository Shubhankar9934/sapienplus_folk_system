"use client";

import Link from "next/link";
import { ShieldCheck } from "lucide-react";

export function SiteFooter() {
  return (
    <footer className="w-full border-t border-border dark:border-white/10">
      {/* ── BOTTOM FOOTER BAND ─────────────────────────────────────── */}
      <section className="bg-coral-strong px-6 py-12 text-ink noise-light dark:bg-[#0a0b0d] dark:text-white dark:noise-dark md:px-16 md:py-16">
        <div className="relative z-10 mx-auto max-w-7xl grid gap-10 md:grid-cols-4">
          
          {/* Logo & Platform Info */}
          <div>
            <div className="font-display text-2xl leading-[1.05] tracking-wide md:text-3xl">
              FOLK<br />CULTURAL<br />INTELLIGENCE
            </div>
            <p className="mt-4 text-xs text-ink/80 dark:text-white/60 leading-relaxed max-w-xs">
              Evidence-centric cultural scoring platform covering 197 countries across 4 unified dimensions.
            </p>
          </div>

          {/* Quick Links Column 1 */}
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-ink/70 dark:text-[#E14B3C] mb-3">
              Platform Index
            </p>
            <ul className="space-y-2.5 text-sm">
              <li><Link href="/" className="hover:underline dark:hover:text-[#E14B3C]">Home</Link></li>
              <li><Link href="/orientations" className="hover:underline dark:hover:text-[#E14B3C]">FOLK Orientation</Link></li>
              <li><Link href="/countries" className="hover:underline dark:hover:text-[#E14B3C]">Country Profiles (197)</Link></li>
              <li><Link href="/world-rankings" className="hover:underline dark:hover:text-[#E14B3C]">World Rankings</Link></li>
              <li><Link href="/compare" className="hover:underline dark:hover:text-[#E14B3C]">Compare Countries</Link></li>
            </ul>
          </div>

          {/* Quick Links Column 2 */}
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-ink/70 dark:text-[#E14B3C] mb-3">
              Research & Team
            </p>
            <ul className="space-y-2.5 text-sm">
              <li><Link href="/methodology" className="hover:underline dark:hover:text-[#E14B3C]">Methodology Note</Link></li>
              <li><Link href="/methodology" className="hover:underline dark:hover:text-[#E14B3C]">Factor Structure Matrix</Link></li>
              <li><Link href="/insights" className="hover:underline dark:hover:text-[#E14B3C]">Analytical Insights (2050)</Link></li>
              <li><Link href="/team" className="hover:underline dark:hover:text-[#E14B3C]">Research Council Team</Link></li>
              <li><Link href="/about" className="hover:underline dark:hover:text-[#E14B3C]">About Platform</Link></li>
            </ul>
          </div>

          {/* Verification & System Standards */}
          <div className="space-y-4 text-xs">
            <p className="font-bold uppercase tracking-widest text-ink/70 dark:text-[#E14B3C]">
              Verification Standards
            </p>

            <div className="rounded-lg border border-ink/10 bg-white/10 p-3 dark:border-white/10 dark:bg-white/[0.03]">
              <div className="flex items-center gap-2 font-semibold text-ink dark:text-white">
                <ShieldCheck className="h-4 w-4 text-coral-strong dark:text-[#E14B3C]" />
                <span>Deterministic Grounding</span>
              </div>
              <p className="mt-1 text-ink/70 dark:text-white/60">
                100% claim-ID verification filter drops ungrounded statements.
              </p>
            </div>

            <p className="text-[11px] text-ink/70 dark:text-white/50 leading-relaxed">
              Scores calibrated against global reference points. Reviewed by an adaptive multi-LLM research council.
            </p>
          </div>

        </div>
      </section>
    </footer>
  );
}


