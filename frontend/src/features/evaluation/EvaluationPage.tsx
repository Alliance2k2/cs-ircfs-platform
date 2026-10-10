import { CheckCircle2, CircleSlash, Download, Printer, RefreshCw } from "lucide-react";
import { useState, type ReactNode } from "react";
import { isStaff, useSession } from "@/app/providers/SessionProvider";
import { BarList } from "@/components/data/BarList";
import { DataState } from "@/components/feedback/DataState";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { useI18n } from "@/i18n";
import { formatDate, formatNumber } from "@/lib/format";
import { API_BASE } from "@/services/api/client";
import { useApi, withParams } from "@/services/api/hooks";
import { evaluationSchema, type Evaluation } from "@/services/api/workspaces";

type Scheme = Evaluation["schemes"][number];
const PERIODS = [90, 180, 365];

function Figure({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line/70 py-1.5 text-sm last:border-0">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right font-semibold tabular-nums">{value}</dd>
    </div>
  );
}

function Section({ number, title, children }: { number: number; title: string; children: ReactNode }) {
  return (
    <section className="rounded-control border border-line p-4">
      <h3 className="flex items-center gap-2 text-sm font-bold">
        <span aria-hidden className="grid h-6 w-6 place-items-center rounded-full bg-forest text-2xs text-white">{number}</span>
        {title}
      </h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function SchemeEvidence({ scheme }: { scheme: Scheme }) {
  const { t, lang } = useI18n();
  const n = (value: number) => formatNumber(value, lang);
  const pct = (value: number | null) => (value === null ? "—" : `${n(value)}%`);
  const doc = scheme.documentation;
  const achievement = scheme.outcomes.yield_achievement;
  const stateTone = doc.state === "documented" ? "good" : doc.state === "demo" ? "warning" : "neutral";
  const stateLabel = { documented: t("evaluation.stateDocumented"), demo: t("evaluation.stateDemo"), missing: t("evaluation.stateMissing") }[doc.state];

  return (
    <Card className="break-inside-avoid p-5">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-line pb-4">
        <div>
          <h2 className="text-xl font-extrabold">{scheme.name}</h2>
          <p className="text-sm text-muted">
            {t("evaluation.partner")}: {scheme.implementing_partner ?? "—"} · {t("evaluation.hectares")}: {scheme.hectares_developed === null ? t("evaluation.stateMissing") : n(scheme.hectares_developed)}
          </p>
        </div>
        <div className="text-right text-sm">
          <p className="text-2xs font-bold uppercase tracking-wider text-muted">{t("evaluation.documentation")}</p>
          <p className="mt-1 flex items-center justify-end gap-2">
            <Badge tone={stateTone}>{stateLabel}</Badge>
            {doc.target_tons !== null && <span className="font-semibold">{n(doc.target_tons)} t</span>}
          </p>
          {doc.target_source && <p className="mt-1 max-w-xs text-xs text-muted">{t("evaluation.source")}: {doc.target_source}</p>}
        </div>
      </header>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Section number={1} title={t("evaluation.outcomes")}>
          <div className="mb-3 rounded-control bg-canvas p-3">
            <p className="text-2xs font-bold uppercase tracking-wider text-muted">{t("evaluation.achievement")}</p>
            <p className="mt-1 font-heading text-lg font-extrabold">
              {achievement.computable && achievement.value !== null ? `${n(achievement.value)}%` : t("evaluation.notComputable")}
            </p>
            <p className="text-xs text-muted">{achievement.formula}</p>
            <p className="mt-2 text-xs font-semibold">{t("evaluation.requirements")}</p>
            <ul className="mt-1 space-y-1">
              {achievement.requirements.map((item) => (
                <li key={item.item} className="flex gap-2 text-xs">
                  {item.met ? <CheckCircle2 aria-label={t("label.yes")} className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" /> : <CircleSlash aria-label={t("label.no")} className="mt-0.5 h-3.5 w-3.5 shrink-0 text-critical" />}
                  <span>{item.item}{item.note && <span className="block text-muted">{item.note}</span>}</span>
                </li>
              ))}
            </ul>
          </div>
          <dl>
            <Figure label={t("evaluation.harvestReports")} value={n(scheme.outcomes.harvest_reports)} />
            <Figure label={t("evaluation.expectedTons")} value={`${n(scheme.outcomes.expected_tons)} t`} />
            <Figure label={t("evaluation.reportedTons")} value={`${n(scheme.outcomes.reported_tons)} t`} />
            <Figure label={t("evaluation.pestAlerts")} value={`${n(scheme.outcomes.severe_pest_alerts)} / ${n(scheme.outcomes.pest_alerts)}`} />
          </dl>
          {scheme.outcomes.crops.length > 0 && (
            <table className="mt-3 w-full text-xs">
              <caption className="sr-only">{t("evaluation.byCrop")}</caption>
              <thead className="text-left text-muted">
                <tr><th scope="col" className="py-1">{t("crops.crop")}</th><th scope="col" className="text-right">{t("evaluation.harvestReports")}</th><th scope="col" className="text-right">{t("evaluation.expectedShort")}</th><th scope="col" className="text-right">{t("evaluation.reportedShort")}</th></tr>
              </thead>
              <tbody>
                {scheme.outcomes.crops.map((crop) => (
                  <tr key={crop.crop} className="border-t border-line/70">
                    <th scope="row" className="py-1 text-left font-semibold">{crop.crop}</th>
                    <td className="text-right tabular-nums">{crop.reports}</td>
                    <td className="text-right tabular-nums">{n(crop.expected_tons)} t</td>
                    <td className="text-right tabular-nums">{n(crop.reported_tons)} t <span className="text-muted">({crop.with_reported_tons})</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Section>

        <Section number={2} title={t("evaluation.bottlenecks")}>
          <dl>
            <Figure label={t("evaluation.assetsDown")} value={`${scheme.bottlenecks.assets_down} / ${scheme.bottlenecks.assets_reported}`} />
            <Figure label={t("irrigation.faults")} value={scheme.bottlenecks.fault_reports} />
            <Figure label={t("evaluation.flagged")} value={scheme.bottlenecks.flagged.length ? scheme.bottlenecks.flagged.join(", ") : t("label.none")} />
            <Figure label={t("evaluation.aboveBaseline")} value={scheme.bottlenecks.above_baseline.length ? scheme.bottlenecks.above_baseline.join(", ") : t("label.none")} />
          </dl>
          <div className="mt-3">
            <BarList tone="amber" empty={t("evaluation.noBottlenecks")} items={Object.entries(scheme.bottlenecks.by_category).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value)} />
          </div>
        </Section>

        <Section number={3} title={t("evaluation.feedback")}>
          <dl>
            <Figure label={t("nav.grievances")} value={scheme.feedback.grievances} />
            <Figure label={t("status.open")} value={scheme.feedback.open} />
            <Figure label={t("status.resolved")} value={scheme.feedback.resolved} />
          </dl>
          <div className="mt-3">
            <BarList tone="water" empty={t("evaluation.noFeedback")} items={Object.entries(scheme.feedback.by_category).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value)} />
          </div>
        </Section>

        <div className="grid gap-4">
          <Section number={4} title={t("evaluation.downstream")}>
            <dl>
              <Figure label={t("evaluation.downstreamTotal")} value={scheme.downstream.grievances} />
              <Figure label={t("evaluation.downstreamCount")} value={scheme.downstream.open} />
            </dl>
          </Section>
          <Section number={5} title={t("evaluation.evidence")}>
            <dl>
              <Figure label={t("evaluation.reports")} value={n(scheme.evidence.reports)} />
              <Figure label={t("evaluation.located")} value={pct(scheme.evidence.located_percent)} />
              <Figure label={t("evaluation.verified")} value={pct(scheme.evidence.verified_percent)} />
              <Figure label={t("verification.rejected")} value={scheme.evidence.rejected} />
              <Figure label={t("evaluation.demo")} value={pct(scheme.evidence.demo_percent)} />
              <Figure label={t("evaluation.months")} value={`${scheme.evidence.months_with_reports} / ${scheme.evidence.months_in_period}`} />
              <Figure label={t("evaluation.lastReport")} value={scheme.evidence.last_report_at ? formatDate(scheme.evidence.last_report_at, lang) : "—"} />
            </dl>
          </Section>
        </div>
      </div>
    </Card>
  );
}

/** The five evaluation questions answered from recorded evidence only, scheme by scheme. */
export function EvaluationPage() {
  const { t } = useI18n();
  const { role } = useSession();
  const [days, setDays] = useState(365);
  const evaluation = useApi(withParams("evaluation", { days }), evaluationSchema);
  const data = evaluation.data;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("evaluation.eyebrow")}
        title={t("evaluation.title")}
        description={t("evaluation.description")}
        updatedAt={evaluation.dataUpdatedAt}
        actions={
          <div className="flex flex-wrap items-end gap-2 print:hidden">
            <Select label={t("evaluation.period")} value={String(days)} onChange={(value) => setDays(Number(value))}
              options={PERIODS.map((n) => ({ value: String(n), label: t("evaluation.days", { n }) }))} />
            <Button icon={RefreshCw} onClick={() => void evaluation.refetch()} loading={evaluation.isFetching}>{t("filter.refresh")}</Button>
            <Button icon={Printer} onClick={() => window.print()} disabled={!data}>{t("action.print")}</Button>
            {isStaff(role) && (
              <a href={`${API_BASE}/${withParams("evaluation/export.csv", { days })}`} download
                className="inline-flex h-10 items-center gap-2 rounded-control bg-primary px-4 text-sm font-semibold text-white shadow-sm hover:bg-primary-strong">
                <Download aria-hidden className="h-4 w-4" />
                {t("action.export")}
              </a>
            )}
          </div>
        }
      />
      {evaluation.isPending ? (
        <DataState kind="loading" />
      ) : evaluation.error || !data ? (
        <DataState kind="error" message={evaluation.error?.message} onRetry={() => void evaluation.refetch()} />
      ) : (
        <>
          <Card className="p-5">
            <h2 className="text-base font-bold">{t("evaluation.questions")}</h2>
            <ol className="mt-3 grid gap-2 md:grid-cols-2">
              {data.questions.map((question) => (
                <li key={question.id} className="flex gap-2 text-sm">
                  <span aria-hidden className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-mint text-2xs font-bold text-forest">{question.id}</span>
                  {question.question}
                </li>
              ))}
            </ol>
            <p className="mt-4 rounded-control bg-canvas p-3 text-xs text-muted"><span className="font-semibold text-ink">{t("evaluation.method")}:</span> {data.method}</p>
          </Card>
          {data.schemes.length === 0 ? (
            <Card><DataState kind="empty" message={t("evaluation.noSchemes")} /></Card>
          ) : (
            data.schemes.map((scheme) => <SchemeEvidence key={scheme.scheme_id} scheme={scheme} />)
          )}
        </>
      )}
    </div>
  );
}
