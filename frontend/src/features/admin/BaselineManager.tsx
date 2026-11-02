import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { z } from "zod";
import { DataState } from "@/components/feedback/DataState";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n";
import { apiSend } from "@/services/api/client";
import { useApi } from "@/services/api/hooks";
import { baselineSchema } from "@/services/api/workspaces";

export function BaselineManager({ schemes }: { schemes: { id: number; name: string }[] }) {
  const { t } = useI18n();
  const toast = useToast();
  const client = useQueryClient();
  const versions = useApi("scheme-baselines", z.array(baselineSchema));
  const [scheme, setScheme] = useState("");
  const [unit, setUnit] = useState("t/ha");
  const [approvalDate, setApprovalDate] = useState("");
  const save = useMutation({
    mutationFn: ({ path, body }: { path: string; body: unknown }) => apiSend("POST", path, body),
    onSuccess: () => {
      toast.success(t("science.saved"));
      void client.invalidateQueries({ queryKey: ["api"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const text = (name: string) => String(values.get(name) ?? "").trim();
    save.mutate({ path: "scheme-baselines", body: {
      scheme_id: Number(scheme), crop_type: text("crop"), season: text("season"), reference_year: Number(text("year")),
      expected_yield: Number(text("yield")), yield_unit: unit, official_source: text("source"), document_reference: text("document"),
      supersedes_id: text("replaces") ? Number(text("replaces")) : null,
    } });
  };
  return (
    <section className="space-y-4 rounded-card border border-line p-5" aria-labelledby="official-targets">
      <h2 id="official-targets" className="text-lg font-bold">{t("science.baselines")}</h2>
      <p className="text-sm text-muted">{t("science.baselineHint")}</p>
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
        <Select label={t("science.scheme")} value={scheme} onChange={setScheme} options={[
          { value: "", label: t("science.scheme") }, ...schemes.map((s) => ({ value: String(s.id), label: s.name })),
        ]} />
        <TextField label={t("science.crop")} name="crop" required maxLength={80} />
        <TextField label={t("science.season")} name="season" required maxLength={20} />
        <TextField label={t("science.year")} name="year" required type="number" min={1900} max={2100} />
        <TextField label={t("science.target")} name="yield" required type="number" min="0.000001" step="any" />
        <Select label={t("science.unit")} value={unit} onChange={setUnit} options={[{ value: "t/ha", label: "t/ha" }, { value: "kg/ha", label: "kg/ha" }]} />
        <TextField label={t("science.officialSource")} name="source" required maxLength={255} />
        <TextField label={t("science.document")} name="document" required maxLength={255} />
        <TextField label={t("science.replaces")} name="replaces" type="number" min={1} />
        <Button type="submit" variant="primary" disabled={!scheme} loading={save.isPending}>{t("science.create")}</Button>
      </form>
      <TextField label={t("science.approvalDate")} type="date" value={approvalDate} onChange={(e) => setApprovalDate(e.target.value)} />
      {versions.isPending ? <DataState kind="loading" /> : versions.error ? (
        <DataState kind="error" message={versions.error.message} onRetry={() => void versions.refetch()} />
      ) : !versions.data?.length ? <p className="text-sm text-muted">{t("science.none")}</p> : (
        <ul className="space-y-3">
          {versions.data.map((b) => (
            <li key={b.id} className="rounded-control border border-line p-3 text-sm">
              <p className="font-semibold">#{b.id} · {schemes.find((s) => s.id === b.scheme_id)?.name} · {b.crop_type} · {b.season} / {b.reference_year}</p>
              <p>{b.expected_yield} {b.yield_unit} · {b.verification_status} · {b.data_origin}{b.supersedes_id ? ` · replaces #${b.supersedes_id}` : ""}</p>
              <p className="break-words text-xs text-muted">{b.official_source} · {b.document_reference}{b.approved_at ? ` · ${b.approved_at}` : ""}</p>
              {b.verification_status === "unverified" && b.data_origin !== "demo" && (
                <Button size="sm" disabled={!approvalDate} loading={save.isPending}
                  onClick={() => save.mutate({ path: `scheme-baselines/${b.id}/approve`, body: { approved_at: approvalDate } })}>{t("science.approve")}</Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
