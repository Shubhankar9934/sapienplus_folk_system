"use client";

import { NavBar } from "@/components/NavBar";
import { SiteFooter } from "@/components/SiteFooter";
import { BookOpen, Layers, Cpu, CheckCircle2, Scale, ArrowRight, Table, Filter, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

const COVERAGE_TABLE = [
  { coverage: "All five frameworks", count: "~27 countries" },
  { coverage: "At least four", count: "60 countries" },
  { coverage: "At least three", count: "84 countries" },
  { coverage: "At least two", count: "120 countries" },
  { coverage: "At least one", count: "171 countries" },
  { coverage: "No framework data (Extension)", count: "26 countries (Direct AI Council Evaluation)" },
];

const AGENT_ROLES = [
  {
    role: "Cultural Anthropologist",
    focus: "Kinship, ritual, custom, and everyday practice.",
  },
  {
    role: "Institutional Analyst",
    focus: "The state, law, religion, and how rules and power operate.",
  },
  {
    role: "Statistician",
    focus: "Keeps the score consistent with quantitative data and baseline.",
  },
  {
    role: "Comparativist",
    focus: "Checks the score against regional peer groups and similar countries.",
  },
  {
    role: "Country Specialist",
    focus: "Supplies qualitative nuance and country-specific detail.",
  },
  {
    role: "Skeptic",
    focus: "Argues against the emerging answer and finds the weakest point.",
  },
];

const FACTOR_ROWS = [
  // D1 Identity
  { fw: "WVS", label: "Choice", d1: "0.959", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Self pole" },
  { fw: "WVS", label: "Equality", d1: "0.915", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Self pole" },
  { fw: "GLO", label: "GLOBE UA — conformity pressure", d1: "-0.904", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Social pole (Empirical surprise)" },
  { fw: "SCH", label: "Embeddedness", d1: "-0.892", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Social pole" },
  { fw: "HOF", label: "Individualism", d1: "0.872", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Self pole" },
  { fw: "HOF", label: "Power Distance", d1: "-0.872", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Social pole" },
  { fw: "SCH", label: "Affective Autonomy", d1: "0.854", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Self pole" },
  { fw: "SCH", label: "Intellectual Autonomy", d1: "0.841", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Self pole" },
  { fw: "TRO", label: "Ascription-Achievement", d1: "0.841", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Self pole" },
  { fw: "TRO", label: "Particularism-Universalism", d1: "0.775", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Self pole" },
  { fw: "TRO", label: "Diffuse-Specific", d1: "0.756", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Self pole" },
  { fw: "WVS", label: "Voice", d1: "0.675", d2: "0.461", d3: "—", d4: "—", asgn: "D1", note: "Also Open: Voice = self-expression & open communication" },
  { fw: "SCH", label: "Hierarchy", d1: "-0.646", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Social pole" },
  { fw: "TRO", label: "Communitarianism-Individualism", d1: "0.640", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Self pole" },
  { fw: "SCH", label: "Egalitarianism", d1: "0.591", d2: "0.683", d3: "—", d4: "—", asgn: "D1", note: "Also Open: flat social relations produce autonomy & openness" },
  { fw: "GLO", label: "Gender Egalitarianism", d1: "0.539", d2: "0.636", d3: "—", d4: "—", asgn: "D1", note: "Also Open: flat gender norms" },
  { fw: "WVS", label: "Defiance", d1: "0.521", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Self pole" },
  { fw: "WVS", label: "Autonomy", d1: "0.501", d2: "—", d3: "—", d4: "—", asgn: "D1", note: "Self pole" },
  { fw: "GLO", label: "Institutional Collectivism", d1: "-0.510", d2: "0.568", d3: "—", d4: "—", asgn: "D1", note: "Social pole & Open (in-group warmth)" },

  // D2 Expression
  { fw: "HOF", label: "Long-Term Orientation", d1: "—", d2: "-0.807", d3: "—", d4: "—", asgn: "D2", note: "Restrained pole" },
  { fw: "HOF", label: "Indulgence", d1: "—", d2: "0.797", d3: "—", d4: "—", asgn: "D2", note: "Open pole" },
  { fw: "TRO", label: "Future-Past Orientation", d1: "-0.811", d2: "-0.807", d3: "—", d4: "—", asgn: "D2", note: "Past-oriented = Social & Restrained" },
  { fw: "GLO", label: "In-Group Collectivism", d1: "—", d2: "0.625", d3: "—", d4: "—", asgn: "D2", note: "Open pole" },
  { fw: "GLO", label: "Power Distance (practices)", d1: "—", d2: "-0.547", d3: "—", d4: "-0.620", asgn: "D2", note: "Restrained pole & Accepting" },
  { fw: "WVS", label: "Scepticism", d1: "—", d2: "0.490", d3: "—", d4: "—", asgn: "D2", note: "Open pole" },
  { fw: "GLO", label: "Humane Orientation", d1: "—", d2: "0.455", d3: "—", d4: "—", asgn: "D2", note: "Open pole" },
  { fw: "GLO", label: "Assertiveness", d1: "—", d2: "-0.494", d3: "-0.573", d4: "—", asgn: "D2", note: "Restrained pole & Fluid" },

  // D3 Structure
  { fw: "HOF", label: "Uncertainty Avoidance", d1: "—", d2: "—", d3: "0.858", d4: "0.333", asgn: "D3", note: "Certain pole & Striving" },
  { fw: "SCH", label: "Harmony", d1: "—", d2: "—", d3: "0.589", d4: "—", asgn: "D3", note: "Certain pole" },
  { fw: "GLO", label: "Future Orientation", d1: "—", d2: "—", d3: "0.420", d4: "—", asgn: "D3", note: "Reassigned from D2 (Planning = managing uncertainty)" },

  // D4 Drive
  { fw: "SCH", label: "Mastery", d1: "—", d2: "—", d3: "—", d4: "0.680", asgn: "D4", note: "Striving pole" },
  { fw: "WVS", label: "Relativism", d1: "—", d2: "—", d3: "—", d4: "-0.644", asgn: "D4", note: "Accepting pole" },
  { fw: "GLO", label: "Performance Orientation", d1: "—", d2: "—", d3: "—", d4: "0.425", asgn: "D4", note: "Reassigned from D2 (Achievement = Drive)" },
  { fw: "HOF", label: "Masculinity", d1: "—", d2: "—", d3: "—", d4: "0.231", asgn: "D4", note: "Striving pole" },

  // Unassigned / Cross-Spread
  { fw: "TRO", label: "Affective-Neutral", d1: "0.415", d2: "-0.510", d3: "—", d4: "—", asgn: "Cross", note: "Spreads across D1 & D2" },
  { fw: "TRO", label: "External-Internal", d1: "0.550", d2: "0.420", d3: "—", d4: "—", asgn: "Cross", note: "Spreads across D1 & D2 (Internal control = Self & Open)" },
];

export default function MethodologyPage() {
  const [filterAsgn, setFilterAsgn] = useState<string>("ALL");

  const filteredFactorRows = FACTOR_ROWS.filter((r) => {
    if (filterAsgn === "ALL") return true;
    return r.asgn === filterAsgn;
  });

  return (
    <>
      <NavBar />
      <main className="min-h-screen bg-background text-foreground dark:bg-[#0E0E10] dark:text-white px-6 py-12 md:px-16 md:py-20">
        <div className="mx-auto max-w-6xl">
          
          {/* Header Banner */}
          <div className="max-w-4xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-coral/30 bg-coral/10 px-3.5 py-1 text-xs font-semibold uppercase tracking-wider text-coral-strong dark:border-white/10 dark:bg-white/5 dark:text-white/80">
              <BookOpen className="h-3.5 w-3.5" />
              <span>FOLK Methodology Note</span>
            </div>
            <h1 className="mt-6 font-display text-4xl tracking-tight text-ink dark:text-white md:text-6xl">
              How the FOLK Scores Were Built
            </h1>
            <p className="mt-4 text-xl font-medium text-ink/90 dark:text-white/90">
              Methodology note: the four orientations, the statistical baseline, and the AI-council scoring
            </p>
            <p className="mt-3 text-base text-muted-foreground dark:text-white/75 leading-relaxed">
              The scores were produced in three stages: a <strong>statistical stage</strong> that defined the four orientations and a starting baseline number for each country; an <strong>AI council stage</strong> that reviewed evidence and qualitative literature; and an <strong>integrator stage</strong> that set the final published score.
            </p>
          </div>

          {/* Part 1 — Defining the Four Orientations */}
          <section className="mt-16 rounded-2xl border border-border bg-card p-8 dark:border-white/10 dark:bg-[#141518] md:p-12">
            <div className="flex items-center gap-3">
              <span className="rounded-md bg-coral-strong px-3 py-1 text-xs font-bold text-white uppercase tracking-wider">
                Part 1
              </span>
              <h2 className="font-display text-2xl md:text-3xl text-ink dark:text-white">
                Defining the Four Orientations (Statistics)
              </h2>
            </div>

            <div className="mt-6 space-y-4 text-muted-foreground dark:text-white/80 leading-relaxed text-sm md:text-base">
              <p>
                Five established cultural frameworks were used as inputs: <strong>Hofstede, Trompenaars, GLOBE, Schwartz, and the World Values Survey (WVS)</strong>. Supplying thirty-four cultural indicators across ~25 complete-data countries, factor analysis (Multiple Factor Analysis) was run to find how many distinct underlying orientations were present. It empirically identified four.
              </p>
              <p>
                The name <strong>FOLK</strong> encodes <strong>Four Orientations of Life and Kinship</strong>:
              </p>
              <ul className="grid gap-3 md:grid-cols-2 pt-2 text-xs md:text-sm">
                <li className="rounded-xl border border-border p-4 bg-background dark:border-white/10 dark:bg-[#0E0E10]">
                  <strong className="text-ink dark:text-white block text-base mb-1">Kinship (Who you belong to & show it)</strong>
                  • <strong>Identity (Social → Self):</strong> Where identity sits — group vs. individual.<br />
                  • <strong>Expression (Restrained → Open):</strong> How openly warmth and emotion are displayed.
                </li>
                <li className="rounded-xl border border-border p-4 bg-background dark:border-white/10 dark:bg-[#0E0E10]">
                  <strong className="text-ink dark:text-white block text-base mb-1">Life (How you organize & strive)</strong>
                  • <strong>Structure (Fluid → Certain):</strong> Preference for rules vs. flexibility.<br />
                  • <strong>Drive (Accepting → Striving):</strong> Contentment vs. competitive achievement.
                </li>
              </ul>
            </div>

            {/* Coverage & Imputation Table */}
            <div className="mt-10">
              <h3 className="font-display text-xl text-ink dark:text-white mb-4">Sample Expansion & MICE Imputation</h3>
              <div className="overflow-x-auto rounded-xl border border-border bg-background dark:border-white/10 dark:bg-[#0E0E10]">
                <table className="w-full text-left text-xs md:text-sm">
                  <thead className="border-b border-border bg-muted/50 dark:border-white/10 dark:bg-white/5 text-ink dark:text-white font-semibold">
                    <tr>
                      <th className="p-3.5">Framework Coverage Level</th>
                      <th className="p-3.5">Countries Scored</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border dark:divide-white/10 text-muted-foreground dark:text-white/80">
                    {COVERAGE_TABLE.map((row, i) => (
                      <tr key={i}>
                        <td className="p-3.5 font-medium">{row.coverage}</td>
                        <td className="p-3.5 font-semibold text-ink dark:text-white">{row.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-xs text-muted-foreground dark:text-white/60">
                Missing values for 171 countries with partial framework data were filled via MICE (Multivariate Imputation by Chained Equations, 40 draws). Stability was validated using Tucker&apos;s φ (0.95+ green). The remaining 26 countries with no framework data were evaluated directly by the AI Council from qualitative evidence.
              </p>
            </div>
          </section>

          {/* FOLK Factor Structure Interactive Matrix (From FOLK_Factor_Structure.html) */}
          <section className="mt-12 rounded-2xl border border-border bg-card p-8 dark:border-white/10 dark:bg-[#141518]">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-coral-strong dark:text-[#E14B3C]">
                  <Table className="h-4 w-4" />
                  <span>Empirical Factor Structure</span>
                </div>
                <h2 className="font-display text-2xl md:text-3xl text-ink dark:text-white mt-1">
                  FOLK Factor Structure Matrix (36 Indicators)
                </h2>
                <p className="text-xs text-muted-foreground dark:text-white/70 mt-1">
                  Cross-framework factor loadings across Hofstede (HOF), GLOBE (GLO), Schwartz (SCH), World Values Survey (WVS), and Trompenaars (TRO).
                </p>
              </div>

              {/* Filter Tabs */}
              <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-border bg-background p-1.5 dark:border-white/10 dark:bg-[#0E0E10]">
                {["ALL", "D1", "D2", "D3", "D4", "Cross"].map((code) => (
                  <button
                    key={code}
                    onClick={() => setFilterAsgn(code)}
                    className={`rounded px-2.5 py-1 text-xs font-semibold transition ${
                      filterAsgn === code
                        ? "bg-coral-strong text-white dark:bg-white dark:text-ink"
                        : "text-muted-foreground hover:text-ink dark:text-white/60 dark:hover:text-white"
                    }`}
                  >
                    {code === "ALL" ? "All Indicators" : code === "Cross" ? "Cross-Loadings" : code}
                  </button>
                ))}
              </div>
            </div>

            {/* Matrix Table */}
            <div className="mt-6 overflow-x-auto rounded-xl border border-border bg-background dark:border-white/10 dark:bg-[#0E0E10]">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-border bg-muted/50 dark:border-white/10 dark:bg-white/5 text-ink dark:text-white font-semibold">
                  <tr>
                    <th className="p-3">FW</th>
                    <th className="p-3">Attribute / Indicator</th>
                    <th className="p-3 text-center">D1 (Identity)</th>
                    <th className="p-3 text-center">D2 (Expression)</th>
                    <th className="p-3 text-center">D3 (Structure)</th>
                    <th className="p-3 text-center">D4 (Drive)</th>
                    <th className="p-3">Assigned</th>
                    <th className="p-3">Notes & Mechanism</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border dark:divide-white/10 text-muted-foreground dark:text-white/80">
                  {filteredFactorRows.map((row, i) => (
                    <tr key={i} className="hover:bg-muted/30 dark:hover:bg-white/[0.02]">
                      <td className="p-3 font-mono font-bold text-ink/70 dark:text-white/70">{row.fw}</td>
                      <td className="p-3 font-semibold text-ink dark:text-white min-w-[180px]">{row.label}</td>
                      <td className="p-3 text-center font-mono">{row.d1}</td>
                      <td className="p-3 text-center font-mono">{row.d2}</td>
                      <td className="p-3 text-center font-mono">{row.d3}</td>
                      <td className="p-3 text-center font-mono">{row.d4}</td>
                      <td className="p-3 font-bold text-coral-strong dark:text-[#E14B3C]">{row.asgn}</td>
                      <td className="p-3 text-xs text-muted-foreground dark:text-white/70 min-w-[220px]">{row.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Part 2 — Statistical Issues Resolved by AI Council */}
          <section className="mt-12 rounded-2xl border border-border bg-card p-8 dark:border-white/10 dark:bg-[#141518]">
            <div className="flex items-center gap-3">
              <span className="rounded-md bg-coral-strong px-3 py-1 text-xs font-bold text-white uppercase tracking-wider">
                Part 2
              </span>
              <h2 className="font-display text-2xl text-ink dark:text-white">
                The Baseline Score & Remaining Statistical Issues
              </h2>
            </div>
            <p className="mt-4 text-sm text-muted-foreground dark:text-white/80 leading-relaxed">
              Statistical baseline scores were accompanied by confidence intervals (e.g. Bhutan Identity: baseline 45, interval 28.6–57.2). However, raw statistical scores suffered from three limitations:
            </p>
            <div className="mt-6 grid gap-4 md:grid-cols-3 text-xs md:text-sm">
              <div className="rounded-xl border border-border p-4 dark:border-white/5 dark:bg-white/[0.02]">
                <strong className="block text-ink dark:text-white text-base mb-1">1. Scale Compression</strong>
                Scores clustered heavily near mid-scale (50), leaving much of the 0–100 range under-utilized.
              </div>
              <div className="rounded-xl border border-border p-4 dark:border-white/5 dark:bg-white/[0.02]">
                <strong className="block text-ink dark:text-white text-base mb-1">2. Identical Scores</strong>
                Multiple countries received identical imputed values across certain orientations.
              </div>
              <div className="rounded-xl border border-border p-4 dark:border-white/5 dark:bg-white/[0.02]">
                <strong className="block text-ink dark:text-white text-base mb-1">3. Flat Profiles</strong>
                Heavy imputation created flat profiles across orientations for data-sparse countries.
              </div>
            </div>
          </section>

          {/* Part 3 — Multi-Agent AI Council Architecture */}
          <section className="mt-12 rounded-2xl border border-border bg-card p-8 dark:border-white/10 dark:bg-[#141518]">
            <div className="flex items-center gap-3">
              <span className="rounded-md bg-coral-strong px-3 py-1 text-xs font-bold text-white uppercase tracking-wider">
                Part 3
              </span>
              <h2 className="font-display text-2xl text-ink dark:text-white">
                Multi-Agent AI Council Architecture
              </h2>
            </div>
            <p className="mt-4 text-sm text-muted-foreground dark:text-white/80 leading-relaxed">
              To prevent single-model confirmation bias, the council runs six specialized expert roles across multiple underlying language models (Claude, OpenAI, DeepSeek):
            </p>

            <div className="mt-6 grid gap-4 md:grid-cols-3 text-xs md:text-sm">
              {AGENT_ROLES.map((agent, i) => (
                <div key={i} className="rounded-xl border border-border p-4 bg-background dark:border-white/10 dark:bg-[#0E0E10]">
                  <strong className="block text-ink dark:text-white text-base">{agent.role}</strong>
                  <p className="mt-1 text-muted-foreground dark:text-white/70">{agent.focus}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Part 4 — Formulaic Score Pipeline to Final Decision */}
          <section className="mt-12 rounded-2xl border border-border bg-card p-8 dark:border-white/10 dark:bg-[#141518]">
            <div className="flex items-center gap-3">
              <span className="rounded-md bg-coral-strong px-3 py-1 text-xs font-bold text-white uppercase tracking-wider">
                Part 4
              </span>
              <h2 className="font-display text-2xl text-ink dark:text-white">
                Formulaic Score Pipeline to Final Decision
              </h2>
            </div>

            <div className="mt-8 flex flex-col md:flex-row items-center justify-between gap-4 text-center text-xs md:text-sm">
              <div className="rounded-xl border border-border p-4 bg-background dark:border-white/10 dark:bg-[#0E0E10] w-full">
                <span className="font-bold text-coral-strong dark:text-[#E14B3C] block">1. Baseline Reference</span>
                <p className="text-muted-foreground dark:text-white/70 mt-1">MFA Factor Baseline</p>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground hidden md:block shrink-0" />
              <div className="rounded-xl border border-border p-4 bg-background dark:border-white/10 dark:bg-[#0E0E10] w-full">
                <span className="font-bold text-coral-strong dark:text-[#E14B3C] block">2. Council Consensus</span>
                <p className="text-muted-foreground dark:text-white/70 mt-1">Weighted Vote Average</p>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground hidden md:block shrink-0" />
              <div className="rounded-xl border border-border p-4 bg-background dark:border-white/10 dark:bg-[#0E0E10] w-full">
                <span className="font-bold text-coral-strong dark:text-[#E14B3C] block">3. Recommended Score</span>
                <p className="text-muted-foreground dark:text-white/70 mt-1">Formulaic & Reproducible</p>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground hidden md:block shrink-0" />
              <div className="rounded-xl border border-border p-4 bg-background dark:border-white/10 dark:bg-[#0E0E10] w-full">
                <span className="font-bold text-coral-strong dark:text-[#E14B3C] block">4. Final Score</span>
                <p className="text-muted-foreground dark:text-white/70 mt-1">Integrator LLM Decision</p>
              </div>
            </div>
          </section>

          {/* Bottom Callout */}
          <div className="mt-12 rounded-2xl bg-ink p-8 text-white dark:bg-[#141518] dark:border dark:border-white/10 md:p-10 flex flex-col md:flex-row items-center justify-between gap-6">
            <div>
              <span className="text-xs font-semibold uppercase tracking-widest text-coral-strong dark:text-[#E14B3C]">
                SUMMARY
              </span>
              <h3 className="mt-2 font-display text-2xl md:text-3xl text-white">
                34 Indicators • 197 Countries • 1 Model
              </h3>
              <p className="mt-2 text-sm text-white/80 max-w-3xl">
                Factor analysis over 34 indicators defined the baseline; six specialized AI council agents reviewed qualitative evidence; and an Integrator set the final score.
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
