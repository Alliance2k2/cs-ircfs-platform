import { lazy, Suspense } from "react";
import { DataState } from "@/components/feedback/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { useI18n } from "@/i18n";
import { useApi } from "@/services/api/hooks";
import { trendsSchema } from "@/services/api/workspaces";
import type { TrendSeries } from "./TrendChartView";

const TrendChartView = lazy(() => import("./TrendChartView"));

export type { TrendSeries };

/** The last twelve months for a few series. One request, shared by every page that shows trends. */
export function useTrends() {
  return useApi("analytics/trends", trendsSchema, { staleTime: 5 * 60_000 });
}

export function TrendChart({ series, caption }: { series: TrendSeries[]; caption?: string }) {
  const { t } = useI18n();
  const trends = useTrends();
  if (trends.isPending) return <Skeleton className="h-64 w-full" />;
  if (trends.error) return <DataState kind="error" compact message={trends.error.message} onRetry={() => void trends.refetch()} />;
  const empty = trends.data.months.every((month) => series.every((item) => !month[item.key]));
  if (empty) return <DataState kind="empty" compact message={t("trends.empty")} />;
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <TrendChartView months={trends.data.months} series={series} caption={caption ?? series.map((item) => item.label).join(", ")} monthLabel={t("trends.month")} />
    </Suspense>
  );
}
