import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { isStaff, useSession } from "@/app/providers/SessionProvider";
import { DataTable } from "@/components/data/DataTable";
import { DataState } from "@/components/feedback/DataState";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { TextArea, TextField } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/Toast";
import { apiSend } from "@/services/api/client";
import { useApi, withParams } from "@/services/api/hooks";
import { maintenanceHistorySchema } from "@/services/api/climateMaintenance";

const dateOnly = (date: Date) => new Intl.DateTimeFormat("en-CA", { timeZone: "Africa/Kigali", year: "numeric", month: "2-digit", day: "2-digit" }).format(date);
const displayTime = (value: string) => new Date(value).toLocaleString("en-GB", { timeZone: "Africa/Kigali" });
const kigaliTime = (value: FormDataEntryValue | null) => new Date(`${String(value)}+02:00`).toISOString();

export function MaintenancePanel() {
  const { role } = useSession();
  const toast = useToast();
  const client = useQueryClient();
  const [start, setStart] = useState(() => dateOnly(new Date(Date.now() - 89 * 86400000)));
  const [end, setEnd] = useState(() => dateOnly(new Date()));
  const history = useApi(withParams("irrigation/maintenance", { start, end }), maintenanceHistorySchema);
  const [assetId, setAssetId] = useState("");
  const [outageId, setOutageId] = useState("");
  const [category, setCategory] = useState("technical");
  const [kind, setKind] = useState("inspection");
  const [restored, setRestored] = useState(false);
  const selected = history.data?.assets.find((a) => String(a.id) === assetId);
  const save = useMutation({
    mutationFn: ({ path, body }: { path: string; body: unknown }) => apiSend("POST", path, body),
    onSuccess: () => { toast.success("Maintenance record saved"); setOutageId(""); setRestored(false); void client.invalidateQueries({ queryKey: ["api"] }); },
    onError: (error: Error) => toast.error(error.message),
  });
  const submit = (event: FormEvent<HTMLFormElement>, type: "outage" | "maintenance") => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const common = { asset_id: Number(assetId), cell_id: selected?.cell_id ?? null, source: form.get("source") };
    const body = type === "outage" ? { ...common, started_at: kigaliTime(form.get("time")), category, description: form.get("description") }
      : { ...common, performed_at: kigaliTime(form.get("time")), kind, action: form.get("action"), outage_id: outageId ? Number(outageId) : null, restored };
    save.mutate({ path: type === "outage" ? "irrigation/outages" : "irrigation/maintenance", body });
  };
  return <Card className="space-y-4 p-5">
    <h2 className="text-lg font-bold">Recorded downtime and maintenance</h2>
    <p className="text-sm text-muted">Durations use recorded outage starts and repairs. Condition reports alone do not establish downtime. No records means unknown, not uninterrupted service.</p>
    <div className="flex flex-wrap items-end gap-3">
      <TextField label="Maintenance period start" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
      <TextField label="Maintenance period end" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
      <Button onClick={() => void history.refetch()} loading={history.isFetching}>Refresh maintenance</Button>
    </div>
    {history.isPending ? <DataState kind="loading" /> : history.error ? <DataState kind="error" message={history.error.message} onRetry={() => void history.refetch()} /> : <>
      <p className="text-xs text-muted">{history.data.method} Open durations calculated through {displayTime(history.data.as_of)} (Kigali).</p>
      <DataTable rows={history.data.assets} rowKey={(a) => a.id} caption="Recorded asset downtime" emptyMessage="No inventory assets in your reporting area" searchText={(a) => `${a.name} ${a.scheme ?? ""}`} columns={[
        { key: "asset", header: "Inventory asset", render: (a) => `${a.name} | ${a.scheme ?? "Unassigned"}` },
        { key: "hours", header: "Recorded downtime", render: (a) => a.recorded_downtime_hours === null ? "Unknown" : `${a.recorded_downtime_hours} hours` },
        { key: "outages", header: "Recorded / open outages", render: (a) => `${a.outage_count} / ${a.open_outages}` },
        { key: "recurring", header: "Recurring categories (3+)", render: (a) => a.recurrent_categories.join(", ") || "None recorded" },
      ]} />
      <Select label="Maintenance inventory asset" value={assetId} onChange={(v) => { setAssetId(v); setOutageId(""); setRestored(false); }} options={[
        { value: "", label: "Choose inventory asset" }, ...history.data.assets.map((a) => ({ value: String(a.id), label: `${a.name} | ${a.scheme ?? "Unassigned"}` })),
      ]} />
      {selected && <>
        <h3 className="font-semibold">{selected.name}: outage history</h3>
        <ul className="space-y-2 text-sm">{selected.outages.map((o) => <li key={o.id} className="rounded-control bg-canvas p-3">
          #{o.id}: {displayTime(o.started_at)} - {o.ended_at ? displayTime(o.ended_at) : "Ongoing"} | {o.category} | {o.repair_status}
          <p>{o.description}</p><p className="text-xs text-muted">Source: {o.source}</p>
        </li>)}</ul>
        <h3 className="font-semibold">Maintenance history</h3>
        {!selected.maintenance.length && <p className="text-sm text-muted">No maintenance records in this period.</p>}
        <ul className="space-y-2 text-sm">{selected.maintenance.map((e) => <li key={e.id}>{displayTime(e.performed_at)} | {e.kind} | {e.restored ? "Service restored" : "Restoration not recorded"}
          <p>{e.action}</p><p className="text-xs text-muted">Source: {e.source}</p>
        </li>)}</ul>
      </>}
      {isStaff(role) && selected && <div className="grid gap-4 lg:grid-cols-2">
        <form onSubmit={(e) => submit(e, "outage")} className="space-y-3 rounded-control border border-line p-4">
          <h3 className="font-semibold">Record an outage</h3>
          <TextField label="Outage start (Kigali time)" name="time" type="datetime-local" required />
          <Select label="Outage bottleneck category" value={category} onChange={setCategory} options={["technical", "social", "institutional", "environmental"].map((value) => ({ value, label: value }))} />
          <TextArea label="Outage description" name="description" required maxLength={2000} />
          <TextField label="Outage source" name="source" required maxLength={255} />
          <Button type="submit" loading={save.isPending}>Save outage</Button>
        </form>
        <form onSubmit={(e) => submit(e, "maintenance")} className="space-y-3 rounded-control border border-line p-4">
          <h3 className="font-semibold">Record maintenance or repair</h3>
          <Select label="Related open outage" value={outageId} onChange={(v) => { setOutageId(v); setRestored(false); }} options={[
            { value: "", label: "Independent maintenance" }, ...selected.outages.filter((o) => o.ended_at === null).map((o) => ({ value: String(o.id), label: `#${o.id} ${o.category}` })),
          ]} />
          <Select label="Maintenance type" value={kind} onChange={(v) => { setKind(v); setRestored(false); }} options={["inspection", "preventive", "repair"].map((value) => ({ value, label: value }))} />
          <TextField label="Maintenance performed (Kigali time)" name="time" type="datetime-local" required />
          <TextArea label="Maintenance action" name="action" required maxLength={2000} />
          <TextField label="Maintenance source" name="source" required maxLength={255} />
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={restored} disabled={kind !== "repair" || !outageId} onChange={(e) => setRestored(e.target.checked)} />Service restored by this repair</label>
          <Button type="submit" loading={save.isPending}>Save maintenance</Button>
        </form>
      </div>}
    </>}
  </Card>;
}
