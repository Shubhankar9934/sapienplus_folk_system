"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { useCountries } from "@/lib/api";
import { flagEmoji } from "@/lib/utils";

export function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const { data: countries } = useCountries();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);

  const results = useMemo(() => {
    const list = countries ?? [];
    if (!q.trim()) return list.slice(0, 8);
    const term = q.toLowerCase();
    return list
      .filter(
        (c) =>
          c.country.toLowerCase().includes(term) ||
          c.iso3.toLowerCase().includes(term)
      )
      .slice(0, 10);
  }, [countries, q]);

  useEffect(() => {
    setActive(0);
  }, [q]);

  useEffect(() => {
    if (!open) setQ("");
  }, [open]);

  function go(iso3: string) {
    onClose();
    router.push(`/country/${iso3}`);
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 backdrop-blur-sm pt-[15vh] px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl rounded-xl border border-line bg-bg-card shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-line px-4">
          <Search className="h-4 w-4 text-ink-dim" />
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown")
                setActive((a) => Math.min(a + 1, results.length - 1));
              if (e.key === "ArrowUp") setActive((a) => Math.max(a - 1, 0));
              if (e.key === "Enter" && results[active]) go(results[active].iso3);
            }}
            placeholder="Search countries (e.g. South Korea, KOR)..."
            className="flex-1 bg-transparent py-3.5 text-sm text-ink outline-none placeholder:text-ink-dim"
          />
          <kbd className="text-[10px] text-ink-dim border border-line rounded px-1.5 py-0.5">
            ESC
          </kbd>
        </div>
        <ul className="max-h-80 overflow-y-auto p-2">
          {results.length === 0 && (
            <li className="px-3 py-4 text-sm text-ink-dim">No countries found.</li>
          )}
          {results.map((c, i) => (
            <li key={c.iso3}>
              <button
                onMouseEnter={() => setActive(i)}
                onClick={() => go(c.iso3)}
                className={`flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left text-sm ${
                  i === active ? "bg-bg-hover" : ""
                }`}
              >
                <span className="flex items-center gap-3">
                  <span className="text-lg">{flagEmoji(c.iso3)}</span>
                  <span className="text-ink">{c.country}</span>
                  <span className="text-xs text-ink-dim">{c.iso3}</span>
                </span>
                {c.archetype && (
                  <span className="text-xs text-ink-dim">{c.archetype}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
