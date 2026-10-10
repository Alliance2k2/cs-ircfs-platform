import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, RefreshCw, Save } from "lucide-react";
import { useState, type FormEvent } from "react";
import { z } from "zod";
import { canAccess } from "@/app/access";
import { useSession } from "@/app/providers/SessionProvider";
import { DataTable, type Column } from "@/components/data/DataTable";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { SelectField, TextField } from "@/components/ui/Field";
import { Drawer } from "@/components/ui/Overlay";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n";
import { formatNumber, relativeTime } from "@/lib/format";
import { apiSend } from "@/services/api/client";
import { useApi, useReferenceData } from "@/services/api/hooks";
import { participationSchema, trainingSchema } from "@/services/api/workspaces";

type Row = z.infer<typeof participationSchema>;
const cooperativeSchema = z.object({ id: z.number(), name: z.string(), sector_id: z.number().nullable(), irrigation_scheme_id: z.number().nullable(), is_pilot: z.boolean() });
type Cooperative = z.infer<typeof cooperativeSchema>;

function Progress({ label, value, target, note }: { label: string; value: number; target: number; note?: string }) {
  const percent = target ? Math.min(100, Math.round((value / target) * 100)) : 0;
  return (
    <Card className="p-5">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 font-heading text-2xl font-extrabold">
        {value} <span className="text-base font-semibold text-muted">/ {target}</span>
      </p>
      <div className="mt-3 h-2 rounded-full bg-canvas" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={target} aria-valuenow={value}>
        <div className="h-2 rounded-full bg-primary" style={{ width: `${Math.max(percent, 2)}%` }} />
      </div>
      {note && <p className="mt-2 text-xs text-muted">{note}</p>}
    </Card>
  );
}

