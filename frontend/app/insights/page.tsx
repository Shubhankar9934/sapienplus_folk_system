"use client";

import { NavBar } from "@/components/NavBar";
import { SiteFooter } from "@/components/SiteFooter";
import { Lightbulb, TrendingUp, ShieldCheck, Compass, Calendar, ArrowRight, Zap, Globe, Sparkles, AlertTriangle, Layers, BookOpen } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

const FOLK_NOTES = [
  {
    id: "note-1",
    noteNum: "FOLK Note 1",
    title: "Who Else Is in the Room?",
    subtitle: "Note on Identity (Social ↔ Self)",
    mean: "39",
    median: "33",
    range: "18 to 88",
    keyInsight: "The family is the oldest insurance company in the world. Where states stay weak, clan networks provide survival. Where welfare states insure the person (e.g. Scandinavia), state individualism flourishes.",
    lowAnchors: "Afghanistan (24), Burkina Faso (23), South Sudan (28)",
    highAnchors: "Sweden (87), Denmark (84), Norway (81)",
    color: "#5b8def",
  },
  {
    id: "note-2",
    noteNum: "FOLK Note 2",
    title: "What May Be Shown?",
    subtitle: "Note on Expression (Restrained ↔ Open)",
    mean: "48",
    median: "48",
    range: "21 to 81",
    keyInsight: "Where people live in dense interdependence, unguarded outbursts are costly (face culture). In high-contact cultures, warmth is the ordinary currency of public life.",
    lowAnchors: "China (21), Czech Republic (22), Japan (28)",
    highAnchors: "Argentina (81), Venezuela (80), USA (71)",
    color: "#e879a6",
  },
  {
    id: "note-3",
    noteNum: "FOLK Note 3",
    title: "Paper or Person?",
    subtitle: "Note on Structure (Fluid ↔ Certain)",
    mean: "55",
    median: "56",
    range: "29 to 83",
    keyInsight: "This is the only axis on which the world tilts above the middle. Centuries of administrative apparatus or recurring natural shocks build protocol into a survival technology.",
    lowAnchors: "Jamaica (29), USA (33), Ghana (35)",
    highAnchors: "Germany (83), Russia (82), France (80)",
    color: "#f0b429",
  },
  {
    id: "note-4",
    noteNum: "FOLK Note 4",
    title: "Ladder or Hammock?",
    subtitle: "Note on Drive (Accepting ↔ Striving)",
    mean: "47",
    median: "46",
    range: "22 to 82",
    keyInsight: "Confucian exam traditions & Protestant work ethics built massive achievement engines. Fiercest striving occurs where a generation remembering poverty sees a real way up.",
    lowAnchors: "Norway (22), Sweden (25), Netherlands (30)",
    highAnchors: "Japan (82), China (80), USA (71), India (71)",
    color: "#34d399",
  },
];

const FUTURE_PROJECTIONS = [
  {
    dimension: "Identity (D1)",
    title: "The Shift Toward Self",
    horizon: "2025–2050",
    projection: "Urbanization, state/market safety nets, and female labor participation push young cohorts toward Self. World median (33) will rise 10–20 points in transition economies (India, Indonesia, Nigeria).",
    marketingImpact: "First-generation solo consumption at scale: personal vehicles, solo apartments, individual subscriptions. Dual-voice campaigns combining family pride with personal identity.",
  },
  {
    dimension: "Expression (D2)",
    title: "Screen-Mediated Openness",
    horizon: "2025–2050",
    projection: "Social media acts as a global expression trainer. Mediated disclosure (emojis, avatars, voice notes) allows open expression without personal exposure, creating two-register consumers.",
    marketingImpact: "User-generated emotion becomes the creative engine. Loud shareable online moments paired with quiet, low-pressure service in person.",
  },
  {
    dimension: "Structure (D3)",
    title: "The Platform as the New Middle",
    horizon: "2025–2050",
    projection: "Strong-state societies deepen certainty via software rules. Weak-state societies leapfrog broken institutions via digital platforms (mobile money, escrow, platform ratings).",
    marketingImpact: "In Certain markets, provenance & audit trails become table stakes. In Fluid markets, platform escrow & delivery ratings own the customer before brands do.",
  },
  {
    dimension: "Drive (D4)",
    title: "Migration of the Striving Engine",
    horizon: "2025–2050",
    projection: "East Asia's striving generation is aging ('lying flat' in China/Japan). The striving engine moves to South Asia, Southeast Asia, and Africa (India, Vietnam, Nigeria, Kenya).",
    marketingImpact: "Education & status upgrades shift to South Asia/Africa. East Asia shifts to quiet luxury, post-material balance, and wellness.",
  },
];

