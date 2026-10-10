import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, History, Landmark, PauseCircle, PlayCircle, Save, Users } from "lucide-react";
import { useState, type FormEvent } from "react";
import { z } from "zod";
import { useSession } from "@/app/providers/SessionProvider";
import { DataTable, type Column } from "@/components/data/DataTable";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Field";
import { Dialog, Drawer } from "@/components/ui/Overlay";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";
import { formatDate, formatTime, parseTimestamp } from "@/lib/format";
import { apiSend } from "@/services/api/client";
import { useApi, useReferenceData } from "@/services/api/hooks";
import { roleSchema, type Role } from "@/services/api/schemas";
import { accountRowSchema, auditSchema, schemeFullSchema, type AccountRow, type AuditRow } from "@/services/api/workspaces";

type Scheme = z.infer<typeof schemeFullSchema>;
type Change = { account: AccountRow; patch: { role?: Role; status?: string }; message: string };
const roleName = (role: string) => role.replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase());

function useSave() {
  const toast = useToast();
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ path, body }: { path: string; body: unknown; done: string }) => apiSend("PATCH", path, body),
    onSuccess: (_, { done }) => {
      toast.success(done);
      void client.invalidateQueries({ queryKey: ["api"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

function AreaForm({ account, onClose }: { account: AccountRow; onClose: () => void }) {
  const { t } = useI18n();
  const { sectors } = useReferenceData();
  const save = useSave();
  const [chosen, setChosen] = useState(new Set(account.sector_ids));
  const toggle = (id: number) => setChosen((current) => {
    const next = new Set(current);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  });
  return (
    <Drawer open onClose={onClose} title={account.full_name} subtitle={t("admin.areaTitle")}
      footer={<Button variant="primary" icon={Save} loading={save.isPending}
        onClick={() => save.mutate({ path: `auth/accounts/${account.id}`, body: { sector_ids: [...chosen] }, done: t("admin.areaSaved") }, { onSuccess: onClose })}>{t("action.save")}</Button>}>
      <p className="text-sm text-muted">{t("admin.areaHint")}</p>
      <fieldset className="mt-4">
        <legend className="sr-only">{t("admin.areaTitle")}</legend>
        <ul className="grid gap-1 sm:grid-cols-2">
          {sectors.map((sector) => (
            <li key={sector.id}>
              <label className="flex items-center gap-2 rounded-control px-2 py-1.5 text-sm hover:bg-canvas">
                <input type="checkbox" checked={chosen.has(sector.id)} onChange={() => toggle(sector.id)} className="h-4 w-4" />
                {sector.name}
              </label>
            </li>
          ))}
        </ul>
      </fieldset>
      <p className="mt-3 text-sm font-semibold">{chosen.size ? t("admin.areaCount", { n: chosen.size }) : t("admin.wholeDistrict")}</p>
    </Drawer>
  );
}

function Accounts() {
  const { t, lang } = useI18n();
  const { account: me } = useSession();
  const { sectorName } = useReferenceData();
  const accounts = useApi("auth/accounts", z.array(accountRowSchema));
  const save = useSave();
  const [status, setStatus] = useState("");
  const [change, setChange] = useState<Change | null>(null);
  const [area, setArea] = useState<AccountRow | null>(null);
  const rows = (accounts.data ?? []).filter((row) => !status || row.status === status);
  const pending = (accounts.data ?? []).filter((row) => row.status === "pending").length;

  const ask = (account: AccountRow, patch: Change["patch"], message: string) => setChange({ account, patch, message });
  const confirm = () => {
    if (!change) return;
    const done = change.patch.role ? t("admin.roleChanged") : t("admin.statusChanged", { status: t(`admin.status.${change.patch.status as "active" | "suspended"}`).toLowerCase() });
    save.mutate({ path: `auth/accounts/${change.account.id}`, body: change.patch, done }, { onSettled: () => setChange(null) });
  };

  const columns: Column<AccountRow>[] = [
    {
      key: "name", header: t("admin.name"), primary: true, sortValue: (row) => row.full_name,
      render: (row) => (
        <span>
          <span className="block font-semibold">{row.full_name}{row.id === me?.id && <span className="ml-1 text-xs text-muted">({t("admin.you")})</span>}</span>
          <span className="text-xs text-muted">{row.email}</span>
        </span>
      ),
    },
    {
      key: "role", header: t("shell.role"), sortValue: (row) => row.role,
      render: (row) => (
        <select
          aria-label={t("admin.roleFor", { name: row.full_name })}
          value={row.role}
          disabled={row.id === me?.id || save.isPending}
          onClick={(event) => event.stopPropagation()}
          onChange={(event) => ask(row, { role: event.target.value as Role }, t("admin.confirmRole", { name: row.full_name, role: roleName(event.target.value) }))}
          className="h-9 rounded-control border border-line bg-surface px-2 text-sm"
        >
          {roleSchema.options.map((role) => <option key={role} value={role}>{roleName(role)}</option>)}
        </select>
      ),
    },
    { key: "area", header: t("shell.area"), render: (row) => (row.sector_ids.length ? row.sector_ids.map((id) => sectorName.get(id) ?? `#${id}`).join(", ") : t("admin.wholeDistrict")) },
    {
      key: "status", header: t("label.status"), sortValue: (row) => row.status,
      render: (row) => <Badge tone={row.status === "active" ? "good" : row.status === "pending" ? "warning" : "critical"}>{t(`admin.status.${row.status as "active"}`)}</Badge>,
    },
    { key: "created", header: t("admin.created"), render: (row) => formatDate(row.created_at, lang), sortValue: (row) => row.created_at },
    {
      key: "actions", header: "",
      render: (row) => <span onClick={(event) => event.stopPropagation()}>{
        row.id === me?.id ? null : row.status === "pending" ? (
          <Button size="sm" variant="primary" icon={CheckCircle2} onClick={() => ask(row, { status: "active" }, t("admin.confirmApprove", { name: row.full_name, role: roleName(row.role) }))}>{t("admin.approve")}</Button>
        ) : row.status === "active" ? (
          <Button size="sm" icon={PauseCircle} onClick={() => ask(row, { status: "suspended" }, t("admin.confirmSuspend", { name: row.full_name }))}>{t("admin.suspend")}</Button>
        ) : (
          <Button size="sm" icon={PlayCircle} onClick={() => ask(row, { status: "active" }, t("admin.confirmReactivate", { name: row.full_name }))}>{t("admin.reactivate")}</Button>
        )}</span>,
    },
  ];

  return (
    <>
      {pending > 0 && <p role="status" className="rounded-control bg-amber-soft px-4 py-2 text-sm font-semibold text-amber">{t("admin.pendingCount", { n: pending })}</p>}
      <DataTable
          rows={rows}
          columns={columns}
          rowKey={(row) => row.id}
          caption={t("admin.accounts")}
          loading={accounts.isPending}
          error={accounts.error ? accounts.error.message : null}
          onRetry={() => void accounts.refetch()}
          emptyMessage={t("admin.noAccounts")}
          searchText={(row) => `${row.full_name} ${row.email} ${row.role}`}
          initialSort={{ key: "status", direction: "desc" }}
          onRowClick={(row) => row.id !== me?.id && setArea(row)}
          toolbar={
            <Select label={t("label.status")} value={status} onChange={setStatus} options={[
              { value: "", label: t("label.all") },
              ...(["pending", "active", "suspended"] as const).map((value) => ({ value, label: t(`admin.status.${value}`) })),
            ]} />
          }
        />
      <p className="text-xs text-muted">{t("admin.rowHint")}</p>
      {area && <AreaForm key={area.id} account={area} onClose={() => setArea(null)} />}
      <Dialog
        open={change !== null}
        onClose={() => setChange(null)}
        title={t("action.confirm")}
        actions={
          <>
            <Button onClick={() => setChange(null)}>{t("action.cancel")}</Button>
            <Button variant={change?.patch.status === "suspended" ? "danger" : "primary"} onClick={confirm} loading={save.isPending}>{t("action.confirm")}</Button>
          </>
        }
      >
        {change?.message}
      </Dialog>
    </>
  );
}

function SchemeForm({ scheme, onClose }: { scheme: Scheme; onClose: () => void }) {
  const { t } = useI18n();
  const save = useSave();
  const [target, setTarget] = useState(scheme.baseline_yield_target_tons?.toString() ?? "");
  const [source, setSource] = useState(scheme.baseline_source ?? "");
  const [partner, setPartner] = useState(scheme.implementing_partner ?? "");
  const [hectares, setHectares] = useState(scheme.hectares_developed?.toString() ?? "");
  const [errors, setErrors] = useState<{ target?: string; source?: string; hectares?: string }>({});

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const problems: typeof errors = {};
    const number = (value: string) => (value.trim() === "" ? null : Number(value));
    if (target.trim() && !(Number(target) >= 0)) problems.target = t("admin.notNumber");
    if (hectares.trim() && !(Number(hectares) >= 0)) problems.hectares = t("admin.notNumber");
    if (target.trim() && !source.trim()) problems.source = t("admin.schemeSourceHint");
    setErrors(problems);
    if (Object.keys(problems).length) return;
    save.mutate(
      {
        path: `irrigation-schemes/${scheme.id}`,
        body: { baseline_yield_target_tons: number(target), baseline_source: source.trim() || null, implementing_partner: partner.trim() || null, hectares_developed: number(hectares) },
        done: t("admin.schemeSaved"),
      },
      { onSuccess: onClose },
    );
  };

  return (
    <Drawer open onClose={onClose} title={scheme.name} subtitle={t("admin.schemeNote")}
      footer={<Button variant="primary" icon={Save} type="submit" form="scheme-form" loading={save.isPending}>{t("action.save")}</Button>}>
      <form id="scheme-form" onSubmit={submit} className="space-y-4" noValidate>
        <TextField label={t("admin.schemeTarget")} inputMode="decimal" value={target} error={errors.target} onChange={(event) => setTarget(event.target.value)} />
        <TextField label={t("admin.schemeSource")} hint={t("admin.schemeSourceHint")} error={errors.source} maxLength={255} value={source} onChange={(event) => setSource(event.target.value)} />
        <TextField label={t("evaluation.partner")} maxLength={100} value={partner} onChange={(event) => setPartner(event.target.value)} />
        <TextField label={t("evaluation.hectares")} inputMode="decimal" value={hectares} error={errors.hectares} onChange={(event) => setHectares(event.target.value)} />
      </form>
    </Drawer>
  );
}

function Schemes() {
  const { t } = useI18n();
  const schemes = useApi("irrigation-schemes", z.array(schemeFullSchema));
  const [editing, setEditing] = useState<Scheme | null>(null);
  const columns: Column<Scheme>[] = [
    { key: "name", header: t("admin.name"), primary: true, render: (row) => <span className="font-semibold">{row.name}</span>, sortValue: (row) => row.name },
    { key: "partner", header: t("evaluation.partner"), render: (row) => row.implementing_partner ?? "—" },
    { key: "hectares", header: t("evaluation.hectares"), render: (row) => row.hectares_developed ?? "—" },
    { key: "target", header: t("evaluation.target"), render: (row) => (row.baseline_yield_target_tons === null ? <Badge>{t("evaluation.stateMissing")}</Badge> : `${row.baseline_yield_target_tons} t`) },
    {
      key: "source", header: t("evaluation.source"), className: "max-w-sm",
      render: (row) => (row.baseline_source ? (
        <span className={cx("text-xs", /DEMONSTRATION/i.test(row.baseline_source) && "font-semibold text-amber")}>{row.baseline_source}</span>
      ) : "—"),
    },
    { key: "active", header: t("label.status"), render: (row) => <Badge tone={row.is_active ? "good" : "neutral"}>{row.is_active ? t("admin.status.active") : t("admin.inactive")}</Badge> },
  ];
  return (
    <>
      <DataTable rows={schemes.data} columns={columns} rowKey={(row) => row.id} caption={t("admin.schemes")} loading={schemes.isPending}
          error={schemes.error ? schemes.error.message : null} onRetry={() => void schemes.refetch()} emptyMessage={t("evaluation.noSchemes")} onRowClick={setEditing} />
      <p className="text-xs text-muted">{t("admin.schemeNote")}</p>
      {editing && <SchemeForm key={editing.id} scheme={editing} onClose={() => setEditing(null)} />}
    </>
  );
}

function Audit() {
  const { t, lang } = useI18n();
  const audit = useApi("admin/audit?limit=500", z.array(auditSchema));
  const columns: Column<AuditRow>[] = [
    { key: "when", header: t("label.date"), render: (row) => `${formatDate(row.created_at, lang)} ${formatTime(parseTimestamp(row.created_at), lang)}`, sortValue: (row) => row.created_at },
    { key: "actor", header: t("admin.actor"), primary: true, render: (row) => <span className="font-semibold">{row.actor}</span>, sortValue: (row) => row.actor },
    { key: "action", header: t("admin.actionCol"), render: (row) => <span className="font-mono text-xs">{row.action}</span>, sortValue: (row) => row.action },
    { key: "entity", header: t("admin.entity"), render: (row) => `${row.entity.replaceAll("_", " ")}${row.entity_id ? ` #${row.entity_id}` : ""}` },
    {
      key: "detail", header: t("admin.detail"), className: "max-w-md",
      render: (row) => {
        const entries = Object.entries(row.detail);
        return entries.length ? <span className="break-words text-xs text-muted">{entries.map(([key, value]) => `${key}: ${typeof value === "object" ? JSON.stringify(value) : String(value)}`).join(" · ")}</span> : "—";
      },
    },
  ];
  return (
    <DataTable rows={audit.data} columns={columns} rowKey={(row) => row.id} caption={t("admin.audit")} loading={audit.isPending}
        error={audit.error ? audit.error.message : null} onRetry={() => void audit.refetch()} emptyMessage={t("admin.auditEmpty")}
        searchText={(row) => `${row.actor} ${row.action} ${row.entity} ${JSON.stringify(row.detail)}`} initialSort={{ key: "when", direction: "desc" }} pageSize={25} />
  );
}

const TABS = [
  { id: "accounts", icon: Users, label: "admin.accounts" },
  { id: "schemes", icon: Landmark, label: "admin.schemes" },
  { id: "audit", icon: History, label: "admin.audit" },
] as const;

/** Accounts and roles, scheme baselines and the audit trail. Administrators only. */
export function AdminPage() {
  const { t } = useI18n();
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("accounts");
  return (
    <div className="space-y-6">
      <PageHeader eyebrow={t("admin.eyebrow")} title={t("admin.title")} description={t("admin.description")} />
      <div role="tablist" aria-label={t("admin.title")} className="flex flex-wrap gap-2">
        {TABS.map((item) => (
          <button key={item.id} type="button" role="tab" aria-selected={tab === item.id} onClick={() => setTab(item.id)}
            className={cx("inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold", tab === item.id ? "border-forest bg-forest text-white" : "border-line bg-surface text-forest hover:bg-canvas")}>
            <item.icon aria-hidden className="h-4 w-4" />
            {t(item.label)}
          </button>
        ))}
      </div>
      <div role="tabpanel" className="space-y-4">
        {tab === "accounts" && <Accounts />}
        {tab === "schemes" && <Schemes />}
        {tab === "audit" && <Audit />}
      </div>
    </div>
  );
}
