import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageSquareShare, Save } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { z } from "zod";
import { DetailRow, PriorityBadge, StatusBadge } from "@/components/data/badges";
import { DataState } from "@/components/feedback/DataState";
import { Button } from "@/components/ui/Button";
import { SelectField, TextArea, TextField } from "@/components/ui/Field";
import { Dialog, Drawer } from "@/components/ui/Overlay";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n";
import type { MessageKey } from "@/i18n/en";
import { formatDate, parseTimestamp, relativeTime } from "@/lib/format";
import { ApiError, apiSend } from "@/services/api/client";
import { useApi, useReferenceData } from "@/services/api/hooks";
import {
  STATUSES, assigneeSchema, caseSchema, eventSchema, feedbackSchema, fieldUserSchema, notificationSchema, type CaseStatus,
} from "@/services/api/workspaces";

export type WorkItem = { kind: "case" | "grievance"; id: number; title: string; details?: string | null; cellId?: number | null };

const CLOSED = new Set<CaseStatus>(["resolved", "closed"]);

/** "2026-10-15" from a server timestamp, for a date input. */
function dateInput(value: string | null): string {
  return value ? parseTimestamp(value).toISOString().slice(0, 10) : "";
}

interface Draft {
  status: CaseStatus;
  assignee: string;
  due: string;
  action: string;
}

/**
 * Assign, set a deadline, record what was done and close the loop for one case or grievance.
 * Every save is a status event on the server, so the history below is the audit trail.
 */
