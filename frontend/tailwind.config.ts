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
        // Bloomberg-terminal inspired dark palette.
        bg: {
          DEFAULT: "#0a0e14",
          soft: "#0f1620",
          card: "#121b27",
          hover: "#1a2533",
        },
        line: "#1e2b3a",
        ink: {
          DEFAULT: "#e6edf3",
          soft: "#9fb0c0",
          dim: "#6b7d8f",
        },
        // Dimension accent colors.
        d1: "#5b8def",
        d2: "#e879a6",
        d3: "#f0b429",
        d4: "#34d399",
        accent: "#5b8def",
        pos: "#34d399",
        neg: "#f87171",
        warn: "#f0b429",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
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
