import { Info } from "lucide-react";
import { useId, useState } from "react";
import { useI18n } from "@/i18n";
import { formatNumber, withUnit } from "@/lib/format";
import type { Metric } from "@/services/api/schemas";
import { SourceBadge } from "./SourceBadge";

/**
 * One headline figure with everything needed to read it honestly: unit, period, source,
 * an optional note, and the definition behind an accessible disclosure.
 */
export function MetricCard({ metric }: { metric: Metric }) {
  const { t, lang } = useI18n();
  const [open, setOpen] = useState(false);
  const definitionId = useId();
  const shown = metric.value === null ? null : withUnit(formatNumber(metric.value, lang), metric.unit);

  return (
    <article className="flex min-h-[9.5rem] min-w-0 flex-col rounded-card border border-line bg-surface p-3 shadow-card sm:p-4" aria-label={metric.label}>
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-muted">{metric.label}</h3>
        <button
          type="button"
          className="-m-1 rounded-full p-1 text-muted hover:bg-canvas hover:text-forest"
          aria-expanded={open}
          aria-controls={definitionId}
          onClick={() => setOpen((value) => !value)}
        >
          <Info aria-hidden className="h-4 w-4" />
          <span className="sr-only">
            {t("metric.definition")}: {metric.label}
          </span>
        </button>
      </div>

      <p className="mt-2 flex items-baseline gap-1.5">
        {shown ? (
          <>
            <span className="tabular font-heading text-2xl font-extrabold tracking-tight text-forest sm:text-3xl">{shown.value}</span>
            {shown.unit && <span className="text-sm font-semibold text-muted">{shown.unit}</span>}
          </>
        ) : (
          <span className="font-heading text-xl font-bold text-muted">{t("metric.noValue")}</span>
        )}
      </p>
      {metric.note && <p className="mt-1 text-xs text-muted">{metric.note}</p>}

      <div className="mt-auto flex flex-wrap items-center gap-2 pt-3">
        <SourceBadge source={metric.source} />
        <span className="text-2xs text-muted">{metric.period}</span>
      </div>
      <p id={definitionId} hidden={!open} className="mt-3 rounded-control bg-canvas p-3 text-xs leading-relaxed text-ink">
        {metric.definition}
      </p>
    </article>
  );
}
