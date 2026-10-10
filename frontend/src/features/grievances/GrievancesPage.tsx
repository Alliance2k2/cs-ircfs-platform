import { RefreshCw, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { z } from "zod";
import { StatusBadge } from "@/components/data/badges";
import { DataTable, type Column } from "@/components/data/DataTable";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { WorkItemDrawer, type WorkItem } from "@/features/actions/WorkItemDrawer";
import { useI18n } from "@/i18n";
import type { MessageKey } from "@/i18n/en";
import { formatDate, parseTimestamp, relativeTime } from "@/lib/format";
import { useApi, useReferenceData } from "@/services/api/hooks";
import { STATUSES, feedbackSchema, type Feedback } from "@/services/api/workspaces";

/** Anonymous community concerns: triage, assign, resolve and close the loop by SMS to the cell. */
export function GrievancesPage() {
  const { t, lang } = useI18n();
  const { place, schemeName } = useReferenceData();
  const list = useApi("feedback", z.array(feedbackSchema));
  const [status, setStatus] = useState("active");
  const [category, setCategory] = useState("");
  const [selected, setSelected] = useState<WorkItem | null>(null);
  const categories = [...new Set((list.data ?? []).map((row) => row.category))].sort();
  const rows = (list.data ?? []).filter(
    (row) => (status === "" || (status === "active" ? !["resolved", "closed"].includes(row.status) : row.status === status)) && (!category || row.category === category),
  );
  const now = Date.now();

  const columns: Column<Feedback>[] = [
    { key: "ref", header: t("grievances.reference"), render: (row) => <span className="font-mono text-xs">FB-{String(row.id).padStart(3, "0")}</span>, sortValue: (row) => row.id },
    {
      key: "category", header: t("grievances.category"), primary: true, sortValue: (row) => row.category,
      render: (row) => (
        <span>
          <span className="block font-semibold">{row.category}</span>
          <span className="line-clamp-2 text-xs text-muted">{row.message}</span>
        </span>
      ),
    },
    { key: "status", header: t("label.status"), render: (row) => <StatusBadge status={row.status} />, sortValue: (row) => STATUSES.indexOf(row.status) },
    {
      key: "place", header: t("actions.place"),
      render: (row) => (
        <span className="text-sm">
          {place(row.cell_id) ?? "—"}
          {row.scheme_id && <span className="block text-xs text-muted">{schemeName.get(row.scheme_id)}</span>}
        </span>
      ),
    },
    {
      key: "due", header: t("actions.due"), sortValue: (row) => row.due_at,
      render: (row) => {
        if (!row.due_at) return <span className="text-muted">—</span>;
        const late = !["resolved", "closed"].includes(row.status) && parseTimestamp(row.due_at).getTime() < now;
        return late ? <Badge tone="critical">{t("actions.overdue")} · {formatDate(row.due_at, lang)}</Badge> : formatDate(row.due_at, lang);
      },
    },
    { key: "received", header: t("grievances.received"), render: (row) => relativeTime(row.created_at, lang), sortValue: (row) => row.created_at },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("grievances.eyebrow")}
        title={t("grievances.title")}
        description={t("grievances.description")}
        updatedAt={list.dataUpdatedAt}
        actions={<Button icon={RefreshCw} onClick={() => void list.refetch()} loading={list.isFetching}>{t("filter.refresh")}</Button>}
      />
      <p className="flex items-start gap-2 rounded-control bg-mint px-4 py-3 text-sm text-primary-strong">
        <ShieldCheck aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
        {t("grievances.anonymity")}
      </p>
      <DataTable
          rows={rows}
          columns={columns}
          rowKey={(row) => row.id}
          caption={t("grievances.title")}
          loading={list.isPending}
          error={list.error ? list.error.message : null}
          onRetry={() => void list.refetch()}
          emptyMessage={t("grievances.empty")}
          searchText={(row) => `FB-${String(row.id).padStart(3, "0")} ${row.category} ${row.message} ${place(row.cell_id) ?? ""}`}
          onRowClick={(row) => setSelected({ kind: "grievance", id: row.id, title: row.category, details: row.message, cellId: row.cell_id })}
          initialSort={{ key: "received", direction: "desc" }}
          toolbar={
            <>
              <Select label={t("label.status")} value={status} onChange={setStatus} options={[
                { value: "active", label: t("grievances.active") },
                { value: "", label: t("label.all") },
                ...STATUSES.map((value) => ({ value, label: t(`status.${value}` as MessageKey) })),
              ]} />
              <Select label={t("grievances.category")} value={category} onChange={setCategory}
                options={[{ value: "", label: t("label.all") }, ...categories.map((value) => ({ value, label: value }))]} />
            </>
          }
        />
      <WorkItemDrawer item={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
