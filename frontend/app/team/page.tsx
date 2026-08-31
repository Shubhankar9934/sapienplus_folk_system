"use client";

import { NavBar } from "@/components/NavBar";
import { SiteFooter } from "@/components/SiteFooter";
import { Users, Brain, Scale, Cpu } from "lucide-react";
import Image from "next/image";

const TEAM_MEMBERS = [
  {
    name: "Dr. Aruni Ghosh",
    title: "The Conceptual Architect",
    role: "Framework Conception & Cultural Architecture",
    image: "/images/team/aruni-ghosh.png",
    bio: "Aruni brings together consumer insight, culture, behavioural science and analytics. His career spans Nielsen and senior regional/global Consumer Insights & Analytics leadership at Philip Morris International, before moving into innovation at SixthFactor Consulting. He holds a PhD in Marketing from IIM Kashipur.",
    contribution: "Conceptualized the FOLK framework—shaping the underlying cultural questions, dimensions, and qualitative interpretations that the statistical and AI layers make measurable and scalable.",
    icon: Brain,
  },
  {
    name: "Pranav Krishna",
    title: "The Statistical Backbone",
    role: "Quantitative Validation & Measurement Architecture",
    image: "/images/team/pranav-krishna.png",
    bio: "Pranav brings mathematical discipline to ideas about culture. An ISI mathematics graduate and EPFL-trained statistician, his background ranges from statistical modelling and climate extremes to time-series forecasting, Monte Carlo simulation, and Marketing Mix Modelling. He serves as Head Statistician at Sapien+AI.",
    contribution: "Turned the conceptual framework into an empirically defensible model—leading the factor analysis, measurement relationships, MICE imputation, and statistical validation.",
    icon: Scale,
  },
  {
    name: "Shubhankar Kumar",
    title: "The AI Builder",
    role: "Multi-Agent System & Reasoning Architecture",
    image: "/images/team/shubhankar-kumar.png",
    bio: "Shubhankar works where AI stops being a model and starts becoming a system. An AI Research Engineer at Sapien+AI with a foundation in Mathematics and Scientific Computing, his work spans agentic AI, multi-agent decision systems, knowledge graphs, and adaptive optimization under uncertainty.",
    contribution: "Built the AI layer—translating the framework and its statistical foundations into agentic computational systems capable of interpreting, deliberating, and scaling cultural intelligence globally.",
    icon: Cpu,
  },
];

export default function TeamPage() {
  return (
    <>
      <NavBar />
      <main className="min-h-screen bg-background text-foreground dark:bg-[#0E0E10] dark:text-white px-6 py-12 md:px-16 md:py-20">
        <div className="mx-auto max-w-6xl">
          
          {/* Header */}
          <div className="max-w-4xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-coral/30 bg-coral/10 px-3.5 py-1 text-xs font-semibold uppercase tracking-wider text-coral-strong dark:border-white/10 dark:bg-white/5 dark:text-white/80">
              <Users className="h-3.5 w-3.5" />
              <span>FOLK Research Team</span>
            </div>
            <h1 className="mt-6 font-display text-4xl tracking-tight text-ink dark:text-white md:text-6xl">
              Meet the Team
            </h1>
            <p className="mt-4 text-lg text-muted-foreground dark:text-white/70">
              The architects, statisticians, and AI engineers behind FOLK Cultural Intelligence.
            </p>
          </div>

          {/* Team Members Grid */}
          <div className="mt-16 grid gap-8 md:grid-cols-3">
            {TEAM_MEMBERS.map((member, i) => (
              <div
                key={i}
                className="flex flex-col justify-between overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-sm dark:border-white/10 dark:bg-[#141518]"
              >
                <div>
                  {/* Photo Container */}
                  <div className="relative h-64 w-full overflow-hidden rounded-xl bg-muted dark:bg-white/5">
                    <img
                      src={member.image}
                      alt={member.name}
                      className="h-full w-full object-cover object-top transition duration-300 hover:scale-105"
                    />
                  </div>

                  <h3 className="mt-6 font-display text-2xl text-ink dark:text-white">{member.name}</h3>
                  <p className="text-xs font-bold uppercase tracking-wider text-coral-strong dark:text-[#E14B3C] mt-1">
                    {member.title}
                  </p>

                  <p className="mt-4 text-xs text-muted-foreground dark:text-white/75 leading-relaxed">
                    {member.bio}
                  </p>
                </div>

                <div className="mt-8 pt-4 border-t border-border dark:border-white/10 text-xs text-muted-foreground dark:text-white/80">
                  <strong className="block text-ink dark:text-white mb-1">FOLK Contribution:</strong>
                  {member.contribution}
                </div>
              </div>
            ))}
          </div>

        </div>
      </main>
      <SiteFooter />
    </>
  );
}