export default function InsightsPage() {
  const [selectedNote, setSelectedNote] = useState<string>("note-1");

  return (
    <>
      <NavBar />
      <main className="min-h-screen bg-background text-foreground dark:bg-[#0E0E10] dark:text-white px-6 py-12 md:px-16 md:py-20">
        <div className="mx-auto max-w-6xl">
          
          {/* Header */}
          <div className="max-w-4xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-coral/30 bg-coral/10 px-3.5 py-1 text-xs font-semibold uppercase tracking-wider text-coral-strong dark:border-white/10 dark:bg-white/5 dark:text-white/80">
              <Lightbulb className="h-3.5 w-3.5" />
              <span>FOLK Research Notes & Insights</span>
            </div>
            <h1 className="mt-6 font-display text-4xl tracking-tight text-ink dark:text-white md:text-6xl">
              Cultural Intelligence Insights
            </h1>
            <p className="mt-4 text-xl font-medium text-ink/90 dark:text-white/90">
              Five FOLK Notes: Drivers, Scores, and 2050 Directional Projections
            </p>
            <p className="mt-2 text-base text-muted-foreground dark:text-white/70">
              Analysis across 197 countries drawn from FOLK Notes 1 through 5.
            </p>
          </div>

          {/* FOLK Notes Grid (Notes 1–4) */}
          <div className="mt-16 grid gap-8 md:grid-cols-2">
            {FOLK_NOTES.map((note) => (
              <div
                key={note.id}
                className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-border bg-card p-8 shadow-sm transition hover:shadow-md dark:border-white/10 dark:bg-[#141518]"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span
                      className="rounded-md px-3 py-1 text-xs font-bold text-white uppercase tracking-wider"
                      style={{ backgroundColor: note.color }}
                    >
                      {note.noteNum}
                    </span>
                    <span className="text-xs text-muted-foreground dark:text-white/60">
                      Mean: <strong className="text-ink dark:text-white">{note.mean}</strong> | Range: {note.range}
                    </span>
                  </div>

                  <h3 className="mt-4 font-display text-2xl text-ink dark:text-white">{note.title}</h3>
                  <p className="text-xs font-semibold uppercase tracking-wider text-coral-strong dark:text-[#E14B3C] mt-1">
                    {note.subtitle}
                  </p>

                  <p className="mt-4 text-sm text-muted-foreground dark:text-white/80 leading-relaxed">
                    {note.keyInsight}
                  </p>
                </div>

                <div className="mt-8 pt-4 border-t border-border dark:border-white/10 space-y-2 text-xs">
                  <div>
                    <span className="font-semibold text-ink/70 dark:text-white/60 uppercase text-[10px] block">Low Pole Countries:</span>
                    <span className="text-muted-foreground dark:text-white/75">{note.lowAnchors}</span>
                  </div>
                  <div>
                    <span className="font-semibold text-ink/70 dark:text-white/60 uppercase text-[10px] block">High Pole Countries:</span>
                    <span className="text-muted-foreground dark:text-white/75">{note.highAnchors}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* FOLK Note 5 — Where Is This Going? (The Next 25 Years) */}
          <section className="mt-16 rounded-2xl border border-border bg-card p-8 dark:border-white/10 dark:bg-[#141518] md:p-12">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-coral-strong/10 text-coral-strong dark:bg-white/10 dark:text-white">
                <Calendar className="h-5 w-5" />
              </div>
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-coral-strong dark:text-[#E14B3C]">FOLK Note 5</span>
                <h2 className="font-display text-2xl md:text-3xl text-ink dark:text-white">
                  Where Is This Going? (2025–2050 Projections)
                </h2>
              </div>
            </div>

            <p className="mt-6 text-sm md:text-base text-muted-foreground dark:text-white/80 leading-relaxed">
              Cultures move slowly, but they do move. Scores are equilibria held in place by institutions, economics, and habit. When those shift, scores follow approximately a generation behind. Here is how the four axes are projected to move by 2050:
            </p>

            {/* Projections Breakdown */}
            <div className="mt-8 grid gap-6 md:grid-cols-2">
              {FUTURE_PROJECTIONS.map((fp, i) => (
                <div key={i} className="rounded-xl border border-border p-6 bg-background dark:border-white/10 dark:bg-[#0E0E10]">
                  <div className="flex items-center justify-between text-xs font-bold text-coral-strong dark:text-[#E14B3C]">
                    <span>{fp.dimension}</span>
                    <span>{fp.horizon}</span>
                  </div>
                  <h3 className="mt-2 font-display text-xl text-ink dark:text-white">{fp.title}</h3>
                  <p className="mt-3 text-xs md:text-sm text-muted-foreground dark:text-white/80 leading-relaxed">
                    {fp.projection}
                  </p>
                  <div className="mt-4 pt-3 border-t border-border dark:border-white/10 text-xs">
                    <strong className="block text-ink dark:text-white mb-1">Commercial & Organizational Impact:</strong>
                    <span className="text-muted-foreground dark:text-white/75">{fp.marketingImpact}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Wildcards / Benders */}
            <div className="mt-8 rounded-xl border border-coral/30 bg-coral/5 p-6 dark:border-white/10 dark:bg-white/[0.02]">
              <h4 className="font-display text-lg text-ink dark:text-white flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-coral-strong dark:text-[#E14B3C]" />
                Wildcards That Could Bend These Lines
              </h4>
              <ul className="mt-3 space-y-2 text-xs md:text-sm text-muted-foreground dark:text-white/80">
                <li>• <strong>AI & Work:</strong> Machine intelligence deflating credential values vs. concentrating rewards.</li>
                <li>• <strong>Climate Shocks:</strong> Pushing affected societies toward Social (mutual aid) and Certain (protocol).</li>
                <li>• <strong>Political Turbulence:</strong> Rapid re-tribalization of identity when security collapses.</li>
              </ul>
            </div>
          </section>

          {/* Bottom Callout */}
          <div className="mt-12 rounded-2xl bg-ink p-8 text-white dark:bg-[#141518] dark:border dark:border-white/10 md:p-10 flex flex-col md:flex-row items-center justify-between gap-6">
            <div>
              <span className="text-xs font-semibold uppercase tracking-widest text-coral-strong dark:text-[#E14B3C]">
                EXPLORE THE DATA
              </span>
              <h3 className="mt-2 font-display text-2xl md:text-3xl text-white">
                Compare Country Scores Across All 4 Orientations
              </h3>
              <p className="mt-2 text-sm text-white/80 max-w-3xl">
                See where any country sits on Identity, Expression, Structure, and Drive calibrated against global baselines.
              </p>
            </div>
            <Link
              href="/countries"
              className="shrink-0 inline-flex items-center gap-2 rounded-lg bg-coral-strong px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90 dark:bg-white dark:text-ink"
            >
              <span>Explore Countries</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

        </div>
      </main>
      <SiteFooter />
    </>
  );
}
