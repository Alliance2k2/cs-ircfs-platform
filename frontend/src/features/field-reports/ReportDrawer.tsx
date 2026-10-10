import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, RotateCcw, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { DetailRow, FlagBadges, OriginBadge, StatusBadge, VerificationBadge } from "@/components/data/badges";
import { DataState } from "@/components/feedback/DataState";
import { Button } from "@/components/ui/Button";
import { TextArea } from "@/components/ui/Field";
import { Drawer } from "@/components/ui/Overlay";
import { useToast } from "@/components/ui/Toast";
import { isStaff, useSession } from "@/app/providers/SessionProvider";
import { useI18n } from "@/i18n";
import type { MessageKey } from "@/i18n/en";
import { formatDate, formatNumber, relativeTime } from "@/lib/format";
import { apiSend } from "@/services/api/client";
import { useApi } from "@/services/api/hooks";
import { fieldReportDetailSchema, type FieldReport } from "@/services/api/workspaces";

type Verdict = "verified" | "rejected" | "unverified";

/** The value a report carries, in words: "4.5 t expected", "32 mm", "severity 4". */
export function reportValue(report: Pick<FieldReport, "kind" | "expected_tons" | "reported_tons" | "rainfall_mm" | "severity" | "condition">, lang: "en" | "rw"): string {
  const n = (value: number | null, unit: string) => (value === null ? null : `${formatNumber(value, lang)} ${unit}`);
  switch (report.kind) {
    case "rain":
      return n(report.rainfall_mm, "mm") ?? "—";
    case "pest":
      return report.severity === null ? "—" : `${report.severity}/5`;
    case "asset":
      return report.condition ?? "—";
    default:
      return [n(report.reported_tons, "t"), report.expected_tons !== null ? `(${n(report.expected_tons, "t")} exp.)` : null].filter(Boolean).join(" ") || "—";
  }
}

export function ReportDrawer({ report, onClose }: { report: Pick<FieldReport, "source" | "id" | "title"> | null; onClose: () => void }) {
  const { t, lang } = useI18n();
  const { role } = useSession();
  const toast = useToast();
  const client = useQueryClient();
  const detail = useApi(report ? `field-reports/${report.source}/${report.id}` : null, fieldReportDetailSchema);
  const [note, setNote] = useState("");
  const [noteError, setNoteError] = useState<string | undefined>();
  const data = detail.data;

  useEffect(() => {
    setNote(data?.verification_note ?? "");
    setNoteError(undefined);
  }, [data?.id, data?.verification_note]);

  const verify = useMutation({
    mutationFn: (status: Verdict) => apiSend("PATCH", `field-reports/${report!.source}/${report!.id}/verification`, { status, note: note.trim() || null }),
    onSuccess: (_, status) => {
      toast.success(t("reports.verified", { status: t(`verification.${status}`).toLowerCase() }));
      void client.invalidateQueries({ queryKey: ["api"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const decide = (status: Verdict) => {
    if (status === "rejected" && !note.trim()) return setNoteError(t("reports.noteHint"));
    setNoteError(undefined);
    verify.mutate(status);
  };

  const staff = isStaff(role);
  return (
    <Drawer
      open={report !== null}
      onClose={onClose}
      title={report?.title ?? ""}
      subtitle={data && (
        <span className="flex flex-wrap items-center gap-2">
          {t(`kind.${data.kind}` as MessageKey)} · {formatDate(data.created_at, lang)} ({relativeTime(data.created_at, lang)})
          <VerificationBadge status={data.verification_status} />
          <OriginBadge origin={data.data_origin} />
        </span>
      )}
      footer={staff && data && (
        <>
          {data.verification_status !== "unverified" && (
            <Button icon={RotateCcw} onClick={() => decide("unverified")} loading={verify.isPending && verify.variables === "unverified"}>{t("reports.unverify")}</Button>
          )}
          <Button variant="danger" icon={XCircle} onClick={() => decide("rejected")} loading={verify.isPending && verify.variables === "rejected"} disabled={data.verification_status === "rejected"}>
            {t("reports.reject")}
          </Button>
          <Button variant="primary" icon={CheckCircle2} onClick={() => decide("verified")} loading={verify.isPending && verify.variables === "verified"} disabled={data.verification_status === "verified"}>
            {t("reports.verify")}
          </Button>
        </>
      )}
    >
      {detail.isPending ? (
        <DataState kind="loading" />
      ) : detail.error || !data ? (
        <DataState kind="error" message={detail.error?.message} onRetry={() => void detail.refetch()} />
      ) : (
        <div className="space-y-6">
          <dl>
            <DetailRow label={t("reports.value")}>{reportValue(data, lang)}</DetailRow>
            {data.crop && <DetailRow label={t("crops.crop")}>{data.crop}</DetailRow>}
            {data.pest && <DetailRow label={t("kind.pest")}>{data.pest}</DetailRow>}
            {data.asset && <DetailRow label={t("kind.asset")}>{data.asset}{data.bottleneck ? ` · ${data.bottleneck}` : ""}</DetailRow>}
            <DetailRow label={t("label.scheme")}>{data.scheme ?? "—"}</DetailRow>
            <DetailRow label={t("reports.location")}>
              {[data.sector, data.cell].filter(Boolean).join(" · ") || "—"}
              {data.latitude !== null && data.longitude !== null && (
                <span className="block text-xs text-muted">{data.latitude.toFixed(5)}, {data.longitude.toFixed(5)} ({t("reports.gps")})</span>
              )}
            </DetailRow>
            <DetailRow label={t("reports.reporter")}>{data.reporter ?? "—"}{data.reporter_role ? ` · ${data.reporter_role.replaceAll("_", " ")}` : ""}</DetailRow>
            {data.notes && <DetailRow label={t("label.notes")}>{data.notes}</DetailRow>}
            <DetailRow label={t("label.flags")}><FlagBadges flags={data.flags} /></DetailRow>
            <DetailRow label={t("reports.case")}>
              {data.case ? (
                <span className="flex flex-wrap items-center gap-2">
                  #{data.case.id} <StatusBadge status={data.case.status} />
                  {staff && <Link className="font-semibold text-primary hover:underline" to={`/actions?open=${data.source === "infrastructure" ? "infrastructure" : "pest_or_disease"}-${data.case.id}`}>{t("action.open")}</Link>}
                </span>
              ) : "—"}
            </DetailRow>
          </dl>

          {staff && (
            <section aria-labelledby="verify-title" className="space-y-3">
              <h3 id="verify-title" className="text-sm font-bold">{t("label.verification")}</h3>
              <TextArea label={t("reports.note")} hint={t("reports.noteHint")} error={noteError} value={note} maxLength={1000} onChange={(event) => setNote(event.target.value)} />
              {data.verification_history.length > 0 && (
                <ol className="space-y-2 border-l-2 border-line pl-4 text-sm">
                  {data.verification_history.map((event, index) => (
                    <li key={index}>
                      <span className="font-semibold">{t(`verification.${event.action.replace("report.", "")}` as MessageKey)}</span>
                      <span className="text-xs text-muted"> · {event.by} · {formatDate(event.at, lang)}</span>
                      {event.detail && <p className="text-muted">{event.detail}</p>}
                    </li>
                  ))}
                </ol>
              )}
            </section>
          )}
        </div>
      )}
    </Drawer>
  );
}
