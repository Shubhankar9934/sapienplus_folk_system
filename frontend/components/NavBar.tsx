"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Globe2, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { CommandPalette } from "./CommandPalette";

const LINKS = [
  { href: "/explore", label: "Explore" },
  { href: "/compare", label: "Compare" },
  { href: "/world-rankings", label: "Rankings" },
];

export function NavBar() {
  const pathname = usePathname();
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
      if (e.key === "Escape") setPaletteOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-line bg-bg/80 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <Globe2 className="h-5 w-5 text-accent" />
            <span className="text-ink">FOLK</span>
            <span className="hidden sm:inline text-ink-dim font-normal">
              Cultural Intelligence
            </span>
          </Link>

          <nav className="flex items-center gap-1">
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-sm transition-colors",
                  pathname?.startsWith(l.href)
                    ? "text-ink bg-bg-hover"
                    : "text-ink-soft hover:text-ink"
                )}
              >
                {l.label}
              </Link>
            ))}
            <button
              onClick={() => setPaletteOpen(true)}
              className="ml-2 flex items-center gap-2 rounded-lg border border-line px-3 py-1.5 text-sm text-ink-dim hover:text-ink-soft"
            >
              <Search className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Search</span>
              <kbd className="hidden sm:inline text-[10px] border border-line rounded px-1">
                Ctrl K
              </kbd>
            </button>
          </nav>
        </div>
      </header>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </>
  );
}
