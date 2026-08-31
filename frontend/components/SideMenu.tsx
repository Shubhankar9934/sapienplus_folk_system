"use client";

import { useEffect, useRef } from "react";
import { Moon, Sun, X } from "lucide-react";
import { useTheme } from "@/hooks/use-theme";
import { useRouter } from "next/navigation";
import gsap from "gsap";

const NAV_ITEMS = [
  { label: "HOME", href: "/" },
  { label: "FOLK ORIENTATION", href: "/orientations" },
  { label: "COUNTRIES", href: "/countries" },
  { label: "COMPARE", href: "/compare" },
  { label: "INSIGHTS", href: "/insights" },
  { label: "METHODOLOGY", href: "/methodology" },
  { label: "TEAM", href: "/team" },
  { label: "ABOUT", href: "/about" },
];

interface SideMenuProps {
  open: boolean;
  onClose: () => void;
}

export function SideMenu({ open, onClose }: SideMenuProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const itemsRef = useRef<HTMLLIElement[]>([]);
  const { theme, toggle } = useTheme();
  const router = useRouter();

  const setItemRef = (el: HTMLLIElement | null, i: number) => {
    if (el) itemsRef.current[i] = el;
  };

  // Initial hidden state (runs once)
  useEffect(() => {
    if (!panelRef.current || !overlayRef.current) return;
    gsap.set(panelRef.current, { xPercent: 100 });
    gsap.set(overlayRef.current, { opacity: 0 });
    gsap.set(itemsRef.current, { x: 60, opacity: 0 });
  }, []);

  useEffect(() => {
    if (!panelRef.current || !overlayRef.current) return;
    const wrapper = panelRef.current.parentElement;
    gsap.killTweensOf([panelRef.current, overlayRef.current, ...itemsRef.current]);

    if (open) {
      if (wrapper) gsap.set(wrapper, { pointerEvents: "auto" });
      const tl = gsap.timeline();
      tl.to(overlayRef.current, { opacity: 1, duration: 0.3, ease: "power2.out" }, 0)
        .to(panelRef.current, { xPercent: 0, duration: 0.55, ease: "power4.out" }, 0)
        .to(
          itemsRef.current,
          { x: 0, opacity: 1, duration: 0.5, stagger: 0.08, ease: "power3.out" },
          0.25,
        );
    } else {
      const tl = gsap.timeline({
        onComplete: () => {
          if (wrapper) gsap.set(wrapper, { pointerEvents: "none" });
        },
      });
      tl.to(
        [...itemsRef.current].reverse(),
        { x: 60, opacity: 0, duration: 0.3, stagger: 0.05, ease: "power2.in" },
        0,
      )
        .to(panelRef.current, { xPercent: 100, duration: 0.45, ease: "power4.in" }, 0.15)
        .to(overlayRef.current, { opacity: 0, duration: 0.3, ease: "power2.in" }, 0.15);
    }
  }, [open]);

  const handleNavClick = (href: string) => {
    onClose();
    router.push(href);
  };

  return (
    <div
      className="fixed inset-0 z-50"
      style={{ pointerEvents: "none" }}
      aria-hidden={!open}
    >
      <div
        ref={overlayRef}
        onClick={onClose}
        className="absolute inset-0 bg-ink/50"
        style={{ opacity: 0 }}
      />
      <aside
        ref={panelRef}
        className="absolute right-0 top-0 h-full w-full bg-ink shadow-2xl md:w-1/2 dark:bg-[#0E0E10]"
      >
        <div className="flex h-16 items-center justify-end gap-3 px-6 md:px-10">
          <button
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            onClick={toggle}
            className="flex h-10 items-center gap-2 rounded-sm border border-white/25 px-3 text-xs uppercase tracking-[0.2em] text-white transition hover:border-white/60"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            <span>{theme === "dark" ? "Light" : "Dark"}</span>
          </button>
          <button
            aria-label="Close menu"
            onClick={onClose}
            className="flex h-10 w-10 items-center justify-center rounded-sm bg-white text-ink transition hover:opacity-90"
          >
            <X className="h-5 w-5" strokeWidth={2.5} />
          </button>
        </div>
        <nav className="px-8 pt-8 md:px-16 md:pt-16">
          <ul className="flex flex-col gap-6 md:gap-8">
            {NAV_ITEMS.map((item, i) => (
              <li
                key={item.label}
                ref={(el) => setItemRef(el, i)}
                className="font-display text-3xl leading-none tracking-tight text-white md:text-5xl"
              >
                <button
                  onClick={() => handleNavClick(item.href)}
                  className="inline-block transition-colors hover:text-coral-strong"
                >
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
    </div>
  );
}
