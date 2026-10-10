import { RefreshCw, Table2 } from "lucide-react";
import { useState } from "react";
import { DataState } from "@/components/feedback/DataState";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { useI18n } from "@/i18n";
import { formatNumber } from "@/lib/format";
import { TrendChart, useTrends, type TrendSeries } from "./TrendChart";

/** Month by month: reports, cases and harvest over the last year. */
export function TrendsPage() {
  const { t, lang } = useI18n();
  const trends = useTrends();
  const [table, setTable] = useState(false);

  const charts: { title: string; series: TrendSeries[] }[] = [
    {
      title: t("trends.reports"),
      series: [
        { key: "reports", label: t("trends.allReports"), color: "primary", kind: "bar" },
        { key: "severe_pests", label: t("trends.severePests"), color: "critical", kind: "line" },
        { key: "asset_faults", label: t("trends.assetFaults"), color: "amber", kind: "line" },
      ],
    },
    {
      title: t("trends.cases"),
      series: [
        { key: "cases_opened", label: t("monthly.opened"), color: "amber", kind: "bar" },
        { key: "cases_resolved", label: t("trends.resolved"), color: "fresh", kind: "bar" },
        { key: "grievances", label: t("nav.grievances"), color: "water", kind: "line" },
      ],
    },
    {
      title: t("trends.harvest"),
      series: [
        { key: "expected_tons", label: t("evaluation.expectedTons"), color: "water", kind: "bar" },
        { key: "reported_tons", label: t("evaluation.reportedTons"), color: "primary", kind: "bar" },
      ],
    },
  ];

  const columns = [
    ["reports", t("trends.allReports")], ["severe_pests", t("trends.severePests")], ["rain_readings", t("climate.readings")],
    ["rainfall_mm", t("climate.rainMonth")], ["asset_faults", t("trends.assetFaults")], ["grievances", t("nav.grievances")],
    ["cases_opened", t("monthly.opened")], ["cases_resolved", t("trends.resolved")], ["expected_tons", t("evaluation.expectedTons")],
    ["reported_tons", t("evaluation.reportedTons")], ["households", t("nutrition.households")], ["average_risk", t("nutrition.averageRisk")],
  ] as const;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("trends.eyebrow")}
        title={t("trends.title")}
        description={t("trends.description")}
        updatedAt={trends.dataUpdatedAt}
        actions={
          <>
            <Button icon={Table2} aria-pressed={table} onClick={() => setTable((value) => !value)}>{t("trends.table")}</Button>
            <Button icon={RefreshCw} onClick={() => void trends.refetch()} loading={trends.isFetching}>{t("filter.refresh")}</Button>
          </>
        }
      />
      {table ? (
        <Card className="overflow-x-auto">
          {trends.isPending ? <DataState kind="loading" /> : trends.error ? <DataState kind="error" message={trends.error.message} onRetry={() => void trends.refetch()} /> : (
            <table className="w-full min-w-[60rem] text-sm">
              <caption className="sr-only">{t("trends.title")}</caption>
              <thead className="bg-canvas text-left text-2xs uppercase tracking-wider text-muted">
                <tr>
                  <th scope="col" className="px-4 py-3">{t("trends.month")}</th>
                  {columns.map(([key, label]) => <th key={key} scope="col" className="px-3 py-3 text-right">{label}</th>)}
                </tr>
              </thead>
              <tbody>
                {trends.data.months.map((month) => (
                  <tr key={month.month} className="border-t border-line">
                    <th scope="row" className="px-4 py-2 text-left font-semibold">{month.label}</th>
                    {columns.map(([key]) => {
                      const value = month[key];
                      return <td key={key} className="px-3 py-2 text-right tabular-nums">{value === null ? "—" : formatNumber(value, lang)}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      ) : (
        <div className="grid gap-6 xl:grid-cols-2">
          {charts.map((chart) => (
            <Card key={chart.title}>
              <CardHeader title={chart.title} />
              <div className="p-5"><TrendChart series={chart.series} caption={chart.title} /></div>
            </Card>
          ))}
          <Card>
            <CardHeader title={t("climate.trend")} note={t("trends.rainNote")} />
            <div className="p-5">
              <TrendChart series={[{ key: "rainfall_mm", label: t("climate.rainMonth"), color: "water", kind: "bar" }, { key: "rain_readings", label: t("climate.readings"), color: "primary", kind: "line" }]} />
            </div>
          </Card>
        </div>
      )}
      <p className="text-xs text-muted">{t("trends.provenance")}</p>
    </div>
  );
}
