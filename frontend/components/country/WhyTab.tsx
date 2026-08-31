"use client";

import { EmptyState } from "@/components/ui";
import type { CountryProfile, Observation } from "@/lib/api";

function Hairline() {
  return <div className="h-px w-full bg-ink/10 dark:bg-white/8" />;
}

function EditorialHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-display text-[1.6rem] uppercase leading-[0.9] tracking-[-0.01em] text-ink dark:text-white">
      {children}
    </h2>
  );
}

function BulletRow({ text }: { text: string }) {
  return (
    <li className="flex items-start gap-3 text-[13px] leading-relaxed text-ink/70 dark:text-white/60">
      <span className="mt-[0.4em] h-1 w-1 shrink-0 rounded-full bg-coral-strong dark:bg-[#E14B3C]" />
      <span>{text}</span>
    </li>
  );
}

function DriverRow({ d }: { d: Observation }) {
  return <BulletRow text={d.text} />;
}

function CompetingForces({ profile }: { profile: CountryProfile }) {
  const forces = profile.competing_forces ?? [];
  if (forces.length === 0) return null;
  return (
    <div>
      <EditorialHeading>Competing cultural forces</EditorialHeading>
      <p className="mt-1 text-[11px] text-ink/40 dark:text-white/30">
        Tensions that shape everyday choices
      </p>
      <Hairline />
      <div className="mt-0 divide-y divide-ink/8 dark:divide-white/8">
        {forces.map((f, i) => (
          <div
            key={i}
            className="grid grid-cols-[1fr_auto_1fr] items-start gap-6 py-5"
          >
            <p className="text-[13px] leading-relaxed text-ink/75 dark:text-white/65">
              {f.pulls_toward}
            </p>
            <span className="pt-0.5 text-[9px] font-bold uppercase tracking-[0.14em] text-ink/25 dark:text-white/20">
              but
            </span>
            <p className="text-right text-[13px] leading-relaxed text-ink/75 dark:text-white/65">
              {f.but_also}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function WhyTab({ profile }: { profile: CountryProfile }) {
  const drivers = profile.historical_drivers ?? [];
  const hasContent =
    drivers.length > 0 || (profile.competing_forces ?? []).length > 0;

  if (!hasContent) {
    return (
      <EmptyState
        title="Not enough evidence yet"
        message={`No grounded historical drivers were found for ${profile.country}.`}
      />
    );
  }

  return (
    <div className="space-y-14">
      {/* Why it became this way */}
      {drivers.length > 0 && (
        <div>
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-[220px_1fr]">
            {/* Left — sticky label */}
            <div className="lg:sticky lg:top-8 lg:self-start">
              <p className="text-[9px] font-bold uppercase tracking-[0.26em] text-coral-strong dark:text-[#E14B3C]">
                Historical drivers
              </p>
              <EditorialHeading>
                Why it became
                <br />
                this way
              </EditorialHeading>
              <p className="mt-2 text-[11px] leading-relaxed text-ink/45 dark:text-white/35">
                Geography, trade and the last century of state-building explain
                most of the placement.
              </p>
            </div>

            {/* Right — driver rows */}
            <div>
              <Hairline />
              <ul className="divide-y divide-ink/8 dark:divide-white/8">
                {drivers.map((d, i) => (
                  <li key={i} className="py-4">
                    <DriverRow d={d} />
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      <CompetingForces profile={profile} />
    </div>
  );
}
