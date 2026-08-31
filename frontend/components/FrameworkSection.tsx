"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ChevronDown } from "lucide-react";

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

type Orientation = {
  name: string;
  question: string;
  highPole: string;
  lowPole: string;
  highBlurb: string;
  lowBlurb: string;
  color: string;
};

// Matches FOLK's actual D1-D4 framework from lib/dimensions.ts
const ORIENTATIONS: Orientation[] = [
  {
    name: "Identity",
    question: "Where does the self begin and end?",
    highPole: "Self",
    lowPole: "Social",
    highBlurb:
      "People see themselves as independent individuals. Personal choice and standing out are prized.",
    lowBlurb:
      "People see themselves through family and community. Belonging and loyalty come first.",
    color: "#5b8def",
  },
  {
    name: "Expression",
    question: "How freely is emotion shown?",
    highPole: "Open",
    lowPole: "Restrained",
    highBlurb:
      "Emotion, warmth and social energy flow freely. Feelings are shown, not hidden.",
    lowBlurb:
      "Emotion is held in check. Composure and reserve are read as maturity.",
    color: "#e879a6",
  },
  {
    name: "Structure",
    question: "How much does a culture need rules and clarity?",
    highPole: "Certain",
    lowPole: "Fluid",
    highBlurb:
      "Ambiguity feels uncomfortable. Clear rules and plans provide security.",
    lowBlurb:
      "Ambiguity is tolerable, even energizing. People improvise and adapt.",
    color: "#f0b429",
  },
  {
    name: "Drive",
    question: "What motivates — achievement, or harmony?",
    highPole: "Striving",
    lowPole: "Accepting",
    highBlurb:
      "Achievement, mastery and ambition give life meaning. Progress is celebrated.",
    lowBlurb:
      "Harmony, balance and contentment matter more than winning.",
    color: "#34d399",
  },
];