export function WorkItemDrawer({ item, onClose }: { item: WorkItem | null; onClose: () => void }) {
  const { t, lang } = useI18n();
  const toast = useToast();
  const client = useQueryClient();
  const { place } = useReferenceData();
  const isCase = item?.kind === "case";

  const record = useApi(item && isCase ? `cases/${item.id}` : null, caseSchema);
  const grievances = useApi(item && !isCase ? "feedback" : null, z.array(feedbackSchema));
  const grievance = grievances.data?.find((row) => row.id === item?.id);
  const history = useApi(item ? `${isCase ? "cases" : "feedback"}/${item.id}/history` : null, z.array(eventSchema));
  const staff = useApi(item ? "admin/assignees" : null, z.array(assigneeSchema), { staleTime: 5 * 60_000 });
  const fieldUsers = useApi(item && !isCase ? "field-users" : null, z.array(fieldUserSchema), { staleTime: 5 * 60_000 });

  const current = isCase ? record.data : grievance;
  const loading = isCase ? record.isPending : grievances.isPending;
  const loadError = (isCase ? record.error : grievances.error) as Error | null;

  const [draft, setDraft] = useState<Draft | null>(null);
  const [errors, setErrors] = useState<Partial<Record<keyof Draft, string>>>({});
  const [preview, setPreview] = useState<z.infer<typeof notificationSchema> | null>(null);

  useEffect(() => {
    if (!current) return setDraft(null);
    const assignee = "assigned_to_account_id" in current ? current.assigned_to_account_id : current.assigned_to_field_user_id;
    setDraft({ status: current.status, assignee: assignee ? String(assignee) : "", due: dateInput(current.due_at), action: current.action_taken ?? "" });
    setErrors({});
  }, [current]);

  const staffName = new Map((staff.data ?? []).map((person) => [person.id, person.full_name]));
  const base = item ? `${isCase ? "cases" : "feedback"}/${item.id}` : "";

  const save = useMutation({
    mutationFn: (value: Draft) => {
      const assignee = value.assignee ? Number(value.assignee) : null;
      // A deadline is the end of the chosen day in Kigali (UTC+2).
      const due = value.due ? `${value.due}T23:59:00+02:00` : null;
      const body = isCase
        ? { status: value.status, assigned_to_account_id: assignee, due_at: due, action_taken: value.action.trim() || null }
        : { status: value.status, assigned_to_field_user_id: assignee, due_at: due, action_taken: value.action.trim() || null };
      return apiSend("PATCH", base, body);
    },
    onSuccess: () => {
      toast.success(t("actions.saved"));
      void client.invalidateQueries();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const notify = useMutation({
    mutationFn: (send: boolean) => apiSend("POST", `${base}/notify-cell`, { preview: !send }, notificationSchema),
    onSuccess: (result, send) => {
      if (!send) return setPreview(result);
      setPreview(null);
      toast.success(t("actions.notifySent", { n: result.recipients }));
      void client.invalidateQueries();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!draft) return;
    const problems: typeof errors = {};
    if (CLOSED.has(draft.status) && !draft.action.trim()) problems.action = t("actions.actionHint");
    if (isCase && draft.status === "assigned" && !draft.assignee) problems.assignee = t("actions.needsAssignee");
    setErrors(problems);
    if (Object.keys(problems).length === 0) save.mutate(draft);
  };

  const ownerOptions = isCase
    ? (staff.data ?? []).map((person) => ({ value: String(person.id), label: `${person.full_name} · ${person.area}` }))
    : (fieldUsers.data ?? []).filter((user) => user.is_active).map((user) => ({
        value: String(user.id),
        label: [user.full_name ?? t("actions.unnamed"), user.cooperative_name, place(user.cell_id)].filter(Boolean).join(" · "),
      }));
  const savedClosed = current ? CLOSED.has(current.status) : false;

  return (
    <Drawer
      open={item !== null}
      onClose={onClose}
      wide
      title={item?.title ?? ""}
      subtitle={item && (
        <span className="flex flex-wrap items-center gap-2">
          {t(isCase ? "actions.case" : "actions.grievance")} #{item.id}
          {current && <StatusBadge status={current.status} />}
          {record.data && <PriorityBadge priority={record.data.priority} />}
        </span>
      )}
      footer={draft && (
        <>
          <Button icon={MessageSquareShare} onClick={() => notify.mutate(false)} loading={notify.isPending && !notify.variables} disabled={!savedClosed} title={savedClosed ? undefined : t("actions.notifyNeedsResolution")}>
            {t("actions.notify")}
          </Button>
          <Button variant="primary" icon={Save} type="submit" form="work-item-form" loading={save.isPending}>
            {t("action.save")}
          </Button>
        </>
      )}
    >
      {loading ? (
        <DataState kind="loading" />
      ) : loadError || !current || !draft ? (
        <DataState kind="error" message={loadError instanceof ApiError ? loadError.message : t("state.error")} onRetry={() => void (isCase ? record.refetch() : grievances.refetch())} />
      ) : (
        <div className="space-y-6">
          <dl>
            <DetailRow label={t("actions.reportDetails")}>{item?.details || ("message" in current ? current.message : "—")}</DetailRow>
            <DetailRow label={t("reports.location")}>{place(item?.cellId ?? ("cell_id" in current ? current.cell_id : null)) ?? "—"}</DetailRow>
            <DetailRow label={t("label.date")}>{formatDate(current.created_at, lang)} · {relativeTime(current.created_at, lang)}</DetailRow>
          </dl>

          <form id="work-item-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2" noValidate>
            <SelectField
              label={t("label.status")}
              value={draft.status}
              onChange={(event) => setDraft({ ...draft, status: event.target.value as CaseStatus })}
              options={STATUSES.map((value) => ({ value, label: t(`status.${value}` as MessageKey) }))}
            />
            <SelectField
              label={t("actions.assignee")}
              value={draft.assignee}
              error={errors.assignee}
              hint={ownerOptions.length ? undefined : t(isCase ? "actions.noStaff" : "actions.noFieldUsers")}
              onChange={(event) => setDraft({ ...draft, assignee: event.target.value })}
              options={[{ value: "", label: t("actions.unassigned") }, ...ownerOptions]}
            />
            <TextField label={t("actions.due")} type="date" value={draft.due} onChange={(event) => setDraft({ ...draft, due: event.target.value })} />
            <div className="sm:col-span-2">
              <TextArea
                label={t("actions.actionTaken")}
                value={draft.action}
                maxLength={3000}
                hint={t("actions.actionHint")}
                error={errors.action}
                required={CLOSED.has(draft.status)}
                onChange={(event) => setDraft({ ...draft, action: event.target.value })}
              />
            </div>
          </form>
          {!savedClosed && <p className="text-xs text-muted">{t("actions.notifyHint")} {t("actions.notifyNeedsResolution")}</p>}

          <section aria-labelledby="work-history">
            <h3 id="work-history" className="text-sm font-bold">{t("label.history")}</h3>
            {history.isPending ? (
              <DataState kind="loading" compact />
            ) : !history.data?.length ? (
              <p className="mt-2 text-sm text-muted">{t("actions.noHistory")}</p>
            ) : (
              <ol className="mt-2 space-y-3 border-l-2 border-line pl-4">
                {history.data.map((event) => (
                  <li key={event.id} className="text-sm">
                    <p className="flex flex-wrap items-center gap-1.5">
                      {event.previous_status && <><StatusBadge status={event.previous_status} />→</>}
                      <StatusBadge status={event.new_status} />
                      <span className="text-xs text-muted">
                        {formatDate(event.created_at, lang)} · {event.changed_by_account_id ? staffName.get(event.changed_by_account_id) ?? `#${event.changed_by_account_id}` : t("actions.system")}
                      </span>
                    </p>
                    {event.action_taken && <p className="mt-1 text-ink">{event.action_taken}</p>}
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      )}

      <Dialog
        open={preview !== null}
        onClose={() => setPreview(null)}
        title={t("actions.notify")}
        actions={
          <>
            <Button onClick={() => setPreview(null)}>{t("action.cancel")}</Button>
            <Button variant="primary" onClick={() => notify.mutate(true)} loading={notify.isPending} disabled={!preview?.recipients}>
              {t("action.send")}
            </Button>
          </>
        }
      >
        <p>{t("actions.notifyPreview", { n: preview?.recipients ?? 0 })}</p>
        <blockquote className="mt-2 rounded-control bg-canvas p-3 text-sm">{preview?.message}</blockquote>
      </Dialog>
    </Drawer>
  );
}
