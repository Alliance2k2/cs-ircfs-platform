import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { z } from "zod";
import { PriorityBadge, StatusBadge } from "@/components/data/badges";
import { DataTable, type Column } from "@/components/data/DataTable";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { useI18n } from "@/i18n";
import { formatDate, parseTimestamp, relativeTime } from "@/lib/format";
import { useApi, useReferenceData } from "@/services/api/hooks";
import { actNowItemSchema, assigneeSchema, type ActNowItem } from "@/services/api/workspaces";
import { WorkItemDrawer, type WorkItem } from "./WorkItemDrawer";

const RANK: Record<string, number> = { critical: 3, high: 2, medium: 1 };

export function toWorkItem(row: ActNowItem): WorkItem {
  return {
    kind: row.item_type === "community_feedback" ? "grievance" : "case",
    id: row.item_id,
    title: row.title,
    details: row.details,
    cellId: row.cell_id,
  };
}

/** The Act Now queue: open cases and grievances, most urgent first, each one workable in a drawer. */
export function ActionsPage() {
  const { t, lang } = useI18n();
  const { place, schemeName } = useReferenceData();
  const [params, setParams] = useSearchParams();
  const [type, setType] = useState("");
  const [priority, setPriority] = useState("");
  const queue = useApi("analytics/act-now", z.array(actNowItemSchema));
  const staff = useApi("admin/assignees", z.array(assigneeSchema), { staleTime: 5 * 60_000 });
  const staffName = new Map((staff.data ?? []).map((person) => [person.id, person.full_name]));

  // ?open=infrastructure-5 opens that item, so links from the bell and the overview land on it.
  const openKey = params.get("open");
  // Kept once opened: a resolved item leaves the open queue, but its drawer must stay to close the loop.
  const [selected, setSelected] = useState<{ key: string; item: WorkItem } | null>(null);
  useEffect(() => {
    if (!openKey) return setSelected(null);
    const row = queue.data?.find((item) => `${item.item_type}-${item.item_id}` === openKey);
    if (row) setSelected((current) => (current?.key === openKey ? current : { key: openKey, item: toWorkItem(row) }));
  }, [openKey, queue.data]);
  const open = (row: ActNowItem | null) =>
    setParams((current) => {
      const next = new URLSearchParams(current);
      if (row) next.set("open", `${row.item_type}-${row.item_id}`);
      else next.delete("open");
      return next;
    }, { replace: true });

  const rows = (queue.data ?? []).filter(
    (row) => (!type || (type === "grievance") === (row.item_type === "community_feedback")) && (!priority || row.priority === priority),
  );
  const now = Date.now();

  const columns: Column<ActNowItem>[] = [
    {
      key: "title",
      header: t("actions.reportDetails"),
      primary: true,
      render: (row) => (
        <span>
          <span className="block font-semibold text-ink">{row.title}</span>
          {row.details && <span className="line-clamp-1 text-xs text-muted">{row.details}</span>}
        </span>
      ),
      sortValue: (row) => row.title,
    },
    {
      key: "type",
      header: t("label.kind"),
      render: (row) => <Badge tone={row.item_type === "community_feedback" ? "water" : "neutral"}>{t(row.item_type === "community_feedback" ? "actions.grievance" : "actions.case")}</Badge>,
    },
    { key: "priority", header: t("label.priority"), render: (row) => <PriorityBadge priority={row.priority} />, sortValue: (row) => RANK[row.priority] ?? 0 },
    { key: "status", header: t("label.status"), render: (row) => <StatusBadge status={row.status} />, sortValue: (row) => row.status },
    {
      key: "place",
      header: t("actions.place"),
      render: (row) => (
        <span className="text-sm">
          {place(row.cell_id) ?? "—"}
          {row.scheme_id && <span className="block text-xs text-muted">{schemeName.get(row.scheme_id)}</span>}
        </span>
      ),
    },
    {
      key: "owner",
      header: t("actions.assignee"),
      render: (row) =>
        row.assigned_to_account_id ? (staffName.get(row.assigned_to_account_id) ?? `#${row.assigned_to_account_id}`)
          : row.assigned_to_field_user_id ? `#${row.assigned_to_field_user_id}` : <span className="text-muted">{t("actions.unassigned")}</span>,
    },
    {
      key: "due",
      header: t("actions.due"),
      render: (row) => {
        if (!row.due_at) return <span className="text-muted">—</span>;
        const late = parseTimestamp(row.due_at).getTime() < now;
        return late ? <Badge tone="critical">{t("actions.overdue")} · {formatDate(row.due_at, lang)}</Badge> : formatDate(row.due_at, lang);
      },
      sortValue: (row) => row.due_at ?? null,
    },
    { key: "opened", header: t("actions.opened"), render: (row) => relativeTime(row.created_at, lang), sortValue: (row) => row.created_at },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("actions.eyebrow")}
        title={t("actions.title")}
        description={t("actions.description")}
        updatedAt={queue.dataUpdatedAt}
        actions={<Button icon={RefreshCw} onClick={() => void queue.refetch()} loading={queue.isFetching}>{t("filter.refresh")}</Button>}
      />
      <DataTable
          rows={rows}
          columns={columns}
          rowKey={(row) => `${row.item_type}-${row.item_id}`}
          caption={t("actions.title")}
          loading={queue.isPending}
          error={queue.error ? queue.error.message : null}
          onRetry={() => void queue.refetch()}
          emptyMessage={t("actions.empty")}
          searchText={(row) => `${row.title} ${row.details ?? ""} ${place(row.cell_id) ?? ""}`}
          onRowClick={open}
          initialSort={{ key: "priority", direction: "desc" }}
          toolbar={
            <>
              <Select label={t("actions.filterType")} value={type} onChange={setType} options={[
                { value: "", label: t("actions.allTypes") },
                { value: "case", label: t("actions.cases") },
                { value: "grievance", label: t("actions.grievances") },
              ]} />
              <Select label={t("label.priority")} value={priority} onChange={setPriority} options={[
                { value: "", label: t("actions.allPriorities") },
                ...(["critical", "high", "medium"] as const).map((value) => ({ value, label: t(`priority.${value}`) })),
              ]} />
            </>
          }
        />
      <WorkItemDrawer item={selected?.item ?? null} onClose={() => open(null)} />
    </div>
  );
}