export function FrameworkSection() {
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        "[data-fw-head]",
        { y: 36, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.9,
          ease: "power3.out",
          stagger: 0.08,
          scrollTrigger: { trigger: sectionRef.current, start: "top 85%", once: true },
        },
      );

      gsap.utils.toArray<HTMLElement>("[data-fw-row]").forEach((row) => {
        gsap.fromTo(
          row,
          { y: 28, opacity: 0 },
          {
            y: 0,
            opacity: 1,
            duration: 0.7,
            ease: "power3.out",
            scrollTrigger: { trigger: row, start: "top 88%", once: true },
          },
        );
        const bar = row.querySelector("[data-fw-bar]");
        if (bar) {
          gsap.fromTo(
            bar,
            { scaleX: 0 },
            {
              scaleX: 1,
              duration: 1.1,
              ease: "power3.out",
              transformOrigin: "left center",
              scrollTrigger: { trigger: row, start: "top 85%", once: true },
            },
          );
        }
      });
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  return (
    <section
      ref={sectionRef}
      className="relative isolate w-full overflow-hidden bg-background text-ink dark:bg-[#0E0E10] dark:text-white"
    >
      {/* Soft coral bloom, top-right */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-40 -top-40 z-0 h-[70vw] max-h-[900px] w-[70vw] max-w-[900px] rounded-full opacity-70 dark:opacity-40"
        style={{
          background:
            "radial-gradient(circle, oklch(0.82 0.09 25 / 55%) 0%, transparent 65%)",
        }}
      />
      {/* Oversized watermark */}
      <div
        aria-hidden
        className="pointer-events-none absolute bottom-[-8%] right-[-2%] z-0 select-none font-display leading-none text-ink/[0.04] dark:text-white/[0.05]"
        style={{ fontSize: "26vw" }}
      >
        04
      </div>

      <div className="relative z-10 mx-auto w-full max-w-6xl px-6 pb-28 pt-24 sm:px-10 md:pt-32">
        {/* Eyebrow */}
        <div
          data-fw-head
          className="flex items-center gap-2 uppercase text-ink/60 dark:text-white/60"
          style={{ fontSize: "11px", fontWeight: 600, letterSpacing: "0.22em" }}
        >
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-coral-strong dark:bg-[#E14B3C]" />
          The Framework / 04 Dimensions
        </div>

        {/* Headline + intro */}
        <div className="mt-6 flex flex-col gap-8 md:flex-row md:items-end md:justify-between">
          <h2
            data-fw-head
            className="font-display uppercase leading-[0.86] tracking-[-0.01em]"
            style={{ fontSize: "clamp(48px, 8vw, 104px)" }}
          >
            How a{" "}
            <span className="text-coral-strong dark:text-[#E14B3C]">Culture</span>
            <br />
            Thinks.
          </h2>
          <p
            data-fw-head
            className="max-w-sm text-[15px] leading-relaxed text-ink/70 dark:text-white/65 md:pb-4"
          >
            Every culture answers four deep questions differently. FOLK scores
            each country on all four dimensions — giving you a complete cultural
            fingerprint, not just a single number.
          </p>
        </div>

        {/* Rows */}
        <div className="mt-16 border-t border-ink/12 dark:border-white/12">
          {ORIENTATIONS.map((o, i) => (
            <div
              key={o.name}
              data-fw-row
              className="group grid grid-cols-1 gap-6 border-b border-ink/12 py-10 md:grid-cols-[minmax(0,0.42fr)_minmax(0,1fr)] md:gap-12 dark:border-white/12"
            >
              {/* Label column */}
              <div className="flex items-start gap-4">
                <span className="font-display text-4xl leading-none text-ink/15 transition-colors duration-300 group-hover:text-coral-strong/60 dark:text-white/15 md:text-5xl">
                  0{i + 1}
                </span>
                <div>
                  <h3 className="font-display text-2xl uppercase leading-none md:text-3xl">
                    {o.name}
                  </h3>
                  <p className="mt-2 max-w-[24ch] text-sm italic leading-relaxed text-ink/55 dark:text-white/55">
                    {o.question}
                  </p>
                </div>
              </div>

              {/* Spectrum column */}
              <div>
                <div
                  data-fw-bar
                  className="h-[3px] w-full rounded-full"
                  style={{
                    background: `linear-gradient(90deg, ${o.color} 0%, oklch(0.18 0.02 250 / 40%) 50%, oklch(0.18 0.02 250) 100%)`,
                  }}
                />
                <div
                  className="mt-3 flex items-center justify-between uppercase text-ink/60 dark:text-white/60"
                  style={{ fontSize: "10px", fontWeight: 600, letterSpacing: "0.22em" }}
                >
                  <span>{o.highPole}</span>
                  <span>{o.lowPole}</span>
                </div>

                <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="rounded-md border border-ink/8 bg-ink/[0.03] p-4 transition-colors duration-300 hover:border-coral-strong/40 dark:border-white/10 dark:bg-white/[0.04]">
                    <p className="text-[13px] leading-relaxed text-ink/75 dark:text-white/70">
                      <span
                        className="mr-1 uppercase"
                        style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.14em", color: o.color }}
                      >
                        High ·
                      </span>
                      {o.highBlurb}
                    </p>
                  </div>
                  <div className="rounded-md border border-ink/8 bg-ink/[0.03] p-4 transition-colors duration-300 hover:border-ink/30 dark:border-white/10 dark:bg-white/[0.04] dark:hover:border-white/30">
                    <p className="text-[13px] leading-relaxed text-ink/75 dark:text-white/70">
                      <span
                        className="mr-1 uppercase text-ink/70 dark:text-white/70"
                        style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.14em" }}
                      >
                        Low ·
                      </span>
                      {o.lowBlurb}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Scroll indicator */}
        <div className="mt-16 flex flex-col items-center gap-3">
          <span
            className="uppercase text-ink/60 dark:text-white/60"
            style={{ fontSize: "11px", letterSpacing: "0.25em" }}
          >
            Scroll
          </span>
          <a
            href="#globe"
            aria-label="Scroll to next section"
            className="flex h-11 w-11 items-center justify-center rounded-full bg-ink text-background transition-transform hover:translate-y-1 dark:bg-white dark:text-[#0E0E10]"
          >
            <ChevronDown className="h-5 w-5" strokeWidth={2.5} />
          </a>
        </div>
      </div>
    </section>
  );
}
