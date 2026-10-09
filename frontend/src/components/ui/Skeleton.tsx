import { cx } from "@/lib/cx";

/** A quiet placeholder block while data loads (no fake numbers). */
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cx("animate-pulse rounded-control bg-line/60", className)} />;
}
