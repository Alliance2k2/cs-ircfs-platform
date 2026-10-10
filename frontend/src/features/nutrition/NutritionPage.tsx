import { EyeOff, RefreshCw, ShieldCheck } from "lucide-react";
import { DataTable, type Column } from "@/components/data/DataTable";
import { DataState } from "@/components/feedback/DataState";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { TrendChart } from "@/features/trends/TrendChart";
import { useI18n } from "@/i18n";
import { formatNumber } from "@/lib/format";
import { useApi } from "@/services/api/hooks";
import { nutritionSchema } from "@/services/api/workspaces";
import type { z } from "zod";

type CellRow = z.infer<typeof nutritionSchema>["by_cell"][number];

/** Household screening by cell. Cells with too few households show no scores, so no family can be singled out. */
export function NutritionPage() {
  const { t, lang } = useI18n();
  const summary = useApi("analytics/nutrition-summary", nutritionSchema);
  const data = summary.data;
  const share = (value: number) => (data?.households ? ` (${Math.round((value / data.households) * 100)}%)` : "");

  const columns: Column<CellRow>[] = [
    { key: "cell", header: t("nutrition.cell"), primary: true, render: (row) => <span className="font-semibold">{row.cell}</span>, sortValue: (row) => row.cell },
    { key: "households", header: t("nutrition.households"), render: (row) => row.households, sortValue: (row) => row.households },
    {
      key: "risk",
      header: t("nutrition.averageRisk"),
      sortValue: (row) => row.average_risk,
      render: (row) =>
        row.suppressed ? (
          <span className="inline-flex items-center gap-1.5 text-xs text-muted"><EyeOff aria-hidden className="h-3.5 w-3.5" />{t("nutrition.hidden")}</span>
        ) : (
          <Badge tone={(row.average_risk ?? 0) >= 3.5 ? "critical" : (row.average_risk ?? 0) >= 2.5 ? "warning" : "good"}>
            {row.average_risk === null ? "—" : formatNumber(row.average_risk, lang)} / 5
          </Badge>
        ),
    },
    { key: "high", header: t("nutrition.highRisk"), sortValue: (row) => row.high_risk, render: (row) => (row.suppressed ? "—" : row.high_risk ?? "—") },
  ];

  const stats = data
    ? [
        { label: t("nutrition.households"), value: String(data.households) },
        { label: t("nutrition.averageRisk"), value: data.average_risk === null ? "—" : `${formatNumber(data.average_risk, lang)} / 5` },
        { label: t("nutrition.highRisk"), value: `${data.high_risk_households}${share(data.high_risk_households)}` },
        { label: t("nutrition.oneMeal"), value: `${data.one_meal_households}${share(data.one_meal_households)}` },
        { label: t("nutrition.insufficient"), value: `${data.food_insufficient}${share(data.food_insufficient)}` },
      ]
    : [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("nutrition.eyebrow")}
        title={t("nutrition.title")}
        description={t("nutrition.description")}
        updatedAt={summary.dataUpdatedAt}
        actions={<Button icon={RefreshCw} onClick={() => void summary.refetch()} loading={summary.isFetching}>{t("filter.refresh")}</Button>}
      />
      {summary.isPending ? (
        <DataState kind="loading" />
      ) : summary.error ? (
        <DataState kind="error" message={summary.error.message} onRetry={() => void summary.refetch()} />
      ) : data && data.households === 0 ? (
        <Card><DataState kind="empty" message={t("nutrition.empty")} /></Card>
      ) : (
        <>
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {stats.map((item) => (
              <Card key={item.label} className="p-5">
                <dt className="text-sm text-muted">{item.label}</dt>
                <dd className="mt-1 font-heading text-2xl font-extrabold">{item.value}</dd>
              </Card>
            ))}
          </dl>
          <p className="flex items-start gap-2 rounded-control bg-mint px-4 py-3 text-sm text-primary-strong">
            <ShieldCheck aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
            {t("nutrition.suppressed", { n: data?.min_households_per_group ?? 5 })}. {t("nutrition.scale")}
          </p>
          <DataTable
              rows={data?.by_cell}
              columns={columns}
              rowKey={(row) => row.cell_id ?? row.cell}
              caption={t("nutrition.byCell")}
              emptyMessage={t("nutrition.empty")}
              searchText={(row) => row.cell}
              initialSort={{ key: "risk", direction: "desc" }}
            />
        </>
      )}
      <Card>
        <CardHeader title={t("nutrition.trend")} />
        <div className="p-5">
          <TrendChart series={[{ key: "households", label: t("nutrition.households"), color: "primary", kind: "bar" }, { key: "average_risk", label: t("nutrition.averageRisk"), color: "critical", kind: "line" }]} />
        </div>
      </Card>
    </div>
  );
}
