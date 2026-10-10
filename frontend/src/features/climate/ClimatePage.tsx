import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, CloudRain, RefreshCw, Send } from "lucide-react";
import { useState } from "react";
import { z } from "zod";
import { canAccess } from "@/app/access";
import { useSession } from "@/app/providers/SessionProvider";
import { DataTable, type Column } from "@/components/data/DataTable";
import { DataState } from "@/components/feedback/DataState";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge, type Tone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Overlay";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n";
import type { MessageKey } from "@/i18n/en";
import { formatNumber } from "@/lib/format";
import { apiSend } from "@/services/api/client";
import { useApi } from "@/services/api/hooks";
import { broadcastSchema, scheduleRowSchema, weeklyAdviceSchema, type ScheduleRow } from "@/services/api/workspaces";
import { TrendChart } from "@/features/trends/TrendChart";

const LEVEL_TONE: Record<string, Tone> = { irrigate_more: "warning", irrigate_less: "water", normal: "good", no_data: "neutral" };

export function LevelBadge({ level }: { level: string }) {
  const { t } = useI18n();
  const known = level in LEVEL_TONE;
  return <Badge tone={LEVEL_TONE[level] ?? "neutral"}>{known ? t(`climate.level.${level}` as MessageKey) : level}</Badge>;
}

/** Rain-gauge totals, the forecast and the advice each sector gets, with a previewed send. */
export function ClimatePage() {
  const { t, lang } = useI18n();
  const { role } = useSession();
  const toast = useToast();
  const client = useQueryClient();
  const schedule = useApi("advisory/irrigation-schedule", z.array(scheduleRowSchema));
  const weekly = useApi("advisory/weekly-advice", weeklyAdviceSchema);
  const [preview, setPreview] = useState<z.infer<typeof broadcastSchema> | null>(null);
  const mm = (value: number | null) => (value === null ? "—" : `${formatNumber(value, lang)} mm`);

  const send = useMutation({
    mutationFn: (live: boolean) => apiSend("POST", "advisory/irrigation-schedule/send", { preview: !live, sector_ids: [] }, broadcastSchema),
    onSuccess: (result, live) => {
      if (!live) return setPreview(result);
      setPreview(null);
      toast.success(t("climate.sent", { recipients: result.total_recipients }));
      void client.invalidateQueries({ queryKey: ["api"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const columns: Column<ScheduleRow>[] = [
    { key: "sector", header: t("label.sector"), primary: true, render: (row) => <span className="font-semibold">{row.sector}</span>, sortValue: (row) => row.sector },
    { key: "level", header: t("climate.status"), render: (row) => <LevelBadge level={row.level} />, sortValue: (row) => row.level },
    { key: "rain", header: t("climate.rain7"), render: (row) => mm(row.rainfall_mm_7d), sortValue: (row) => row.rainfall_mm_7d },
    { key: "readings", header: t("climate.readings"), render: (row) => row.readings, sortValue: (row) => row.readings },
    { key: "forecast", header: t("climate.forecast"), render: (row) => mm(row.forecast_mm_7d), sortValue: (row) => row.forecast_mm_7d },
    {
      key: "thresholds",
      header: t("climate.thresholds"),
      render: (row) => (
        <span className="text-sm">
          {formatNumber(row.threshold_dry_mm, lang)} / {formatNumber(row.threshold_wet_mm, lang)} mm
          <span className="block text-xs text-muted">{row.threshold_source ?? t("climate.uncalibrated")}</span>
        </span>
      ),
    },
    {
      key: "advice",
      header: t("climate.advice"),
      className: "max-w-md",
      render: (row) => <span className="text-sm">{lang === "rw" ? row.message_rw : row.message_en}</span>,
    },
  ];

  const w = weekly.data;
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("climate.eyebrow")}
        title={t("climate.title")}
        description={t("climate.description")}
        updatedAt={schedule.dataUpdatedAt}
        actions={
          <>
            <Button icon={RefreshCw} onClick={() => void schedule.refetch()} loading={schedule.isFetching}>{t("filter.refresh")}</Button>
            {canAccess(role, "planner") && (
              <Button variant="primary" icon={Send} onClick={() => send.mutate(false)} loading={send.isPending && send.variables === false}>
                {t("climate.send")}
              </Button>
            )}
          </>
        }
      />
      <p className="flex items-start gap-2 rounded-control bg-water-soft px-4 py-3 text-sm text-water">
        <CloudRain aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
        {t("climate.provenance")}
      </p>

      <DataTable
          rows={schedule.data}
          columns={columns}
          rowKey={(row) => row.sector_id}
          caption={t("climate.title")}
          loading={schedule.isPending}
          error={schedule.error ? schedule.error.message : null}
          onRetry={() => void schedule.refetch()}
          emptyMessage={t("state.empty")}
          searchText={(row) => row.sector}
          pageSize={20}
        />

      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <Card>
          <CardHeader title={t("climate.weekly")} />
          <div className="space-y-2 p-5 text-sm">
            {weekly.isPending ? <DataState kind="loading" compact /> : weekly.error ? <DataState kind="error" compact onRetry={() => void weekly.refetch()} /> : w && (
              <>
                <p className="flex items-start gap-2">
                  <CalendarClock aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-muted" />
                  {w.enabled ? t("climate.weeklyOn", { day: w.weekday, time: w.time }) : t("climate.weeklyOff")}
                </p>
                <p className="text-muted">
                  {w.last_run ? t("climate.lastRun", { week: w.last_run.week_key, sectors: w.last_run.sectors, recipients: w.last_run.recipients }) : t("climate.noRun")}
                </p>
              </>
            )}
          </div>
        </Card>
        <Card>
          <CardHeader title={t("climate.trend")} />
          <div className="p-5">
            <TrendChart series={[{ key: "rainfall_mm", label: t("climate.rainMonth"), color: "water", kind: "bar" }, { key: "rain_readings", label: t("climate.readings"), color: "primary", kind: "line" }]} />
          </div>
        </Card>
      </div>

      <Dialog
        open={preview !== null}
        onClose={() => setPreview(null)}
        title={t("climate.send")}
        actions={
          <>
            <Button onClick={() => setPreview(null)}>{t("action.cancel")}</Button>
            <Button variant="primary" icon={Send} onClick={() => send.mutate(true)} loading={send.isPending && send.variables === true} disabled={!preview?.total_recipients}>
              {t("action.send")}
            </Button>
          </>
        }
      >
        <p>{t("climate.sendPreview", { recipients: preview?.total_recipients ?? 0, sectors: preview?.sectors.length ?? 0 })}</p>
        {preview && preview.sectors.length > 0 && (
          <ul className="mt-3 space-y-1">
            {preview.sectors.map((item) => (
              <li key={item.sector} className="flex items-center justify-between gap-2 rounded-control bg-canvas px-3 py-1.5">
                <span>{item.sector} <LevelBadge level={item.level} /></span>
                <span className="font-semibold">{item.recipients}</span>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-xs text-muted">{t("climate.sendHint")}</p>
      </Dialog>
    </div>
  );
}
