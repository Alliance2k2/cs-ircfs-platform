import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { TextField, TextArea } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n";
import { apiSend } from "@/services/api/client";
import type { FieldReportDetail } from "@/services/api/workspaces";

export function CorrectionForm({ report, onSaved }: { report: FieldReportDetail; onSaved: () => void }) {
  const { t } = useI18n();
  const toast = useToast();
  const client = useQueryClient();
  const [unit, setUnit] = useState(report.harvest_unit ?? "t");
  const [observation, setObservation] = useState(report.observation_type ?? "farmer_estimate");
  const save = useMutation({
    mutationFn: (body: unknown) => apiSend("POST", `field-reports/${report.source}/${report.id}/corrections`, body),
    onSuccess: () => {
      toast.success(t("science.corrected"));
      void client.invalidateQueries({ queryKey: ["api"] });
      onSaved();
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const text = (key: string) => String(form.get(key) ?? "").trim() || null;
    const number = (key: string) => text(key) === null ? null : Number(text(key));
    const changes = report.source === "crop" ? {
      crop_type: text("crop"), season: text("season"), reference_year: number("year"),
      cultivated_area_hectares: number("cultivated"), harvested_area_hectares: number("harvested"),
      observed_quantity: number("quantity"), harvest_unit: number("quantity") === null ? null : unit,
      // The backend converts the supplied quantity, avoiding a conflict with the old canonical tonnes.
      reported_harvest_tons: null, harvest_date: text("harvestDate"), data_source: text("source"), observation_type: observation,
    } : { observation_date: text("observationDate"), gauge_code: text("gauge"), data_source: text("source"), rainfall_mm: number("rainfall"), operational_status: text("condition"), fault_description: text("fault") };
    save.mutate({ reason: text("reason"), changes });
  };
  return (
    <form onSubmit={submit} className="space-y-3 rounded-control border border-line p-4">
      <h3 className="text-sm font-bold">{t("science.correction")}</h3>
      <p className="text-xs text-muted">{t("science.correctionHint")}</p>
      {report.source === "crop" ? <>
        <TextField label={t("science.crop")} name="crop" required defaultValue={report.crop ?? ""} maxLength={80} />
        <TextField label={t("science.season")} name="season" defaultValue={report.season ?? ""} maxLength={20} />
        <TextField label={t("science.year")} name="year" type="number" min={1900} max={2100} defaultValue={report.reference_year ?? ""} />
        <TextField label={t("science.cultivated")} name="cultivated" type="number" min="0.000001" step="any" defaultValue={report.cultivated_area_hectares ?? ""} />
        <TextField label={t("science.harvested")} name="harvested" type="number" min="0.000001" step="any" defaultValue={report.harvested_area_hectares ?? ""} />
        <TextField label={t("science.quantity")} name="quantity" type="number" min={0} step="any" defaultValue={report.observed_quantity ?? report.reported_tons ?? ""} />
        <Select label={t("science.unit")} value={unit} onChange={setUnit} options={[{ value: "t", label: "t" }, { value: "kg", label: "kg" }]} />
        <TextField label={t("science.harvestDate")} name="harvestDate" type="date" defaultValue={report.harvest_date ?? ""} />
        <Select label={t("science.observation")} value={observation} onChange={setObservation} options={[
          { value: "farmer_estimate", label: t("science.estimate") }, { value: "measured", label: t("science.measured") },
          { value: "historical_reference", label: t("science.historical") },
        ]} />
        <TextField label={t("science.source")} name="source" defaultValue={report.data_source ?? ""} maxLength={255} />
      </> : <>
        <TextField label="Rainfall observation date" name="observationDate" type="date" defaultValue={report.observation_date ?? ""} />
        <TextField label="Gauge code (if assigned)" name="gauge" maxLength={80} defaultValue={report.gauge_code ?? ""} />
        <TextField label="Observation source" name="source" maxLength={255} defaultValue={report.data_source ?? ""} />
        <TextField label={t("kind.rain")} name="rainfall" type="number" min={0} max={300} step="any" defaultValue={report.rainfall_mm ?? ""} />
        <label className="block text-sm">{t("kind.asset")}
          <select name="condition" defaultValue={report.condition ?? ""} className="mt-1 block h-10 w-full rounded-control border border-line bg-surface px-3">
            <option value="">—</option><option value="operational">operational</option><option value="faulty">faulty</option><option value="offline">offline</option>
          </select>
        </label>
        <TextArea label={t("label.notes")} name="fault" defaultValue={report.notes ?? ""} maxLength={2000} />
      </>}
      <TextArea label={t("science.reason")} name="reason" required maxLength={1000} />
      <Button type="submit" variant="primary" loading={save.isPending}>{t("science.correct")}</Button>
    </form>
  );
}
