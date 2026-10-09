import type { ReactNode } from "react";
import { cx } from "@/lib/cx";

export type Tone = "neutral" | "good" | "warning" | "critical" | "water" | "brand";

const TONES: Record<Tone, string> = {
  neutral: "bg-canvas text-muted ring-line",
  good: "bg-mint text-primary-strong ring-fresh/40",
  warning: "bg-amber-soft text-amber ring-amber/25",
  critical: "bg-critical-soft text-critical ring-critical/25",
  water: "bg-water-soft text-water ring-water/25",
  brand: "bg-forest text-white ring-forest",
};

export function Badge({ tone = "neutral", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span className={cx("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-2xs font-bold ring-1 ring-inset", TONES[tone], className)}>
      {children}
    </span>
  );
}
