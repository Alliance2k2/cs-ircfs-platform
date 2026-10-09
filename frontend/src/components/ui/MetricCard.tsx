import { Info, type LucideIcon } from "lucide-react";
import { useId, useState } from "react";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";
import { formatNumber, withUnit } from "@/lib/format";
import type { Metric } from "@/services/api/schemas";
import { SourceBadge } from "./SourceBadge";

export type Accent = "green" | "blue" | "gold" | "coral" | "violet" | "teal";

interface MetricCardProps {
  metric: Metric;
  icon?: LucideIcon;
  accent?: Accent;
}

/**
 * One headline figure with everything needed to read it honestly: unit, period, source,
 * an optional note, and the definition behind an accessible disclosure.
 */
export function MetricCard({ metric, icon: Icon, accent = "green" }: MetricCardProps) {
  const { t, lang } = useI18n();
  const [open, setOpen] = useState(false);
  const definitionId = useId();
  const shown = metric.value === null ? null : withUnit(formatNumber(metric.value, lang), metric.unit);

  return (
    <article
      className={cx(
        "flex min-h-[11rem] min-w-0 flex-col rounded-[20px] border border-line bg-surface p-4 shadow-card transition-shadow hover:shadow-raised sm:p-5",
        `wash-${accent}`,
      )}
      aria-label={metric.label}
    >
      <div className="flex items-start justify-between gap-2">
        {Icon && (
          <span aria-hidden className={cx("tile h-11 w-11", `tile-${accent}`)}>
            <Icon className="h-5 w-5" />
          </span>
        )}
        <button
          type="button"
          className="-m-1 ml-auto rounded-full p-1 text-muted hover:bg-canvas hover:text-forest"
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

      <h3 className={cx("text-sm font-semibold text-muted", Icon ? "mt-3.5" : "-mt-5 pr-6")}>{metric.label}</h3>
      <p className="mt-1 flex items-baseline gap-1.5">
        {shown ? (
          <>
            <span className="tabular font-heading text-2xl font-extrabold tracking-tight text-forest sm:text-[2rem]">{shown.value}</span>
            {shown.unit && <span className="text-sm font-semibold text-muted">{shown.unit}</span>}
          </>
        ) : (
          <span className="font-heading text-xl font-bold text-muted">{t("metric.noValue")}</span>
        )}
      </p>
      {metric.note && <p className="mt-0.5 text-xs text-muted">{metric.note}</p>}

      <div className="mt-auto flex flex-wrap items-center gap-x-2 gap-y-1 pt-3">
        <SourceBadge source={metric.source} />
        <span className="text-2xs text-muted">{metric.period}</span>
      </div>
      <p id={definitionId} hidden={!open} className="mt-3 rounded-control bg-canvas p-3 text-xs leading-relaxed text-ink">
        {metric.definition}
      </p>
    </article>
  );
}
