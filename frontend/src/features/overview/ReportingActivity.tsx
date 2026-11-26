import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { useSession, isStaff } from "@/app/providers/SessionProvider";
import { Card, CardHeader } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { DataState } from "@/components/feedback/DataState";
import { Skeleton } from "@/components/ui/Skeleton";
import { apiGet, query } from "@/services/api/client";
import { useI18n } from "@/i18n";
import { formatNumber } from "@/lib/format";
import type { OverviewFilters } from "./useOverview";

const activitySchema = z.object({ start: z.string(), end: z.string(), previous_start: z.string(), previous_end: z.string(), reports: z.number(), previous_reports: z.number(), change: z.number(), verified_reports: z.number(), located_reports: z.number(), demo_mode: z.boolean() });
const cellsSchema = z.array(z.object({ id: z.number(), name: z.string(), sector_id: z.number() }));
const cooperativesSchema = z.array(z.object({ id: z.number(), name: z.string(), sector_id: z.number().nullable() }));
const day = (date: Date) => new Intl.DateTimeFormat("en-CA", { timeZone: "Africa/Kigali", year: "numeric", month: "2-digit", day: "2-digit" }).format(date);

/** Receipt filters affect only this panel; operational condition remains a current-state view. */
export function ReportingActivity({ filters }: { filters: OverviewFilters }) {
  const { t, lang } = useI18n();
  const { role } = useSession();
  const defaults = useMemo(() => {
    const today = new Date();
    return { end: day(today), start: day(new Date(today.getTime() - (filters.days - 1) * 86400000)) };
  }, [filters.days]);
  const [dates, setDates] = useState<{ start: string; end: string } | null>(null);
  const [cell, setCell] = useState("");
  const [cooperative, setCooperative] = useState("");
  const range = dates ?? defaults;
  const cells = useQuery({ queryKey: ["activity-cells"], queryFn: ({ signal }) => apiGet("cells", cellsSchema, signal), staleTime: 600000 });
  const coops = useQuery({ queryKey: ["activity-cooperatives"], queryFn: ({ signal }) => apiGet("cooperatives", cooperativesSchema, signal), enabled: isStaff(role), staleTime: 600000 });
  // Changing sector cannot accidentally retain a hidden cell or cooperative.
  const selectedCell = cells.data?.find((item) => String(item.id) === cell && (!filters.sectorId || item.sector_id === filters.sectorId));
  const selectedCoop = coops.data?.find((item) => String(item.id) === cooperative && (!filters.sectorId || item.sector_id === filters.sectorId));
  const params = { ...range, sector_id: filters.sectorId, scheme_id: filters.schemeId, cell_id: selectedCell?.id, cooperative_id: selectedCoop?.id };
  const valid = Boolean(range.start && range.end && range.start <= range.end && (Date.parse(range.end) - Date.parse(range.start)) / 86400000 < 366);
  const result = useQuery({ queryKey: ["reporting-activity", params], queryFn: ({ signal }) => apiGet(`analytics/reporting-activity${query(params)}`, activitySchema, signal), enabled: valid, refetchInterval: 60000 });
  const data = result.data;
  return <Card aria-label={t("activity.title")}>
    <CardHeader title={t("activity.title")} note={t("activity.note")} />
    <div className="space-y-4 p-4 sm:p-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Select label={t("activity.cell")} value={selectedCell ? cell : ""} onChange={setCell} options={[{ value: "", label: t("activity.allCells") }, ...(cells.data ?? []).filter((item) => !filters.sectorId || item.sector_id === filters.sectorId).map((item) => ({ value: String(item.id), label: item.name }))]} />
        {isStaff(role) && <Select label={t("activity.cooperative")} value={selectedCoop ? cooperative : ""} onChange={setCooperative} options={[{ value: "", label: t("activity.allCooperatives") }, ...(coops.data ?? []).filter((item) => !filters.sectorId || item.sector_id === filters.sectorId).map((item) => ({ value: String(item.id), label: item.name }))]} />}
        {(["start", "end"] as const).map((key) => <label key={key} className="flex min-w-0 flex-col gap-1 text-2xs font-bold uppercase tracking-wider text-muted">{t(key === "start" ? "activity.start" : "activity.end")}<input type="date" value={range[key]} onChange={(event) => setDates({ ...range, [key]: event.target.value })} className="min-h-11 min-w-0 rounded-control border border-line bg-surface px-3 text-sm font-semibold text-ink" /></label>)}
      </div>
      {(cells.isError || coops.isError) && <p role="status" className="text-xs text-amber">{t("activity.optionsError")}</p>}
      {!valid ? <p role="alert" className="text-sm text-critical">{t("activity.invalid")}</p> : result.isPending ? <Skeleton className="h-24" /> : result.isError ? <DataState kind="error" message={result.error.message} onRetry={() => void result.refetch()} /> : data && <>
        <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[[t("activity.reports"), data.reports], [t("activity.previous"), data.previous_reports], [t("activity.verified"), data.verified_reports], [t("activity.located"), data.located_reports]].map(([label, value]) => <div key={String(label)} className="min-w-0 rounded-xl border border-line bg-canvas p-3"><dt className="text-xs text-muted">{label}</dt><dd className="mt-2 font-heading text-2xl font-extrabold tabular-nums text-forest">{formatNumber(Number(value), lang)}</dd></div>)}
        </dl>
        <p className="text-sm text-ink">{t("activity.change", { n: `${data.change > 0 ? "+" : ""}${formatNumber(data.change, lang)}` })} <span className="text-muted">({data.previous_start} – {data.previous_end})</span></p>
        <p className="text-xs text-muted">{t("activity.basis")}</p>
      </>}
    </div>
  </Card>;
}
