import { useOperationsCopy } from "@/i18n/operationsCopy";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { z } from "zod";
import { DataTable, type Column } from "@/components/data/DataTable";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Overlay";
import { TextField } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n";
import { apiSend } from "@/services/api/client";
import { useApi, useReferenceData } from "@/services/api/hooks";
import { cellSchema } from "@/services/api/workspaces";

import { ReadinessPanel } from "./ReadinessPanel";

const rowSchema = z.object({
  id: z.number(), is_active: z.boolean(), code: z.string().optional(),
  label_en: z.string().optional(), label_rw: z.string().optional(), sort_order: z.number().optional(),
  name_en: z.string().optional(), name_rw: z.string().optional(), asset_type: z.string().nullable().optional(),
  scheme_id: z.number().nullable().optional(), cell_id: z.number().nullable().optional(),
});
type Row = z.infer<typeof rowSchema>;
type Kind = "categories" | "assets";
const endpoints = { categories: "grievance-categories", assets: "scheme-assets" };

function Editor({ kind, row, onClose }: { kind: Kind; row: Row | null; onClose: () => void }) {
  const copy=useOperationsCopy();
  const { t } = useI18n();
  const toast = useToast();
  const client = useQueryClient();
  const { schemes, place } = useReferenceData();
  const cells = useApi("cells", z.array(cellSchema));
  const [scheme, setScheme] = useState(row?.scheme_id?.toString() ?? "");
  const [cell, setCell] = useState(row?.cell_id?.toString() ?? "");
  const save = useMutation({
    mutationFn: (body: Record<string, unknown>) => apiSend(row ? "PATCH" : "POST", `${endpoints[kind]}${row ? `/${row.id}` : ""}`, body),
    onSuccess: () => { toast.success(copy("Reference entry saved")); void client.invalidateQueries({ queryKey: ["api"] }); onClose(); },
    onError: (error: Error) => toast.error(error.message),
  });
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const value = (name: string) => String(form.get(name) ?? "").trim();
    const body: Record<string, unknown> = { is_active: form.get("active") === "on" };
    if (kind === "assets") Object.assign(body, { name_en: value("en"), name_rw: value("rw"),
      scheme_id: scheme ? Number(scheme) : null, cell_id: cell ? Number(cell) : null, asset_type: value("type") || null });
    else Object.assign(body, { label_en: value("en"), label_rw: value("rw"), sort_order: Number(value("order") || 0),
      ...(!row && value("code") ? { code: value("code") } : {}) });
    save.mutate(body);
  };
  return <Drawer open onClose={onClose} title={copy(kind === "assets" ? "Asset inventory" : "Grievance category")}
    footer={<Button type="submit" form="reference-editor" variant="primary" loading={save.isPending}>{t("action.save")}</Button>}>
    <form id="reference-editor" onSubmit={submit} className="space-y-4">
      <p className="text-sm text-muted">{copy("Enter district-confirmed reference information. Deactivate retired entries to preserve report history.")}</p>
      <TextField label={copy("English label")} name="en" defaultValue={row?.name_en ?? row?.label_en ?? ""} required maxLength={kind === "assets" ? 120 : 80} />
      <TextField label={copy("Kinyarwanda label")} name="rw" defaultValue={row?.name_rw ?? row?.label_rw ?? ""} required maxLength={120} />
      {kind === "assets" ? <>
        <Select label={copy("Irrigation scheme")} value={scheme} onChange={setScheme} options={[{value:"",label:copy("Unassigned")}, ...schemes.map(s => ({value:String(s.id), label:s.name}))]} />
        <Select label={copy("Asset cell")} value={cell} onChange={setCell} options={[{value:"",label:copy("Location not confirmed")}, ...(cells.data ?? []).map(c => ({value:String(c.id), label:place(c.id) ?? c.name}))]} />
        <TextField label={copy("Asset type")} name="type" defaultValue={row?.asset_type ?? ""} maxLength={40} />
      </> : <>
        {!row && <TextField label={copy("Category code (optional)")} name="code" maxLength={40} />}
        <TextField label={copy("Menu order")} name="order" type="number" min={0} max={999} defaultValue={row?.sort_order ?? 0} />
      </>}
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="active" defaultChecked={row?.is_active ?? true} />{copy("Active in phone menus")}</label>
    </form>
  </Drawer>;
}

export function ManagementPage() {
  const copy=useOperationsCopy();
  const { t, lang } = useI18n();
  const [kind, setKind] = useState<Kind>("assets");
  const [editing, setEditing] = useState<Row | null | undefined>(undefined);
  const query = useApi(endpoints[kind], z.array(rowSchema));
  const { schemeName, place } = useReferenceData();
  const columns: Column<Row>[] = [
    {key:"name",header:copy("Reference entry"),primary:true,render:r => (lang === "rw" ? r.name_rw ?? r.label_rw : r.name_en ?? r.label_en) ?? "—"},
    {key:"rw",header:copy("Kinyarwanda"),render:r => r.name_rw ?? r.label_rw ?? "—"},
    {key:"location",header:copy(kind === "assets" ? "Scheme / location" : "Menu order"),render:r => kind === "assets" ? `${schemeName.get(r.scheme_id ?? 0) ?? "Unassigned"} · ${place(r.cell_id) ?? "Location not confirmed"}` : r.sort_order},
    {key:"status",header:t("label.status"),render:r => <Badge tone={r.is_active ? "good" : "neutral"}>{copy(r.is_active ? "Active" : "Inactive")}</Badge>},
  ];
  return <div className="space-y-6">
    <PageHeader eyebrow={copy("Administration")} title={copy("Platform management")} description={copy("Maintain the reference lists used in phone reporting and infrastructure monitoring.")} />
    <div role="tablist" aria-label={copy("Reference lists")} className="flex flex-wrap gap-2">
      {(["assets","categories"] as const).map(tab => <button key={tab} role="tab" aria-selected={kind === tab} onClick={() => {setKind(tab); setEditing(undefined);}}
        className="rounded-control border border-line px-4 py-2 text-sm font-semibold">{copy(tab === "assets" ? "Asset inventory" : "Grievance categories")}</button>)}
    </div>
    <Button variant="primary" onClick={() => setEditing(null)}>{copy(kind === "assets" ? "Add asset" : "Add category")}</Button>
    <DataTable rows={query.data} columns={columns} rowKey={r => r.id} caption={copy(kind === "assets" ? "Asset inventory" : "Grievance categories")}
      loading={query.isPending} error={query.error?.message} onRetry={() => void query.refetch()} emptyMessage={copy("No reference entries. Add district-confirmed entries to get started.")}
      onRowClick={setEditing} searchText={r => `${r.name_en ?? r.label_en} ${r.name_rw ?? r.label_rw}`} />
    <ReadinessPanel />
    <p className="text-sm text-muted"><a className="underline" href="/management.html">{copy("Other registry tools")}</a> remain available for field users and historical records.</p>
    {editing !== undefined && <Editor key={`${kind}-${editing?.id ?? "new"}`} kind={kind} row={editing} onClose={() => setEditing(undefined)} />}
  </div>;
}
