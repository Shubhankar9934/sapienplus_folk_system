"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { CommandPalette } from "./CommandPalette";
import { SideMenu } from "./SideMenu";

export const NAV_ITEMS = [
  { label: "Home", href: "/" },
  { label: "FOLK Orientation", href: "/orientations" },
  { label: "Countries", href: "/countries" },
  { label: "Compare", href: "/compare" },
  { label: "Insights", href: "/insights" },
  { label: "Methodology", href: "/methodology" },
  { label: "Team", href: "/team" },
  { label: "About", href: "/about" },
];

export function NavBar() {
  const pathname = usePathname();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
      if (e.key === "Escape") {
        setPaletteOpen(false);
        setMenuOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      {/* World-blend style header bar */}
      <header className="relative z-40 mx-4 mt-4 flex h-16 items-center justify-between gap-4 rounded-md bg-white px-6 shadow-sm dark:mx-0 dark:mt-0 dark:rounded-none dark:bg-[#0E0E10] dark:shadow-none dark:border-b dark:border-white/[0.06] md:mx-8 md:px-10 dark:md:mx-0 dark:md:px-10">
        {/* Logo mark + wordmark */}
        <Link href="/" className="flex items-center gap-3 shrink-0">
          {/* Bar-chart logo mark */}
          <div className="flex items-end gap-[2px]">
            <span className="inline-block h-5 w-[6px] bg-ink dark:bg-white" />
            <span className="inline-block h-7 w-[6px] bg-ink dark:bg-white" />
            <span className="inline-block h-4 w-[6px] bg-coral-strong" />
            <span className="inline-block h-6 w-[6px] bg-ink dark:bg-white" />
          </div>
          <div className="font-display text-[10px] leading-[1.05] tracking-[0.08em] text-ink dark:text-white md:text-xs">
            FOLK
            <br />
            CULTURAL INTELLIGENCE
          </div>
        </Link>

        {/* Center: Main Navigation Menu Items */}
        <nav className="hidden lg:flex items-center gap-6 xl:gap-8 text-sm font-medium">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname?.startsWith(item.href);

            return (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  "relative py-1.5 transition-colors duration-200",
                  isActive
                    ? "font-semibold text-ink dark:text-white"
                    : "text-muted-foreground hover:text-ink dark:text-white/60 dark:hover:text-white"
                )}
              >
                {item.label}
                {/* Active Underline Indicator */}
                {isActive && (
                  <span className="absolute bottom-0 left-0 right-0 h-[2px] rounded-full bg-ink dark:bg-white" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Right side: search + hamburger */}
        <div className="flex items-center gap-3 shrink-0">
          {/* Quick search */}
          <button
            onClick={() => setPaletteOpen(true)}
            className={cn(
              "hidden items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground transition hover:border-ink/30 dark:border-white/15 dark:text-white/50 dark:hover:border-white/30 md:flex",
            )}
          >
            <Search className="h-3.5 w-3.5" />
            <span>Search</span>
            <kbd className="text-[10px] border border-border rounded px-1 dark:border-white/15">
              ⌘K
            </kbd>
          </button>

          {/* Hamburger → opens SideMenu */}
          <button
            aria-label="Open menu"
            onClick={() => setMenuOpen(true)}
            className="flex h-10 w-10 flex-col items-center justify-center gap-[5px] rounded-sm bg-ink transition hover:opacity-90 dark:bg-white"
          >
            <span className="block h-[2px] w-5 bg-white dark:bg-[#141518]" />
            <span className="block h-[2px] w-5 bg-white dark:bg-[#141518]" />
            <span className="block h-[2px] w-5 bg-white dark:bg-[#141518]" />
          </button>
        </div>
      </header>

      <SideMenu open={menuOpen} onClose={() => setMenuOpen(false)} />
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
      />
    </>
  );
}
