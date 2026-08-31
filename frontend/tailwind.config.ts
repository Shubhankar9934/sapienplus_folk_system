import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // World-blend editorial palette
        background: "oklch(0.965 0.003 200)",
        foreground: "oklch(0.18 0.02 250)",
        ink: {
          DEFAULT: "oklch(0.18 0.02 250)",
          soft: "#9fb0c0",
          dim: "#6b7d8f",
        },
        coral: {
          DEFAULT: "oklch(0.82 0.09 25)",
          strong: "oklch(0.72 0.16 25)",
        },
        nodata: "oklch(0.82 0.01 250)",
        purple: {
          DEFAULT: "oklch(0.52 0.13 300)",
          light: "oklch(0.62 0.11 300)",
        },
        charcoal: "oklch(0.24 0.01 250)",
        "editorial-black": "oklch(0.12 0.01 250)",
        card: {
          DEFAULT: "oklch(1 0 0)",
          foreground: "oklch(0.18 0.02 250)",
        },
        muted: {
          DEFAULT: "oklch(0.93 0.005 200)",
          foreground: "oklch(0.5 0.01 250)",
        },
        border: "oklch(0.88 0.005 200)",
        // FOLK dimension accent colors (kept from original)
        d1: "#5b8def",
        d2: "#e879a6",
        d3: "#f0b429",
        d4: "#34d399",
        accent: "#5b8def",
        pos: "#34d399",
        neg: "#f87171",
        warn: "#f0b429",
        // Legacy dark palette aliases (for existing pages)
        bg: {
          DEFAULT: "#0a0e14",
          soft: "#0f1620",
          "card": "#121b27",
          hover: "#1a2533",
        },
        line: "#1e2b3a",
      },
      fontFamily: {
        display: ["Anton", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["Inter", "var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.3s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
