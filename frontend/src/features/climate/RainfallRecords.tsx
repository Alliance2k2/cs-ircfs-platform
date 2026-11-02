import { lazy, Suspense, useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { useSession } from "@/app/providers/SessionProvider";
import { DataTable } from "@/components/data/DataTable";
import { DataState } from "@/components/feedback/DataState";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { TextField } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/Toast";
import { useApi, useReferenceData, withParams } from "@/services/api/hooks";
import { apiSend } from "@/services/api/client";
import { rainfallAnalysisSchema, rainfallReferenceSchema } from "@/services/api/climateMaintenance";

const RainfallChart = lazy(() => import("./RainfallChart"));
const dateOnly = (date: Date) => new Intl.DateTimeFormat("en-CA", { timeZone: "Africa/Kigali", year: "numeric", month: "2-digit", day: "2-digit" }).format(date);

export function RainfallRecords() {
  const { role } = useSession();
  const { sectors, schemes } = useReferenceData();
  const toast = useToast();
  const client = useQueryClient();
  const [start, setStart] = useState(() => dateOnly(new Date(Date.now() - 29 * 86400000)));
  const [end, setEnd] = useState(() => dateOnly(new Date()));
  const [location, setLocation] = useState("");
  const [reference, setReference] = useState("");
  const [approveDate, setApproveDate] = useState("");
  const references = useApi("climate/references", z.array(rainfallReferenceSchema));
  const [kind, id] = location.split(":");
  const analysis = useApi(withParams("climate/rainfall", { start, end, sector_id: kind === "sector" ? id : "", scheme_id: kind === "scheme" ? id : "", reference_id: reference }), rainfallAnalysisSchema);
  const save = useMutation({
    mutationFn: ({ path, body }: { path: string; body: unknown }) => apiSend("POST", path, body),
    onSuccess: () => { toast.success("Reference saved"); void client.invalidateQueries({ queryKey: ["api"] }); },
    onError: (error: Error) => toast.error(error.message),
  });
  const submitReference = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    save.mutate({ path: "climate/references", body: {
      sector_id: kind === "sector" ? Number(id) : null, scheme_id: kind === "scheme" ? Number(id) : null,
      period_start: start, period_end: end, reference_start_year: Number(form.get("from")), reference_end_year: Number(form.get("to")),
      mean_rainfall_mm: Number(form.get("mean")), source: form.get("source"), document_reference: form.get("document"),
    } });
  };
  const chooseReference = (value: string) => {
    setReference(value);
    const ref = references.data?.find((r) => String(r.id) === value);
    if (ref) { setStart(ref.period_start); setEnd(ref.period_end); setLocation(ref.sector_id ? `sector:${ref.sector_id}` : `scheme:${ref.scheme_id}`); }
  };
  const data = analysis.data;
  const mm = (value: number | null) => value === null ? "Missing" : `${value} mm`;
  return <Card className="space-y-4 p-5">
    <h2 className="text-lg font-bold">Daily and seasonal rainfall evidence</h2>
    <p className="text-sm text-muted">Recorded zero is distinct from missing rain. Partial totals are not complete seasonal rainfall. Historical comparisons require approved sources and complete verified gauge records.</p>
    <div className="flex flex-wrap items-end gap-3">
      <TextField label="Rainfall period start" type="date" value={start} onChange={(e) => { setStart(e.target.value); setReference(""); }} />
      <TextField label="Rainfall period end" type="date" value={end} onChange={(e) => { setEnd(e.target.value); setReference(""); }} />
      <Select label="Rainfall location" value={location} onChange={(v) => { setLocation(v); setReference(""); }} options={[
        { value: "", label: "Accessible reporting area" }, ...sectors.map((s) => ({ value: `sector:${s.id}`, label: `Sector: ${s.name}` })), ...schemes.map((s) => ({ value: `scheme:${s.id}`, label: `Scheme: ${s.name}` })),
      ]} />
      <Select label="Historical rainfall reference" value={reference} onChange={chooseReference} options={[
        { value: "", label: "No reference selected" }, ...(references.data ?? []).map((r) => ({ value: String(r.id), label: `#${r.id} ${r.reference_start_year}-${r.reference_end_year}: ${r.source}` })),
      ]} />
      <Button onClick={() => void analysis.refetch()} loading={analysis.isFetching}>Refresh rainfall</Button>
    </div>
    {references.error && <DataState kind="error" message={references.error.message} onRetry={() => void references.refetch()} />}
    {analysis.isPending ? <DataState kind="loading" /> : analysis.error || !data ? <DataState kind="error" message={analysis.error?.message} onRetry={() => void analysis.refetch()} /> : <>
      <dl className="grid gap-3 text-sm sm:grid-cols-3">
        <div><dt>Partial period total (daily means)</dt><dd className="font-bold">{mm(data.summary.partial_total_mm)}</dd></div>
        <div><dt>Seven-day partial total ending {data.end}</dt><dd className="font-bold">{mm(data.seven_day.partial_total_mm)} / {data.seven_day.missing_days} missing days</dd></div>
        <div><dt>Complete verified gauge total</dt><dd className="font-bold">{mm(data.summary.verified_complete_total_mm)} / {data.summary.complete_verified_gauges} gauges</dd></div>
        <div><dt>Missing days</dt><dd>{data.summary.missing_days}</dd></div>
        <div><dt>Coverage among observed gauges</dt><dd>{data.summary.coverage_percent === null ? "Missing" : `${data.summary.coverage_percent}%`}</dd></div>
        <div><dt>Legacy receipt dates / unidentified reports</dt><dd>{data.summary.legacy_date_reports} / {data.summary.unknown_gauge_reports}</dd></div>
      </dl>
      <p role="status" className="rounded-control bg-canvas p-3 text-sm">Rainfall anomaly: {data.anomaly.status.replaceAll("_", " ")}
        {data.anomaly.difference_mm !== null && ` | ${data.anomaly.difference_mm} mm`}{data.anomaly.percent !== null && ` | ${data.anomaly.percent}%`}
        {data.anomaly.reference && <span className="block text-xs">{data.anomaly.reference.source} | {data.anomaly.reference.document_reference} | {data.anomaly.reference.reference_start_year}-{data.anomaly.reference.reference_end_year}</span>}
      </p>
      <p className="text-xs text-muted">{data.summary.method}</p>
      <p className="text-xs text-muted">Generated: {new Date(data.generated_at).toLocaleString("en-GB", { timeZone: "Africa/Kigali" })} (Kigali)</p>
      <Suspense fallback={<DataState kind="loading" compact />}><RainfallChart daily={data.summary.daily} /></Suspense>
      <DataTable rows={data.summary.daily} rowKey={(r) => r.date} caption="Daily rainfall observations" emptyMessage="No rainfall observations" searchText={(r) => r.date} columns={[
        { key: "date", header: "Date", render: (r) => r.date }, { key: "mean", header: "Mean rainfall", render: (r) => mm(r.mean_mm) },
        { key: "gauges", header: "Reporting gauges", render: (r) => r.gauges }, { key: "verified", header: "Verified and sourced", render: (r) => r.verified_gauges },
      ]} />
      <div className="grid gap-4 sm:grid-cols-2">{[["By sector", data.by_sector], ["By irrigation scheme", data.by_scheme]].map(([label, groups]) => (
        <section key={String(label)}><h3 className="text-sm font-bold">{String(label)}</h3><ul className="text-sm">{(groups as typeof data.by_sector).map((g) => <li key={g.id ?? "none"}>{g.name}: {mm(g.partial_total_mm)} | {g.missing_days} missing days</li>)}</ul></section>
      ))}</div>
    </>}
    {role === "administrator" && <details className="rounded-control border border-line p-4">
      <summary className="cursor-pointer font-semibold">Historical reference documents and approval</summary>
      <p className="my-3 text-sm text-muted">Uses the selected location and comparison dates above. Enter a documented historical mean for exactly this period. No historical value is inferred.</p>
      <form onSubmit={submitReference} className="grid gap-3 sm:grid-cols-2">
        <TextField label="Reference first year" name="from" type="number" required min={1900} max={2100} />
        <TextField label="Reference last year" name="to" type="number" required min={1900} max={2100} />
        <TextField label="Historical mean total (mm)" name="mean" type="number" required min={0} max={100000} step="any" />
        <TextField label="Rainfall reference source" name="source" required maxLength={255} />
        <TextField label="Rainfall source document" name="document" required maxLength={255} />
        <Button type="submit" disabled={!location} loading={save.isPending}>Save rainfall reference</Button>
      </form>
      <TextField label="Rainfall reference approval date" type="date" value={approveDate} onChange={(e) => setApproveDate(e.target.value)} />
      <ul className="mt-3 space-y-2 text-sm">{references.data?.map((r) => <li key={r.id}>#{r.id}: {r.source} | {r.document_reference} | {r.approved_at ?? "Unapproved"}
        {!r.approved_at && r.data_origin !== "demo" && <Button size="sm" disabled={!approveDate} loading={save.isPending} onClick={() => save.mutate({ path: `climate/references/${r.id}/approve`, body: { approved_at: approveDate } })}>Approve rainfall reference #{r.id}</Button>}
      </li>)}</ul>
    </details>}
  </Card>;
}
