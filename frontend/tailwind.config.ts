import type { Config } from "tailwindcss";

// Every colour is a semantic token from src/styles/tokens.css, so components never
// hard-code a hex value and the palette can change in one place.
const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        forest: { DEFAULT: token("forest"), light: token("forest-light"), deep: token("forest-deep") },
        primary: { DEFAULT: token("primary"), strong: token("primary-strong") },
        fresh: token("fresh"),
        mint: token("mint"),
        lime: token("lime"),
        canvas: token("canvas"),
        surface: token("surface"),
        ink: token("ink"),
        muted: token("muted"),
        line: token("line"),
        amber: { DEFAULT: token("amber"), soft: token("amber-soft") },
        critical: { DEFAULT: token("critical"), soft: token("critical-soft") },
        water: { DEFAULT: token("water"), soft: token("water-soft") },
        violet: { DEFAULT: token("violet"), soft: token("violet-soft") },
        teal: { DEFAULT: token("teal"), soft: token("teal-soft") },
      },
      fontFamily: {
        sans: ["DM Sans", "Segoe UI", "system-ui", "sans-serif"],
        heading: ["Manrope", "DM Sans", "Segoe UI", "system-ui", "sans-serif"],
      },
      borderRadius: { card: "var(--radius-card)", control: "var(--radius-control)" },
      boxShadow: { card: "var(--shadow-card)", raised: "var(--shadow-raised)" },
      fontSize: { "2xs": ["0.6875rem", { lineHeight: "1rem" }] },
    },
  },
  plugins: [],
} satisfies Config;
