import { FlaskConical } from "lucide-react";
import { DataState } from "@/components/feedback/DataState";
import { MetricCard } from "@/components/ui/MetricCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { useI18n } from "@/i18n";
import { ApiError } from "@/services/api/client";
import { AssetHealth } from "./AssetHealth";
import { FilterBar } from "./FilterBar";
import { METRIC_STYLE } from "./metricStyle";
import { ModuleGrid } from "./ModuleGrid";
import { OverviewHero } from "./OverviewHero";
import { PriorityActions } from "./PriorityActions";
import { RainfallPanel } from "./RainfallPanel";
import { RecentReports } from "./RecentReports";
import { SchemeComparison } from "./SchemeComparison";
import { useOverview, useOverviewFilters } from "./useOverview";

function LoadingGrid() {
  return (
    <div className="space-y-6" aria-hidden>
      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        {Array.from({ length: 8 }, (_, index) => (
          <Skeleton key={index} className="h-[11rem]" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-12">
        <Skeleton className="h-72 lg:col-span-7" />
        <Skeleton className="h-72 lg:col-span-5" />
      </div>
    </div>
  );
}

/**
 * The District Planning Dashboard's first screen. Top to bottom it answers: what is
 * happening, what needs a decision today, how the schemes compare, where the water risk
 * is, and what the field said last.
 */
export function OverviewPage() {
  const { t } = useI18n();
  const [filters, setFilters] = useOverviewFilters();
  const overview = useOverview(filters);
  const data = overview.data;

  return (
    <div className="space-y-6">
      <OverviewHero data={data} />

      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4 rounded-[20px] border border-line bg-surface px-4 py-4 shadow-card sm:px-5">
        <div className="max-w-xl">
          <h2 className="text-lg font-extrabold">{t("overview.title")}</h2>
          <p className="mt-0.5 text-sm text-muted">{t("overview.subtitle")}</p>
        </div>
        <FilterBar
          filters={filters}
          onChange={setFilters}
          onRefresh={() => overview.refetch()}
          refreshing={overview.isFetching}
          updatedAt={overview.dataUpdatedAt}
        />
      </div>

      {data?.demo_mode && (
        <p role="note" className="flex items-start gap-2.5 rounded-card border border-amber/30 bg-amber-soft px-4 py-3 text-sm font-semibold text-amber">
          <FlaskConical aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
          {t("banner.demo")}
        </p>
      )}

      {overview.isPending ? (
        <LoadingGrid />
      ) : overview.isError && !data ? (
        <DataState
          kind={overview.error instanceof ApiError && overview.error.unreachable ? "unreachable" : "error"}
          message={overview.error.message}
          onRetry={() => overview.refetch()}
        />
      ) : data ? (
        <>
          <section aria-label={t("overview.title")} className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
            {data.metrics.map((metric) => (
              <MetricCard key={metric.key} metric={metric} icon={METRIC_STYLE[metric.key]?.icon} accent={METRIC_STYLE[metric.key]?.accent} />
            ))}
          </section>

          <div className="grid gap-6 lg:grid-cols-12">
            <div className="lg:col-span-7">
              <PriorityActions actions={data.priority_actions} />
            </div>
            <div className="lg:col-span-5">
              <AssetHealth assets={data.assets} schemes={data.schemes} />
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-12">
            <div className="lg:col-span-7">
              <SchemeComparison schemes={data.schemes} />
            </div>
            <div className="lg:col-span-5">
              <RainfallPanel rows={data.rainfall} />
            </div>
          </div>

          <RecentReports reports={data.recent_reports} />

          <ModuleGrid data={data} />
        </>
      ) : null}
    </div>
  );
}
