"use client";

import { NavBar } from "@/components/NavBar";
import { SiteFooter } from "@/components/SiteFooter";
import { DIMENSIONS } from "@/lib/dimensions";
import { Compass, Users, Sparkles, Shield, Flame, Table, AlertTriangle, Layers, CheckCircle2, ArrowRight, BookOpen } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

const COMPARISON_TABLE = [
  {
    framework: "Hofstede",
    strength: "Most widely cited; robust country scores across 70+ nations.",
    limitation: "Core data from the late 1960s and 70s; the masculine–feminine labelling has aged badly.",
    mapping: "All six dimensions absorbed. Individualism & Power Distance → Identity; Uncertainty Avoidance → Structure; Indulgence → Expression; Masculinity → Drive.",
  },
  {
    framework: "GLOBE",
    strength: "Rigorous multi-country study; separates what cultures value from what they practise.",
    limitation: "Nine overlapping dimensions; hard to apply in the field.",
    mapping: "Spread across all four. Notably, GLOBE Uncertainty Avoidance maps to Identity rather than Structure — a key empirical distinction.",
  },
  {
    framework: "Schwartz",
    strength: "Theoretically elegant; grounded in universal human values.",
    limitation: "Limited everyday uptake; needs translation into plain terms.",
    mapping: "Anchors Identity through Autonomy and Embeddedness, and Structure through Harmony.",
  },
  {
    framework: "World Values Survey",
    strength: "Largest global dataset; tracks cultural change over decades.",
    limitation: "Not built as a practical tool; can feel abstract without context.",
    mapping: "The richest single source for Identity — Choice, Equality, Voice, Autonomy.",
  },
  {
    framework: "Trompenaars",
    strength: "Accessible and intuitive; widely used in coaching and training.",
    limitation: "Smaller sample base; less independent academic validation.",
    mapping: "All four dimensions load cleanly onto Identity, confirming their individualism–collectivism core.",
  },
];

const ORIENTATION_NOTES = [
  {
    code: "D1",
    title: "Who Else Is in the Room?",
    subtitle: "Note on Identity (Social ↔ Self)",
    stats: "Scores: 18 to 88 | World Mean: 39 | Median: 33",
    body: "Identity runs from Social to Self. At the Social end, a person's sense of who they are sits inside the family, the kin group, and the community. At the Self end, the individual is the unit, and the group is something you join. Most of humanity lives on the Social side. The strongly Self countries are a small cluster, mostly wealthy and mostly Western.",
    lowAnchors: "Family & tribe primacy, collective accountability, shared identity",
    highAnchors: "Personal choice, individual agency, voluntary group association",
  },
  {
    code: "D2",
    title: "What May Be Shown?",
    subtitle: "Note on Expression (Restrained ↔ Open)",
    stats: "Scores: 21 to 81 | World Mean: 48 (Even distribution)",
    body: "Expression runs from Restrained to Open, measuring how freely warmth, emotion, and social energy are displayed. China (21), Czech Republic (22), and Japan (28) hold the Restrained end. Argentina (81), Colombia (77), and the USA (71) hold the Open end. The same feelings exist everywhere; what differs is the rule about where they may be spent.",
    lowAnchors: "Formal containment, contextual warmth, emotional restraint",
    highAnchors: "Everyday emotional visibility, open social warmth, direct disclosure",
  },
  {
    code: "D3",
    title: "Paper or Person?",
    subtitle: "Note on Structure (Fluid ↔ Certain)",
    stats: "Scores: 29 to 83 | World Mean: 55 (World tilts Certain)",
    body: "Structure runs from Fluid to Certain, measuring how strongly rules, order, and predictability are preferred over flexibility and improvisation. Germany (83) and Russia (82) sit at the Certain end, while Jamaica (29) and USA (33) sit at the Fluid end. Rules exist everywhere; this measures whether people expect them to hold and what they lean on when they do not.",
    lowAnchors: "Improvisation, flexible guidelines, personal relationship reliance",
    highAnchors: "Institutional rules, explicit codification, predictability requirement",
  },
  {
    code: "D4",
    title: "Ladder or Hammock?",
    subtitle: "Note on Drive (Accepting ↔ Striving)",
    stats: "Scores: 22 to 82 | World Mean: 47",
    body: "Drive runs from Accepting to Striving, measuring how much ambition, achievement, and visible success are emphasized over contentment and balance. Japan (82), China (80), and USA (71) sit at the Striving end. Norway (22) and Netherlands (30) sit at the Accepting end. Wealth appears at both ends; the difference lies in what the wealth is for.",
    lowAnchors: "Quality of life, contentment, balance, relational harmony",
    highAnchors: "Competitive achievement, visible success, performance mastery",
  },
];

