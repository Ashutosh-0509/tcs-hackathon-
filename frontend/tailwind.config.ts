import type { Config } from "tailwindcss";

/**
 * TrustLens design tokens. Deliberately monochrome + warm paper, with semantic
 * colour reserved for reliability state only. No "AI blue".
 */
const config: Config = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        raised: "var(--raised)",
        line: "var(--line)",
        ink: "var(--ink)",
        "ink-soft": "var(--ink-soft)",
        "ink-faint": "var(--ink-faint)",
        certain: { DEFAULT: "var(--certain)", tint: "var(--certain-tint)", line: "var(--certain-line)" },
        caution: { DEFAULT: "var(--caution)", tint: "var(--caution-tint)", line: "var(--caution-line)" },
        alert: { DEFAULT: "var(--alert)", tint: "var(--alert-tint)", line: "var(--alert-line)" },
      },
      fontFamily: {
        sans: [
          "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto",
          "Helvetica Neue", "Arial", "sans-serif",
        ],
        mono: [
          "ui-monospace", "SFMono-Regular", "Menlo", "Consolas",
          "Liberation Mono", "monospace",
        ],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem", letterSpacing: "0.04em" }],
      },
      borderRadius: { card: "12px", control: "9px" },
      boxShadow: {
        card: "0 1px 2px rgba(20,18,15,0.04), 0 1px 3px rgba(20,18,15,0.03)",
        pop: "0 8px 30px rgba(20,18,15,0.10)",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: { "fade-up": "fade-up 0.28s cubic-bezier(0.2,0.6,0.2,1) both" },
    },
  },
  plugins: [],
};

export default config;
