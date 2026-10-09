import { lazy, Suspense } from "react";
import { DataState } from "@/components/feedback/DataState";
import { Card, CardHeader } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { SourceBadge } from "@/components/ui/SourceBadge";
import { useI18n } from "@/i18n";
import { formatNumber } from "@/lib/format";
import { tokenColor } from "@/lib/tokens";
import type { ChartRow } from "@/components/charts/SchemeChart";
import type { Metric, SchemeRow } from "@/services/api/schemas";

// Recharts is large: load the chart only when this card renders.
const SchemeChart = lazy(() => import("@/components/charts/SchemeChart"));

function YieldFigure({ metric }: { metric: Metric }) {
  const { lang, t } = useI18n();
  return (
    <div className="rounded-control bg-canvas px-3 py-2.5">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <p className="text-2xs font-bold uppercase tracking-wider text-muted">{metric.label}</p>
        <SourceBadge source={metric.source} />
      </div>
      <p className="mt-0.5 font-heading text-lg font-extrabold text-forest">
        {metric.value === null ? (
          <span className="text-sm font-bold text-muted">{t("metric.noValue")}</span>
        ) : (
          <>
            {formatNumber(metric.value, lang)}
            <span className="ml-1 text-xs font-semibold text-muted">{metric.unit}</span>
          </>
        )}
      </p>
      {metric.note && <p className="mt-1 text-xs leading-relaxed text-muted">{metric.note}</p>}
    </div>
  );
}

export function SchemeComparison({ schemes }: { schemes: SchemeRow[] }) {
  const { t } = useI18n();
  const data: ChartRow[] = schemes.map((scheme) => ({
    name: scheme.name,
    [t("scheme.reports")]: scheme.reports,
    [t("scheme.pests")]: scheme.pest_alerts,
    [t("scheme.assetsDown")]: scheme.assets_down,
    [t("scheme.grievances")]: scheme.open_grievances,
  }));
  const series = [
    { key: t("scheme.reports"), color: tokenColor("primary") },
    { key: t("scheme.pests"), color: tokenColor("amber") },
    { key: t("scheme.assetsDown"), color: tokenColor("critical") },
    { key: t("scheme.grievances"), color: tokenColor("water") },
  ];

  return (
    <Card aria-labelledby="schemes-title">
      <CardHeader id="schemes-title" title={t("section.schemes")} note={t("section.schemesNote")} />
      {schemes.length === 0 ? (
        <DataState kind="empty" message={t("section.schemesEmpty")} />
      ) : (
        <div className="space-y-5 p-5">
          <Suspense fallback={<Skeleton className="h-56 w-full" />}>
            <SchemeChart data={data} series={series} caption={t("scheme.chartTitle")} schemeLabel={t("filter.scheme")} />
          </Suspense>

          <div className="grid gap-4 md:grid-cols-2">
            {schemes.map((scheme) => (
              <article key={scheme.scheme_id} className="rounded-card border border-line p-4">
                <header className="mb-3">
                  <h3 className="text-base font-bold">{scheme.name}</h3>
                  <p className="text-xs text-muted">
                    {[scheme.implementing_partner, scheme.hectares_developed ? `${scheme.hectares_developed} ha` : null].filter(Boolean).join(" · ")}
                  </p>
                </header>
                <div className="grid gap-2">
                  <YieldFigure metric={scheme.reported_harvest} />
                  <YieldFigure metric={scheme.yield_target} />
                  <YieldFigure metric={scheme.yield_achievement} />
                </div>
              </article>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