export default function FolkOrientationPage() {
  const [activeTab, setActiveTab] = useState<string>("overview");

  return (
    <>
      <NavBar />
      <main className="min-h-screen bg-background text-foreground dark:bg-[#0E0E10] dark:text-white px-6 py-12 md:px-16 md:py-20">
        <div className="mx-auto max-w-6xl">
          
          {/* Header Banner */}
          <div className="text-center max-w-4xl mx-auto">
            <div className="inline-flex items-center gap-2 rounded-full border border-coral/30 bg-coral/10 px-3.5 py-1 text-xs font-semibold uppercase tracking-wider text-coral-strong dark:border-white/10 dark:bg-white/5 dark:text-white/80">
              <Compass className="h-3.5 w-3.5" />
              <span>FOLK Framework & Orientations</span>
            </div>
            <h1 className="mt-6 font-display text-4xl tracking-tight md:text-6xl text-ink dark:text-white">
              FOLK Orientation
            </h1>
            <p className="mt-4 text-xl font-medium text-ink/90 dark:text-white/90">
              Four Orientations of Life and Kinship
            </p>
            <p className="mt-2 text-base text-muted-foreground dark:text-white/70">
              Five frameworks. Five decades. One universal language.
            </p>
          </div>

          {/* Section 01 & 02: The Problem & What We Built */}
          <section className="mt-16 rounded-2xl border border-border bg-card p-8 dark:border-white/10 dark:bg-[#141518] md:p-12">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-coral-strong/10 text-coral-strong dark:bg-white/10 dark:text-white">
                <Layers className="h-5 w-5" />
              </div>
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-coral-strong dark:text-[#E14B3C]">Section 01 & 02</span>
                <h2 className="font-display text-2xl md:text-3xl text-ink dark:text-white">The Problem & What We Built</h2>
              </div>
            </div>

            <div className="mt-6 space-y-4 text-muted-foreground dark:text-white/80 leading-relaxed">
              <p>
                We all move through cultures constantly. Culture shapes how people make decisions, build trust, stay motivated, and respond to change. Decades of scholarship produced five major frameworks (<strong>Hofstede, GLOBE, Schwartz, WVS, Trompenaars</strong>), supplying over thirty overlapping dimensions. Anyone trying to use all five faces contradictory scores and conceptual noise.
              </p>
              <p>
                We took thirty-four cultural indicators across all five frameworks and ran them through a <strong>cross-framework factor analysis (Multiple Factor Analysis)</strong>. Every existing model was constructed top-down from theoretical hypotheses. FOLK is built bottom-up: we allowed data from five independent research traditions to find its own structure, naming the four genuine dimensions that emerged.
              </p>
              <p className="font-medium text-ink dark:text-white text-base">
                Where the frameworks agree, FOLK begins. Where quantitative data runs out, we enrich and validate the model with sociological literature and AI-assisted cultural synthesis across 197 countries.
              </p>
            </div>

            {/* The 4 Dimensions Grid */}
            <div className="mt-10 grid gap-6 md:grid-cols-2">
              {DIMENSIONS.map((dim, i) => {
                const icons = { D1: Users, D2: Sparkles, D3: Shield, D4: Flame };
                const Icon = icons[dim.code];
                const indexStr = `0${i + 1}`;

                return (
                  <div
                    key={dim.code}
                    className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm transition-all hover:border-neutral-300 dark:border-white/10 dark:bg-[#0A0E14] dark:hover:border-white/20"
                  >
                    <div>
                      {/* Top Row: Index/Code + Icon */}
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-[#E14B3C]">
                          {indexStr} / {dim.code} · {dim.low.toUpperCase()}–{dim.high.toUpperCase()}
                        </span>
                        <Icon className="h-4 w-4 text-neutral-400 dark:text-white/40 transition-colors group-hover:text-neutral-900 dark:group-hover:text-white" />
                      </div>

                      {/* Main Condensed Title */}
                      <h3 className="mt-2 font-display text-3xl font-black uppercase tracking-tight text-neutral-900 dark:text-white leading-none">
                        {dim.label}
                      </h3>

                      {/* Description */}
                      <p className="mt-3 text-xs leading-relaxed text-neutral-600 dark:text-white/70">
                        {dim.code === "D1" && "Identity (Social ↔ Self): Where does identity sit, with the individual or the group? The most consistent dimension in cultural literature."}
                        {dim.code === "D2" && "Expression (Restrained ↔ Open): How freely does a culture display emotion, warmth, and social energy in everyday life?"}
                        {dim.code === "D3" && "Structure (Fluid ↔ Certain): How much does a culture need rules, clarity, and predictability versus flexibility and improvisation?"}
                        {dim.code === "D4" && "Drive (Accepting ↔ Striving): What motivates societal effort — achievement, competition, and mastery, or sufficiency and balance?"}
                      </p>
                    </div>

                    {/* Minimal Line Spectrum */}
                    <div className="mt-6 pt-4 border-t border-neutral-100 dark:border-white/10">
                      <div className="flex justify-between text-[10px] font-bold uppercase tracking-wider text-neutral-500 dark:text-white/60 mb-1.5">
                        <span>{dim.low} (3)</span>
                        <span>{dim.high} (97)</span>
                      </div>
                      <div className="h-[2px] w-full overflow-hidden rounded-full bg-neutral-200 dark:bg-white/15">
                        <div
                          className="h-full rounded-full bg-[#E14B3C]"
                          style={{ width: "100%" }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Deep-Dive Notes on the 4 Orientations */}
          <section className="mt-12">
            <div className="flex items-center gap-3 mb-6">
              <BookOpen className="h-6 w-6 text-[#E14B3C]" />
              <h2 className="font-display text-3xl font-black uppercase tracking-tight text-neutral-900 dark:text-white">
                Deep-Dive Notes on the Four Orientations
              </h2>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              {ORIENTATION_NOTES.map((note) => (
                <div key={note.code} className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0A0E14]">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#E14B3C]">
                      {note.code} • {note.title}
                    </span>
                    <span className="text-[11px] font-semibold text-neutral-400 dark:text-white/50">{note.stats}</span>
                  </div>
                  <h3 className="mt-2 font-display text-xl font-black uppercase text-neutral-900 dark:text-white">{note.subtitle}</h3>
                  <p className="mt-3 text-xs leading-relaxed text-neutral-600 dark:text-white/75">{note.body}</p>

                  <div className="mt-6 pt-4 border-t border-neutral-100 dark:border-white/10 grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="block font-bold text-neutral-400 dark:text-white/40 uppercase text-[10px] tracking-wider">Low Pole</span>
                      <span className="text-neutral-700 dark:text-white/80 font-medium text-xs">{note.lowAnchors}</span>
                    </div>
                    <div>
                      <span className="block font-bold text-neutral-400 dark:text-white/40 uppercase text-[10px] tracking-wider">High Pole</span>
                      <span className="text-neutral-700 dark:text-white/80 font-medium text-xs">{note.highAnchors}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Section 04: Why It Matters */}
          <section className="mt-12 rounded-2xl border border-border bg-card p-8 dark:border-white/10 dark:bg-[#141518]">
            <h2 className="font-display text-2xl md:text-3xl text-ink dark:text-white">Section 04 — Why It Matters</h2>
            <div className="mt-6 grid gap-6 md:grid-cols-3 text-sm text-muted-foreground dark:text-white/80">
              <div className="rounded-xl border border-border p-5 dark:border-white/5 dark:bg-white/[0.02]">
                <strong className="block text-ink dark:text-white text-base mb-1">Working Together & Leading</strong>
                Predicts friction around feedback, decision-making, and accountability. Leading across Striving/Certain vs Open/Fluid cultures requires explicit style shifts.
              </div>
              <div className="rounded-xl border border-border p-5 dark:border-white/5 dark:bg-white/[0.02]">
                <strong className="block text-ink dark:text-white text-base mb-1">Building Trust</strong>
                Open vs Restrained and Self vs Social orientations dictate how trust is built, how ideas land, and decision timelines.
              </div>
              <div className="rounded-xl border border-border p-5 dark:border-white/5 dark:bg-white/[0.02]">
                <strong className="block text-ink dark:text-white text-base mb-1">Navigating Change</strong>
                A change natural in a Fluid, Striving culture meets resistance in a Certain, Accepting one. FOLK explains why and how to adapt.
              </div>
            </div>
          </section>

          {/* Section 05: What This Framework Is Not */}
          <section className="mt-12 rounded-2xl border border-border bg-card p-8 dark:border-white/10 dark:bg-[#141518]">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-6 w-6 text-coral-strong dark:text-[#E14B3C]" />
              <h2 className="font-display text-2xl text-ink dark:text-white">Section 05 — What This Framework Is Not</h2>
            </div>
            <div className="mt-6 grid gap-6 text-sm text-muted-foreground dark:text-white/80 md:grid-cols-3">
              <div className="rounded-xl border border-border p-5 dark:border-white/5 dark:bg-white/[0.02]">
                <strong className="block text-ink dark:text-white text-base mb-1">Not a Replacement</strong>
                FOLK captures the common signal. Users needing micro-level granularity (such as Hofstede&apos;s individual scores) should use source frameworks directly.
              </div>
              <div className="rounded-xl border border-border p-5 dark:border-white/5 dark:bg-white/[0.02]">
                <strong className="block text-ink dark:text-white text-base mb-1">Uneven Anchoring</strong>
                Identity and Expression are richly anchored across frameworks. Structure and Drive rest on fewer primary anchors, particularly at Fluid & Accepting poles.
              </div>
              <div className="rounded-xl border border-border p-5 dark:border-white/5 dark:bg-white/[0.02]">
                <strong className="block text-ink dark:text-white text-base mb-1">One Conceptual Override</strong>
                GLOBE Performance Orientation statistically grouped with Expression, but its meaning (competitive achievement) belongs in Drive. We reassigned it and disclose it transparently.
              </div>
            </div>
          </section>

          {/* Section 06: How FOLK Relates to Source Frameworks */}
          <section className="mt-12">
            <div className="flex items-center gap-3 mb-6">
              <Table className="h-6 w-6 text-coral-strong dark:text-[#E14B3C]" />
              <h2 className="font-display text-3xl text-ink dark:text-white">
                Section 06 — Source Framework Mapping
              </h2>
            </div>

            <div className="overflow-x-auto rounded-2xl border border-border bg-card dark:border-white/10 dark:bg-[#141518]">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border bg-muted/50 dark:border-white/10 dark:bg-white/5 text-ink dark:text-white">
                  <tr>
                    <th className="p-4 font-semibold">Framework</th>
                    <th className="p-4 font-semibold">Core Strength</th>
                    <th className="p-4 font-semibold">Key Limitation</th>
                    <th className="p-4 font-semibold">How It Maps Into FOLK</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border dark:divide-white/10 text-muted-foreground dark:text-white/80">
                  {COMPARISON_TABLE.map((row, i) => (
                    <tr key={i} className="hover:bg-muted/30 dark:hover:bg-white/[0.02]">
                      <td className="p-4 font-bold text-ink dark:text-white whitespace-nowrap">{row.framework}</td>
                      <td className="p-4 min-w-[200px]">{row.strength}</td>
                      <td className="p-4 min-w-[200px]">{row.limitation}</td>
                      <td className="p-4 min-w-[250px] text-xs text-ink/90 dark:text-white/90">{row.mapping}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Section 07: The Invitation */}
          <div className="mt-12 rounded-2xl bg-ink p-8 text-white dark:bg-[#141518] dark:border dark:border-white/10 md:p-10 flex flex-col md:flex-row items-center justify-between gap-6">
            <div>
              <span className="text-xs font-semibold uppercase tracking-widest text-coral-strong dark:text-[#E14B3C]">
                SECTION 07 — THE INVITATION
              </span>
              <h3 className="mt-2 font-display text-2xl md:text-3xl text-white">
                Identity. Expression. Structure. Drive.
              </h3>
              <p className="mt-2 text-sm text-white/80 max-w-3xl">
                Four orientations. Five frameworks. One universal language. Map any country, team, or society against the four orientations to see where culture actually sits.
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
