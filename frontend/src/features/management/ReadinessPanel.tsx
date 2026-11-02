import { useOperationsCopy } from "@/i18n/operationsCopy";
import { z } from "zod";
import { useApi } from "@/services/api/hooks";
import { DataState } from "@/components/feedback/DataState";
const schema=z.object({field_crop_reports:z.number(),verified_crop_reports:z.number(),measured_yield_reports:z.number(),
  approved_baseline_versions:z.number(),approved_rainfall_references:z.number(),inventory_without_confirmed_cell:z.number(),
  inactive_or_uncovered_schemes:z.number(),active_administrators:z.number(),limitations:z.array(z.string())});
export function ReadinessPanel(){
  const copy=useOperationsCopy();
  const data=useApi("admin/readiness",schema);
  if(data.isPending)return <DataState kind="loading"/>;
  if(data.error||!data.data)return <DataState kind="error" message={data.error?.message} onRetry={()=>void data.refetch()}/>;
  const r=data.data;
  const rows=[['Field crop reports',r.field_crop_reports],['Verified crop reports',r.verified_crop_reports],['Measured yield reports',r.measured_yield_reports],
    ['Approved baseline versions',r.approved_baseline_versions],['Approved rainfall references',r.approved_rainfall_references],
    ['Assets without confirmed cells',r.inventory_without_confirmed_cell],['Inactive or uncovered schemes',r.inactive_or_uncovered_schemes],['Active staff administrators',r.active_administrators]];
  return <section className="space-y-3 rounded-card border border-line p-5" aria-labelledby="pilot-readiness">
    <h2 id="pilot-readiness" className="text-lg font-bold">{copy("Pilot data readiness")}</h2>
    <dl className="grid gap-3 sm:grid-cols-2">{rows.map(([label,value])=><div key={label} className="rounded-control bg-canvas p-3"><dt className="text-sm text-muted">{copy(String(label))}</dt><dd className="text-xl font-bold">{value}</dd></div>)}</dl>
    <ul className="list-disc space-y-1 pl-5 text-sm text-muted">{r.limitations.map(item=><li key={item}>{copy(item)}</li>)}</ul>
    <p className="text-sm font-semibold">{copy("No ML training or causal-impact claim is authorized by these counts.")}</p>
  </section>;
}
