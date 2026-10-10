import { RefreshCw } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { BarList, tally } from "@/components/data/BarList";
import { DataState } from "@/components/feedback/DataState";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { useI18n } from "@/i18n";
import { TrendChart } from "@/features/trends/TrendChart";
import { useApi, withParams } from "@/services/api/hooks";
import { fieldReportListSchema } from "@/services/api/workspaces";

const PERIODS = [30, 90, 365];

/** What is planted, what is expected and what is attacking it, from farmers' own reports. */
export function CropsPage() {
  const { t } = useI18n();
  const [days, setDays] = useState(90);
  const list = useApi(withParams("field-reports", { days }), fieldReportListSchema);
  const reports = (list.data?.reports ?? []).filter((report) => report.source === "crop" && report.data_origin !== "simulator");
  const harvest = reports.filter((report) => report.kind === "harvest");
  const pests = reports.filter((report) => report.kind === "pest");
  const lists = [
    { title: t("crops.byCrop"), items: tally(reports, (report) => report.crop), tone: "primary" as const, unit: "" },
    { title: t("crops.pestsBySeverity"), items: tally(pests, (report) => (report.severity === null ? null : t("crops.severity", { n: report.severity }))).sort((a, b) => b.label.localeCompare(a.label)), tone: "critical" as const, unit: "" },
    { title: t("crops.pestsBySector"), items: tally(pests, (report) => report.sector), tone: "amber" as const, unit: "" },
    { title: t("crops.topPests"), items: tally(pests, (report) => report.pest).slice(0, 8), tone: "amber" as const, unit: "" },
    { title: t("crops.expectedByCrop"), items: tally(harvest.filter((report) => report.expected_tons !== null), (report) => report.crop, (report) => report.expected_tons ?? 0), tone: "water" as const, unit: "t" },
    { title: t("crops.reportedByCrop"), items: tally(harvest.filter((report) => report.reported_tons !== null), (report) => report.crop, (report) => report.reported_tons ?? 0), tone: "primary" as const, unit: "t" },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("crops.eyebrow")}
        title={t("crops.title")}
        description={t("crops.description")}
        updatedAt={list.dataUpdatedAt}
        actions={
          <>
            <Select label={t("filter.period")} value={String(days)} onChange={(value) => setDays(Number(value))}
              options={PERIODS.map((n) => ({ value: String(n), label: t("filter.days", { n }) }))} />
            <Button icon={RefreshCw} onClick={() => void list.refetch()} loading={list.isFetching} className="self-end">{t("filter.refresh")}</Button>
          </>
        }
      />
      {list.data?.truncated && <p role="status" className="rounded-control bg-amber-soft px-4 py-2 text-sm font-semibold text-amber">{t("crops.truncated")}</p>}
      {list.isPending ? (
        <DataState kind="loading" />
      ) : list.error ? (
        <DataState kind="error" message={list.error.message} onRetry={() => void list.refetch()} />
      ) : (
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {lists.map((item) => (
            <Card key={item.title}>
              <CardHeader title={item.title} />
              <div className="p-5"><BarList items={item.items} tone={item.tone} unit={item.unit} empty={t("crops.empty")} /></div>
            </Card>
          ))}
        </div>
      )}
      <Card>
        <CardHeader title={t("crops.monthly")} />
        <div className="p-5">
          <TrendChart series={[{ key: "plantings", label: t("crops.plantings"), color: "primary", kind: "bar" }, { key: "severe_pests", label: t("trends.severePests"), color: "critical", kind: "line" }]} />
        </div>
      </Card>
      <p className="text-xs text-muted">
        {t("crops.provenance")} <Link to="/field-reports" className="font-semibold text-primary hover:underline">{t("crops.seeReports")}</Link>
      </p>
    </div>
  );
}
