import { useOperationsCopy } from "@/i18n/operationsCopy";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { z } from "zod";
import { DataTable, type Column } from "@/components/data/DataTable";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Overlay";
import { TextField } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/Toast";
import { apiSend } from "@/services/api/client";
import { useApi } from "@/services/api/hooks";

const deliveryRow = z.object({kind:z.enum(["sms","airtime"]),id:z.number(),status:z.string(),phone_number:z.string(),
  provider_id:z.string().nullable(),delivery_attempts:z.number(),last_attempt_at:z.string().nullable(),created_at:z.string()});
const queueSchema = z.object({rows:z.array(deliveryRow),totals:z.record(z.record(z.number())),unmatched_receipts:z.number()});
type Delivery = z.infer<typeof deliveryRow>;

function ReconcileForm({ item, onClose }: { item:Delivery; onClose:()=>void }) {
  const copy=useOperationsCopy();
  const toast=useToast();
  const client=useQueryClient();
  const [action,setAction]=useState(item.status === "queued" ? "cancel" : "accepted");
  const blocked=["dry_run","delivered","dispatching","cancelled"].includes(item.status);
  const save=useMutation({
    mutationFn:(body:unknown)=>apiSend("POST",`delivery/${item.kind}/${item.id}/reconcile`,body),
    onSuccess:()=>{toast.success(copy("Delivery review recorded"));void client.invalidateQueries({queryKey:["api"]});onClose();},
    onError:(error:Error)=>toast.error(error.message),
  });
  const submit=(event:FormEvent<HTMLFormElement>)=>{
    event.preventDefault();
    const values=new FormData(event.currentTarget);
    save.mutate({action,reference:String(values.get("reference")??"").trim(),provider_id:String(values.get("provider")??"").trim()||null,
      confirmed_not_sent:values.get("not-sent")==="on"});
  };
  return <Drawer open onClose={onClose} title={copy("Review {kind} #{id}",{kind:item.kind,id:item.id})}>
    <p className="mb-4 text-sm text-muted">{copy("Check the provider's transaction record first. Requeueing may cause another charge. Never requeue an uncertain transaction without confirmation that it was not sent.")}</p>
    {blocked ? <p role="status">{copy("This state cannot be manually changed: {status}.",{status:item.status})}</p> : <form onSubmit={submit} className="space-y-4">
      <Select label={copy("Review outcome")} value={action} onChange={setAction} options={item.status==="queued" ? [{value:"cancel",label:copy("Cancel queued item")}] : [
        {value:"accepted",label:copy("Provider confirmed acceptance")},{value:"delivered",label:copy("Provider confirmed delivery")},{value:"failed",label:copy("Provider confirmed failure")},
        {value:"requeue",label:copy("Requeue after provider confirmed nothing was sent")},{value:"cancel",label:copy("Cancel unsent item")}]} />
      <TextField label={copy("Provider transaction ID")} name="provider" defaultValue={item.provider_id??""} maxLength={120} required={action==="accepted"||action==="delivered"} />
      <TextField label={copy("Evidence reference (no phone numbers or message text)")} name="reference" minLength={5} maxLength={255} required />
      {action==="requeue"&&<label className="flex items-start gap-2 text-sm"><input type="checkbox" name="not-sent" required />{copy("I checked the provider and confirmed this transaction was not sent.")}</label>}
      <Button type="submit" variant="primary" loading={save.isPending}>{copy("Record review")}</Button>
    </form>}
  </Drawer>;
}

export function DeliveryOperations() {
  const copy=useOperationsCopy();
  const data=useApi("delivery/queue",queueSchema,{refetchInterval:15_000});
  const [selected,setSelected]=useState<Delivery|null>(null);
  const columns:Column<Delivery>[]=[
    {key:"id",header:copy("Delivery reference"),primary:true,render:r=>`${r.kind} #${r.id}`},
    {key:"status",header:copy("Status"),render:r=>r.status},
    {key:"phone",header:copy("Recipient"),render:r=>r.phone_number},
    {key:"provider",header:copy("Provider ID"),render:r=>r.provider_id??"Not recorded"},
    {key:"attempts",header:copy("Attempts"),render:r=>r.delivery_attempts},
  ];
  return <section className="space-y-3 rounded-card border border-line p-4" aria-labelledby="delivery-operations">
    <h2 id="delivery-operations" className="text-lg font-bold">{copy("Delivery review")}</h2>
    <p className="text-sm text-muted">{copy("Only provider receipts or an audited operator review establish final delivery. Duplicate or late callbacks cannot regress a delivered transaction.")}</p>
    {data.data&&<p role="status" className="text-sm">{copy("Unmatched provider receipts: {receipts}. Unknown outcomes: {unknown}.",{receipts:data.data.unmatched_receipts,unknown:(data.data.totals.sms?.unknown??0)+(data.data.totals.airtime?.unknown??0)})}</p>}
    <DataTable rows={data.data?.rows} columns={columns} rowKey={r=>`${r.kind}-${r.id}`} caption={copy("Delivery queue")} emptyMessage={copy("No delivery records.")}
      searchText={r=>`${r.kind} ${r.id} ${r.status} ${r.phone_number} ${r.provider_id??""}`}
      loading={data.isPending} error={data.error?.message} onRetry={()=>void data.refetch()} onRowClick={setSelected} />
    {selected&&<ReconcileForm item={selected} onClose={()=>setSelected(null)} />}
  </section>;
}
