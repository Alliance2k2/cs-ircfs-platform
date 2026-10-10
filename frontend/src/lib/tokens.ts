/** Fallbacks match src/styles/tokens.css, for environments without computed styles (tests). */
const FALLBACK: Record<string, string> = {
  forest: "6 78 59",
  primary: "8 127 91",
  fresh: "66 184 131",
  mint: "223 244 231",
  muted: "92 112 102",
  line: "223 232 225",
  amber: "146 94 8",
  critical: "190 58 52",
  water: "26 104 142",
};

/**
 * A design token as a colour string for libraries that write SVG attributes
 * (Recharts, Mapbox GL), where CSS variables do not resolve.
 */
export function tokenColor(name: keyof typeof FALLBACK | string, alpha = 1): string {
  let channels = "";
  try {
    channels = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim();
  } catch {
    channels = "";
  }
  // Comma syntax on purpose: Mapbox GL rejects the space-separated rgb() form.
  const [r, g, b] = (channels || FALLBACK[name] || FALLBACK.muted!).split(/\s+/);
  return alpha === 1 ? `rgb(${r}, ${g}, ${b})` : `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
