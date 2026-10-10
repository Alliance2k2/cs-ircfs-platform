import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";
import { formatNumber } from "@/lib/format";

export interface BarItem {
  label: string;
  value: number;
  /** A second figure shown after the value, e.g. "of 12". */
  note?: string;
}

const TONES = { primary: "bg-primary", water: "bg-water", amber: "bg-amber", critical: "bg-critical" } as const;

/** Ranked horizontal bars as a plain list: readable by screen readers and on any phone. */
export function BarList({ items, tone = "primary", unit = "", empty }: { items: BarItem[]; tone?: keyof typeof TONES; unit?: string; empty: string }) {
  const { lang } = useI18n();
  if (!items.length) return <p className="py-4 text-sm text-muted">{empty}</p>;
  const max = Math.max(...items.map((item) => item.value), 1);
  return (
    <ul className="space-y-2.5">
      {items.map((item) => (
        <li key={item.label} className="text-sm">
          <div className="flex items-baseline justify-between gap-3">
            <span className="min-w-0 truncate text-ink">{item.label}</span>
            <span className="shrink-0 font-semibold tabular-nums">
              {formatNumber(item.value, lang)}{unit && ` ${unit}`}
              {item.note && <span className="ml-1 text-xs font-normal text-muted">{item.note}</span>}
            </span>
          </div>
          <div aria-hidden className="mt-1 h-2 rounded-full bg-canvas">
            <div className={cx("h-2 rounded-full", TONES[tone])} style={{ width: `${Math.max((item.value / max) * 100, 2)}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

/** Count rows by a key, largest first. */
export function tally<T>(rows: T[], key: (row: T) => string | null, value: (row: T) => number = () => 1): BarItem[] {
  const totals = new Map<string, number>();
  rows.forEach((row) => {
    const name = key(row);
    if (name) totals.set(name, (totals.get(name) ?? 0) + value(row));
  });
  return [...totals.entries()].map(([label, total]) => ({ label, value: Math.round(total * 10) / 10 })).sort((a, b) => b.value - a.value);
}
