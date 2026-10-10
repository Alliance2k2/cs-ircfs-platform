import { Download, RefreshCw } from "lucide-react";
import { useState } from "react";
import { isStaff, useSession } from "@/app/providers/SessionProvider";
import { FlagBadges, OriginBadge, VerificationBadge } from "@/components/data/badges";
import { DataTable, type Column } from "@/components/data/DataTable";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { useI18n } from "@/i18n";
import type { MessageKey } from "@/i18n/en";
import { formatDate, relativeTime } from "@/lib/format";
import { API_BASE } from "@/services/api/client";
import { useApi, useReferenceData, withParams } from "@/services/api/hooks";
import { fieldReportListSchema, type FieldReport } from "@/services/api/workspaces";
import { ReportDrawer, reportValue } from "./ReportDrawer";

const KINDS = ["harvest", "pest", "rain", "asset"] as const;
const PERIODS = [7, 30, 90, 365];

interface Filters {
  kind: string;
  days: number;
  sector_id: string;
  scheme_id: string;
  verification: string;
  origin: string;
}

/** Every citizen report with its automatic checks, filterable, verifiable and exportable. */
export function FieldReportsPage() {
  const { t, lang } = useI18n();
  const { role } = useSession();
  const { sectors, schemes } = useReferenceData();
  const [filters, setFilters] = useState<Filters>({ kind: "", days: 30, sector_id: "", scheme_id: "", verification: "", origin: "" });
  const [selected, setSelected] = useState<FieldReport | null>(null);
  const path = withParams("field-reports", { ...filters });
  const list = useApi(path, fieldReportListSchema);
  const set = (patch: Partial<Filters>) => setFilters((current) => ({ ...current, ...patch }));
  const flagged = (list.data?.reports ?? []).filter((report) => report.flags.length).length;

  const columns: Column<FieldReport>[] = [
    {
      key: "title",
      header: t("reports.title"),
      primary: true,
      render: (row) => (
        <span>
          <span className="block font-semibold text-ink">{row.title}</span>
          <span className="text-xs text-muted">{t(`kind.${row.kind}` as MessageKey)}</span>
        </span>
      ),
      sortValue: (row) => row.title,
    },
    { key: "value", header: t("reports.value"), render: (row) => reportValue(row, lang) },
    {
      key: "place",
      header: t("reports.location"),
      render: (row) => (
        <span className="text-sm">
          {[row.sector, row.cell].filter(Boolean).join(" · ") || "—"}
          {row.scheme && <span className="block text-xs text-muted">{row.scheme}</span>}
        </span>
      ),
      sortValue: (row) => row.sector,
    },
    { key: "reporter", header: t("reports.reporter"), render: (row) => row.reporter ?? "—" },
    { key: "flags", header: t("label.flags"), render: (row) => <FlagBadges flags={row.flags} />, sortValue: (row) => row.flags.length },
    {
      key: "verification",
      header: t("label.verification"),
      render: (row) => (
        <span className="flex flex-wrap gap-1">
          <VerificationBadge status={row.verification_status} />
          <OriginBadge origin={row.data_origin} />
        </span>
      ),
      sortValue: (row) => row.verification_status,
    },
    {
      key: "date",
      header: t("label.date"),
      render: (row) => <span title={relativeTime(row.created_at, lang)}>{formatDate(row.created_at, lang)}</span>,
      sortValue: (row) => row.created_at,
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("reports.eyebrow")}
        title={t("reports.title")}
        description={t("reports.description")}
        updatedAt={list.dataUpdatedAt}
        actions={
          <>
            <Button icon={RefreshCw} onClick={() => void list.refetch()} loading={list.isFetching}>{t("filter.refresh")}</Button>
            {isStaff(role) && (
              <a
                href={`${API_BASE}/${withParams("field-reports/export.csv", { ...filters })}`}
                download
                className="inline-flex h-10 items-center gap-2 rounded-control bg-primary px-4 text-sm font-semibold text-white shadow-sm hover:bg-primary-strong"
              >
                <Download aria-hidden className="h-4 w-4" />
                {t("action.export")}
              </a>
            )}
          </>
        }
      />

      <div className="flex flex-wrap items-end gap-3">
        <Select label={t("label.kind")} value={filters.kind} onChange={(kind) => set({ kind })}
          options={[{ value: "", label: t("label.all") }, ...KINDS.map((kind) => ({ value: kind, label: t(`kind.${kind}`) }))]} />
        <Select label={t("filter.period")} value={String(filters.days)} onChange={(days) => set({ days: Number(days) })}
          options={PERIODS.map((days) => ({ value: String(days), label: t("filter.days", { n: days }) }))} />
        <Select label={t("filter.sector")} value={filters.sector_id} onChange={(sector_id) => set({ sector_id })}
          options={[{ value: "", label: t("filter.allSectors") }, ...sectors.map((sector) => ({ value: String(sector.id), label: sector.name }))]} />
        <Select label={t("filter.scheme")} value={filters.scheme_id} onChange={(scheme_id) => set({ scheme_id })}
          options={[{ value: "", label: t("filter.allSchemes") }, ...schemes.map((scheme) => ({ value: String(scheme.id), label: scheme.name }))]} />
        <Select label={t("label.verification")} value={filters.verification} onChange={(verification) => set({ verification })}
          options={[{ value: "", label: t("label.all") }, ...(["unverified", "verified", "rejected"] as const).map((value) => ({ value, label: t(`verification.${value}`) }))]} />
        <Select label={t("label.origin")} value={filters.origin} onChange={(origin) => set({ origin })}
          options={[{ value: "", label: t("label.all") }, ...(["field", "demo", "import"] as const).map((value) => ({ value, label: t(`origin.${value}`) }))]} />
      </div>

      {list.data && (
        <p className="flex flex-wrap items-center gap-2 text-sm text-muted">
          <Badge tone={flagged ? "warning" : "good"}>{t("reports.flaggedCount", { n: flagged })}</Badge>
          {t("reports.flagNote")}
          {!list.data.personal_data && <span>{t("reports.masked")}</span>}
        </p>
      )}
      {list.data?.truncated && <p role="status" className="rounded-control bg-amber-soft px-4 py-2 text-sm font-semibold text-amber">{t("reports.truncated")}</p>}

      <DataTable
          rows={list.data?.reports}
          columns={columns}
          rowKey={(row) => `${row.source}-${row.id}`}
          caption={t("reports.title")}
          loading={list.isPending}
          error={list.error ? list.error.message : null}
          onRetry={() => void list.refetch()}
          emptyMessage={t("reports.empty")}
          searchText={(row) => `${row.title} ${row.crop ?? ""} ${row.pest ?? ""} ${row.asset ?? ""} ${row.sector ?? ""} ${row.cell ?? ""} ${row.reporter ?? ""}`}
          onRowClick={setSelected}
          initialSort={{ key: "date", direction: "desc" }}
        />
      <ReportDrawer report={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
