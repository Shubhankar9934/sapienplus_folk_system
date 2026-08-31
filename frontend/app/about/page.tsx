"use client";

import { NavBar } from "@/components/NavBar";
import { SiteFooter } from "@/components/SiteFooter";
import { Info, Globe, ShieldCheck, Compass } from "lucide-react";

export default function AboutPage() {
  return (
    <>
      <NavBar />
      <main className="min-h-screen bg-background text-foreground dark:bg-[#0E0E10] dark:text-white px-6 py-12 md:px-16 md:py-20">
        <div className="mx-auto max-w-6xl">
          {/* Header */}
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-coral/30 bg-coral/10 px-3.5 py-1 text-xs font-semibold uppercase tracking-wider text-coral-strong dark:border-white/10 dark:bg-white/5 dark:text-white/80">
              <Info className="h-3.5 w-3.5" />
              <span>Platform Mission</span>
            </div>
            <h1 className="mt-6 font-display text-4xl tracking-tight text-ink dark:text-white md:text-6xl">
              About FOLK Cultural Intelligence
            </h1>
            <p className="mt-4 text-lg text-muted-foreground dark:text-white/70">
              FOLK is an evidence-centric cultural intelligence platform built to answer one fundamental question: <em className="text-ink dark:text-white font-medium">&ldquo;If I moved here tomorrow, what cultural realities would I experience?&rdquo;</em>
            </p>
          </div>

          {/* Pillars */}
          <div className="mt-16 grid gap-8 md:grid-cols-3">
            <div className="rounded-xl border border-border bg-card p-8 dark:border-white/10 dark:bg-[#141518]">
              <Globe className="h-8 w-8 text-coral-strong dark:text-[#E14B3C]" />
              <h3 className="mt-4 font-display text-xl text-ink dark:text-white">197 Countries & Territories</h3>
              <p className="mt-2 text-sm text-muted-foreground dark:text-white/70">
                171 base countries + 26 extension countries systematically indexed across 4 unified dimensions (Identity, Expression, Structure, Drive).
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card p-8 dark:border-white/10 dark:bg-[#141518]">
              <ShieldCheck className="h-8 w-8 text-coral-strong dark:text-[#E14B3C]" />
              <h3 className="mt-4 font-display text-xl text-ink dark:text-white">Deterministic Evidence Grounding</h3>
              <p className="mt-2 text-sm text-muted-foreground dark:text-white/70">
                Every observation is grounded in empirical citations. A deterministic filter automatically drops ungrounded statements.
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card p-8 dark:border-white/10 dark:bg-[#141518]">
              <Compass className="h-8 w-8 text-coral-strong dark:text-[#E14B3C]" />
              <h3 className="mt-4 font-display text-xl text-ink dark:text-white">Culture-First Profiles</h3>
              <p className="mt-2 text-sm text-muted-foreground dark:text-white/70">
                Replaces generic chatbot summaries with structured cultural fingerprints, reasoning-first council views, and calibrated confidence levels.
              </p>
            </div>
          </div>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