function CooperativeForm({ cooperative, onClose }: { cooperative: Cooperative | "new" | null; onClose: () => void }) {
  const { t } = useI18n();
  const toast = useToast();
  const client = useQueryClient();
  const { sectors, schemes } = useReferenceData();
  const existing = cooperative && cooperative !== "new" ? cooperative : null;
  const [name, setName] = useState(existing?.name ?? "");
  const [sector, setSector] = useState(existing?.sector_id ? String(existing.sector_id) : "");
  const [scheme, setScheme] = useState(existing?.irrigation_scheme_id ? String(existing.irrigation_scheme_id) : "");
  const [pilot, setPilot] = useState(existing?.is_pilot ?? false);
  const [error, setError] = useState<string | undefined>();

  const save = useMutation({
    mutationFn: () => {
      const body = { name: name.trim(), sector_id: sector ? Number(sector) : null, irrigation_scheme_id: scheme ? Number(scheme) : null, is_pilot: pilot };
      return existing ? apiSend("PATCH", `cooperatives/${existing.id}`, body) : apiSend("POST", "cooperatives", body);
    },
    onSuccess: () => {
      toast.success(t("coops.saved"));
      void client.invalidateQueries({ queryKey: ["api"] });
      onClose();
    },
    onError: (failure: Error) => toast.error(failure.message),
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (name.trim().length < 2) return setError(t("coops.nameHint"));
    setError(undefined);
    save.mutate();
  };

  return (
    <Drawer
      open={cooperative !== null}
      onClose={onClose}
      title={existing ? existing.name : t("coops.new")}
      footer={<Button variant="primary" icon={Save} type="submit" form="coop-form" loading={save.isPending}>{t("action.save")}</Button>}
    >
      <form id="coop-form" onSubmit={submit} className="space-y-4" noValidate>
        <TextField label={t("admin.name")} value={name} required error={error} maxLength={120} onChange={(event) => setName(event.target.value)} />
        <SelectField label={t("label.sector")} value={sector} onChange={(event) => setSector(event.target.value)}
          options={[{ value: "", label: t("label.none") }, ...sectors.map((item) => ({ value: String(item.id), label: item.name }))]} />
        <SelectField label={t("label.scheme")} value={scheme} onChange={(event) => setScheme(event.target.value)}
          options={[{ value: "", label: t("label.none") }, ...schemes.map((item) => ({ value: String(item.id), label: item.name }))]} />
        <label className="flex items-center gap-2 text-sm font-semibold">
          <input type="checkbox" checked={pilot} onChange={(event) => setPilot(event.target.checked)} className="h-4 w-4 accent-[rgb(var(--primary))]" />
          {t("coops.pilotFlag")}
        </label>
      </form>
    </Drawer>
  );
}

/** Participation by cooperative and progress on training Citizen Science Monitors. */
export function CooperativesPage() {
  const { t, lang } = useI18n();
  const { role } = useSession();
  const { sectorName } = useReferenceData();
  const participation = useApi("cooperatives/participation", z.array(participationSchema));
  const training = useApi("cooperatives/training-progress", trainingSchema);
  const cooperatives = useApi("cooperatives", z.array(cooperativeSchema));
  const [editing, setEditing] = useState<Cooperative | "new" | null>(null);
  const editor = canAccess(role, "planner");

  const columns: Column<Row>[] = [
    {
      key: "name", header: t("admin.name"), primary: true, sortValue: (row) => row.name,
      render: (row) => (
        <span className="flex flex-wrap items-center gap-2">
          <span className="font-semibold">{row.name}</span>
          {row.is_pilot && <Badge tone="brand">{t("coops.pilotBadge")}</Badge>}
        </span>
      ),
    },
    { key: "sector", header: t("label.sector"), render: (row) => (row.sector_id ? sectorName.get(row.sector_id) ?? "—" : "—") },
    { key: "members", header: t("coops.members"), render: (row) => row.members, sortValue: (row) => row.members },
    { key: "champions", header: t("coops.champions"), render: (row) => row.data_champions, sortValue: (row) => row.data_champions },
    { key: "reports", header: t("coops.reports30"), render: (row) => row.reports_30d, sortValue: (row) => row.reports_30d },
    { key: "active", header: t("coops.active"), render: (row) => row.active_reporters_30d, sortValue: (row) => row.active_reporters_30d },
    { key: "last", header: t("coops.lastReport"), render: (row) => (row.last_report_at ? relativeTime(row.last_report_at, lang) : "—"), sortValue: (row) => row.last_report_at },
  ];
  const tr = training.data;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("coops.eyebrow")}
        title={t("coops.title")}
        description={t("coops.description")}
        updatedAt={participation.dataUpdatedAt}
        actions={
          <>
            <Button icon={RefreshCw} onClick={() => { void participation.refetch(); void training.refetch(); }} loading={participation.isFetching}>{t("filter.refresh")}</Button>
            {editor && <Button variant="primary" icon={Plus} onClick={() => setEditing("new")}>{t("coops.new")}</Button>}
          </>
        }
      />
      {tr && (
        <div className="grid gap-4 md:grid-cols-3">
          <Progress label={t("coops.training")} value={tr.trained_monitors} target={tr.target} note={t("coops.trainingNote", { total: tr.monitors_total, percent: formatNumber(tr.percent, lang) })} />
          <Progress label={t("coops.pilot")} value={tr.pilot_cooperatives} target={tr.pilot_target} />
          <Card className="p-5">
            <p className="text-sm text-muted">{t("coops.champions")}</p>
            <p className="mt-1 font-heading text-2xl font-extrabold">{tr.data_champions}</p>
          </Card>
        </div>
      )}
      <DataTable
          rows={participation.data}
          columns={columns}
          rowKey={(row) => row.id}
          caption={t("coops.title")}
          loading={participation.isPending}
          error={participation.error ? participation.error.message : null}
          onRetry={() => void participation.refetch()}
          emptyMessage={t("coops.empty")}
          searchText={(row) => row.name}
          onRowClick={editor ? (row) => setEditing(cooperatives.data?.find((item) => item.id === row.id) ?? null) : undefined}
          initialSort={{ key: "reports", direction: "desc" }}
        />
      {editing !== null && <CooperativeForm key={editing === "new" ? "new" : editing.id} cooperative={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}
