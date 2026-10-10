import { ArrowDownRight, ArrowUpRight, Minus, Printer, RefreshCw } from "lucide-react";
import { useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { z } from "zod";
import { BarList } from "@/components/data/BarList";
import { DataState } from "@/components/feedback/DataState";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { TextField } from "@/components/ui/Field";
import { useI18n } from "@/i18n";
import type { MessageKey } from "@/i18n/en";
import { cx } from "@/lib/cx";
import { formatNumber } from "@/lib/format";
import { useApi, withParams } from "@/services/api/hooks";
import { monthlySchema } from "@/services/api/workspaces";

const reportSchema = monthlySchema.extend({
  cases: monthlySchema.shape.cases.extend({ by_priority: z.record(z.number()).optional() }),
  grievances: z.object({ received: z.number(), resolved: z.number(), close_loop_sms: z.number(), median_days_to_resolve: z.number().nullable(), by_category: z.record(z.number()) }),
  pests: z.array(z.object({ pest: z.string(), reports: z.number(), severe: z.number(), sectors: z.array(z.string()) })),
  rainfall: z.array(z.object({ sector: z.string(), rainfall_mm: z.number(), gauges: z.number(), readings: z.number() })),
  nutrition: z.object({
    households: z.number(), average_risk: z.number().nullable(), high_risk_households: z.number(),
    cells: z.array(z.object({ cell: z.string(), sector: z.string().nullable(), households: z.number(), average_risk: z.number() })),
    cells_hidden: z.number().optional(), min_households_per_group: z.number().optional(),
  }),
  messages: z.object({ airtime_rewards: z.number(), airtime_rwf: z.number(), sms_sent_by_purpose: z.record(z.unknown()), delivery: z.record(z.number()) }),
});

const FIGURES = ["reports", "harvest_reports", "pest_reports", "rain_readings", "asset_faults", "grievances", "nutrition_surveys", "ussd_sessions", "sms_received", "new_people", "cases_opened"] as const;

function currentMonth(): string {
  return new Intl.DateTimeFormat("en-CA", { year: "numeric", month: "2-digit", timeZone: "Africa/Kigali" }).format(new Date()).slice(0, 7);
}

function Block({ title, children, note }: { title: string; children: ReactNode; note?: string }) {
  return (
    <Card className="break-inside-avoid">
      <CardHeader title={title} note={note} />
      <div className="p-5">{children}</div>
    </Card>
  );
}

/** One month of evidence against the month before, ready to print for the district meeting. */
export function MonthlyReportPage() {
  const { t, lang } = useI18n();
  const [params, setParams] = useSearchParams();
  const [month, setMonth] = useState(params.get("month") ?? currentMonth());
  const report = useApi(withParams("analytics/monthly-report", { month }), reportSchema);
  const data = report.data;
  const n = (value: number) => formatNumber(value, lang);
  const choose = (value: string) => {
    if (!/^\d{4}-\d{2}$/.test(value)) return;
    setMonth(value);
    setParams({ month: value }, { replace: true });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("monthly.eyebrow")}
        title={data ? `${t("monthly.title")} · ${data.label}` : t("monthly.title")}
        description={t("monthly.description")}
        updatedAt={report.dataUpdatedAt}
        actions={
          <div className="flex flex-wrap items-end gap-2 print:hidden">
            <div className="w-44"><TextField label={t("monthly.month")} type="month" value={month} max={currentMonth()} onChange={(event) => choose(event.target.value)} /></div>
            <Button icon={RefreshCw} onClick={() => void report.refetch()} loading={report.isFetching}>{t("filter.refresh")}</Button>
            <Button icon={Printer} onClick={() => window.print()} disabled={!data}>{t("action.print")}</Button>
          </div>
        }
      />
      {report.isPending ? (
        <DataState kind="loading" />
      ) : report.error || !data ? (
        <DataState kind="error" message={report.error?.message} onRetry={() => void report.refetch()} />
      ) : (
        <>
          <section aria-labelledby="figures-title">
            <h2 id="figures-title" className="sr-only">{t("monthly.figures")}</h2>
            <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
              {FIGURES.filter((key) => data.figures[key]).map((key) => {
                const figure = data.figures[key]!;
                const change = figure.change_percent;
                const Icon = change === null || change === 0 ? Minus : change > 0 ? ArrowUpRight : ArrowDownRight;
                return (
                  <Card key={key} className="p-4">
                    <dt className="text-xs text-muted">{t(`monthly.figure.${key}` as MessageKey)}</dt>
                    <dd className="mt-1 font-heading text-2xl font-extrabold">{n(figure.value)}</dd>
                    <dd className={cx("mt-0.5 flex items-center gap-1 text-xs", change === null ? "text-muted" : "text-ink")}>
                      <Icon aria-hidden className="h-3.5 w-3.5" />
                      {change === null ? t("monthly.noComparison", { n: figure.previous }) : t("monthly.changeVs", { change: `${change > 0 ? "+" : ""}${change}`, n: figure.previous })}
                    </dd>
                  </Card>
                );
              })}
            </dl>
            <p className="mt-2 text-xs text-muted">{t("monthly.sectorsReporting", { n: data.sectors_reporting, total: data.sectors_total })}</p>
          </section>

          <div className="grid gap-6 lg:grid-cols-2 [&>*]:min-w-0">
            <Block title={t("monthly.schemes")}>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[32rem] text-sm">
                  <thead className="text-left text-2xs uppercase tracking-wider text-muted">
                    <tr>
                      <th scope="col" className="py-2">{t("label.scheme")}</th>
                      <th scope="col" className="text-right">{t("evaluation.harvestReports")}</th>
                      <th scope="col" className="text-right">{t("evaluation.expectedShort")}</th>
                      <th scope="col" className="text-right">{t("monthly.reported")}</th>
                      <th scope="col" className="text-right">{t("trends.severePests")}</th>
                      <th scope="col" className="text-right">{t("trends.assetFaults")}</th>
                      <th scope="col" className="text-right">{t("nav.grievances")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.schemes.map((scheme) => (
                      <tr key={scheme.name} className="border-t border-line">
                        <th scope="row" className="py-2 text-left font-semibold">{scheme.name}</th>
                        <td className="text-right tabular-nums">{scheme.crop_reports}</td>
                        <td className="text-right tabular-nums">{n(scheme.expected_tons)} t</td>
                        <td className="text-right tabular-nums">{n(scheme.reported_tons)} t</td>
                        <td className="text-right tabular-nums">{scheme.severe_pest_reports}</td>
                        <td className="text-right tabular-nums">{scheme.asset_faults}</td>
                        <td className="text-right tabular-nums">{scheme.grievances}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Block>

            <Block title={t("monthly.cases")}>
              <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                {[
                  [t("monthly.opened"), data.cases.opened],
                  [t("monthly.resolved"), data.cases.resolved_in_month],
                  [t("monthly.openAtEnd"), data.cases.open_at_month_end],
                  [t("monthly.medianDays"), data.cases.median_days_to_resolve === null ? "—" : n(data.cases.median_days_to_resolve)],
                ].map(([label, value]) => (
                  <div key={String(label)} className="rounded-control bg-canvas p-3">
                    <dt className="text-xs text-muted">{label}</dt>
                    <dd className="font-heading text-xl font-extrabold">{value}</dd>
                  </div>
                ))}
              </dl>
              <h3 className="mt-5 text-sm font-bold">{t("nav.grievances")}</h3>
              <p className="mt-1 text-sm text-muted">
                {t("monthly.grievanceLine", { received: data.grievances.received, resolved: data.grievances.resolved, sms: data.grievances.close_loop_sms })}
              </p>
              <div className="mt-3">
                <BarList tone="water" empty={t("evaluation.noFeedback")} items={Object.entries(data.grievances.by_category).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value)} />
              </div>
            </Block>

            <Block title={t("monthly.pests")}>
              <BarList tone="critical" empty={t("crops.empty")} items={data.pests.map((pest) => ({ label: pest.pest, value: pest.reports, note: t("monthly.severeIn", { n: pest.severe, sectors: pest.sectors.join(", ") || "—" }) }))} />
            </Block>

            <Block title={t("monthly.rainfall")} note={t("trends.rainNote")}>
              <BarList tone="water" unit="mm" empty={t("crops.empty")} items={data.rainfall.map((row) => ({ label: row.sector, value: row.rainfall_mm, note: t("monthly.gauges", { n: row.gauges }) }))} />
            </Block>

            <Block title={t("nav.nutrition")} note={t("nutrition.scale")}>
              <p className="text-sm">
                {t("monthly.nutritionLine", { n: data.nutrition.households, high: data.nutrition.high_risk_households, risk: data.nutrition.average_risk === null ? "—" : n(data.nutrition.average_risk) })}
              </p>
              <div className="mt-3">
                <BarList tone="amber" empty={t("monthly.noCells")} items={data.nutrition.cells.map((cell) => ({ label: `${cell.cell}${cell.sector ? ` · ${cell.sector}` : ""}`, value: cell.average_risk, note: t("monthly.households", { n: cell.households }) }))} />
              </div>
              {(data.nutrition.cells_hidden ?? 0) > 0 && (
                <p className="mt-2 text-xs text-muted">{t("monthly.cellsHidden", { n: data.nutrition.cells_hidden ?? 0, min: data.nutrition.min_households_per_group ?? 5 })}</p>
              )}
            </Block>

            <Block title={t("monthly.sectors")}>
              <BarList empty={t("crops.empty")} items={data.sector_activity.map((row) => ({ label: row.sector, value: row.reports }))} />
              <p className="mt-4 text-sm text-muted">{t("monthly.rewards", { n: data.messages.airtime_rewards, rwf: n(data.messages.airtime_rwf) })}</p>
            </Block>
          </div>
          <p className="text-xs text-muted">{t("trends.provenance")}</p>
        </>
      )}
    </div>
  );
}
