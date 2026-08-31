"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export interface TabItem {
  id: string;
  label: string;
}

export function Tabs({
  tabs,
  children,
  initial,
}: {
  tabs: TabItem[];
  children: (active: string) => React.ReactNode;
  initial?: string;
}) {
  const [active, setActive] = useState(initial ?? tabs[0]?.id);

  return (
    <div>
      <div className="flex gap-1 border-b border-line overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActive(t.id)}
            className={cn(
              "relative px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors",
              active === t.id ? "text-ink" : "text-ink-dim hover:text-ink-soft",
            )}
          >
            {t.label}
            {active === t.id && (
              <motion.div
                layoutId="tab-underline"
                className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-accent"
              />
            )}
          </button>
        ))}
      </div>
      <div className="pt-6 animate-fade-in">{children(active)}</div>
    </div>
  );
}
