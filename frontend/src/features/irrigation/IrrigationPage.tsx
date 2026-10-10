import { AlertTriangle, CircleCheck, ClipboardList, RefreshCw, Wrench } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { isStaff, useSession } from "@/app/providers/SessionProvider";
import { DetailRow, OriginBadge, StatusBadge, VerificationBadge } from "@/components/data/badges";
import { DataTable, type Column } from "@/components/data/DataTable";
import { DataState } from "@/components/feedback/DataState";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Drawer } from "@/components/ui/Overlay";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";
import { formatDate, relativeTime } from "@/lib/format";
import { useApi, withParams } from "@/services/api/hooks";
import { assetHistorySchema, assetsSchema, type AssetRow } from "@/services/api/workspaces";

function Stat({ label, value, icon: Icon, tone }: { label: string; value: number | undefined; icon: typeof Wrench; tone: string }) {
  return (
    <Card className="flex items-center gap-4 p-5">
      <span aria-hidden className={cx("grid h-11 w-11 place-items-center rounded-xl", tone)}>
        <Icon className="h-5 w-5" />
      </span>
      <span>
        <span className="block font-heading text-2xl font-extrabold">{value ?? "—"}</span>
        <span className="text-sm text-muted">{label}</span>
      </span>
    </Card>
  );
}

function AssetDrawer({ asset, onClose }: { asset: AssetRow | null; onClose: () => void }) {
  const { t, lang } = useI18n();
  const { role } = useSession();
  const history = useApi(asset ? withParams("irrigation/assets/history", { asset: asset.asset, scheme_id: asset.scheme_id }) : null, assetHistorySchema);
  return (
    <Drawer open={asset !== null} onClose={onClose} title={asset?.asset ?? ""} subtitle={asset?.scheme ?? undefined} wide>
      {asset && (
        <dl className="mb-6">
          <DetailRow label={t("label.status")}><Badge tone={asset.down ? "critical" : "good"}>{asset.status}</Badge></DetailRow>
          <DetailRow label={t("irrigation.lastReport")}>{formatDate(asset.reported_at, lang)} · {relativeTime(asset.reported_at, lang)}</DetailRow>
          {asset.bottleneck && <DetailRow label={t("evaluation.bottlenecks")}>{asset.bottleneck}</DetailRow>}
          {asset.description && <DetailRow label={t("label.notes")}>{asset.description}</DetailRow>}
          <DetailRow label={t("irrigation.faults")}>{asset.fault_reports} / {asset.reports}</DetailRow>
          <DetailRow label={t("irrigation.openCases")}>
            {asset.open_cases.length === 0 ? "—" : (
              <span className="flex flex-wrap gap-2">
                {asset.open_cases.map((item) => (
                  <span key={item.id} className="inline-flex items-center gap-1.5">
                    {isStaff(role) ? <Link className="font-semibold text-primary hover:underline" to={`/actions?open=infrastructure-${item.id}`}>#{item.id}</Link> : `#${item.id}`}
                    <StatusBadge status={item.status} />
                  </span>
                ))}
              </span>
            )}
          </DetailRow>
        </dl>
      )}
      <h3 className="text-sm font-bold">{t("irrigation.history")}</h3>
      {history.isPending ? (
        <DataState kind="loading" compact />
      ) : history.error ? (
        <DataState kind="error" compact message={history.error.message} onRetry={() => void history.refetch()} />
      ) : (
        <ol className="mt-3 space-y-3 border-l-2 border-line pl-4">
          {history.data.history.map((entry) => (
            <li key={entry.id} className="text-sm">
              <p className="flex flex-wrap items-center gap-1.5">
                <span className="font-semibold">{entry.condition ?? "—"}</span>
                <span className="text-xs text-muted">{formatDate(entry.created_at, lang)}{entry.sector ? ` · ${entry.sector}` : ""}</span>
                <VerificationBadge status={entry.verification_status} />
                <OriginBadge origin={entry.data_origin} />
                {entry.case && <StatusBadge status={entry.case.status} />}
              </p>
              {(entry.bottleneck || entry.description) && <p className="mt-0.5 text-muted">{[entry.bottleneck, entry.description].filter(Boolean).join(" — ")}</p>}
            </li>
          ))}
        </ol>
      )}
    </Drawer>
  );
}

/** Pumps, canals and solar arrays: current condition, history and open cases. */
export function IrrigationPage() {
  const { t, lang } = useI18n();
  const data = useApi("irrigation/assets", assetsSchema);
  const [selected, setSelected] = useState<AssetRow | null>(null);

  const columns: Column<AssetRow>[] = [
    {
      key: "asset", header: t("kind.asset"), primary: true, sortValue: (row) => row.asset,
      render: (row) => (
        <span>
          <span className="block font-semibold">{row.asset}</span>
          <span className="text-xs text-muted">{row.scheme ?? "—"}</span>
        </span>
      ),
    },
    { key: "status", header: t("label.status"), sortValue: (row) => (row.down ? 0 : 1), render: (row) => <Badge tone={row.down ? "critical" : "good"}>{row.status}</Badge> },
    { key: "bottleneck", header: t("evaluation.bottlenecks"), render: (row) => row.bottleneck ?? "—" },
    { key: "sector", header: t("label.sector"), render: (row) => row.sector ?? "—", sortValue: (row) => row.sector },
    { key: "faults", header: t("irrigation.faults"), render: (row) => `${row.fault_reports} / ${row.reports}`, sortValue: (row) => row.fault_reports },
    { key: "cases", header: t("irrigation.openCases"), render: (row) => row.open_cases.length || "—", sortValue: (row) => row.open_cases.length },
    { key: "reported", header: t("irrigation.lastReport"), render: (row) => relativeTime(row.reported_at, lang), sortValue: (row) => row.reported_at },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("irrigation.eyebrow")}
        title={t("irrigation.title")}
        description={t("irrigation.description")}
        updatedAt={data.dataUpdatedAt}
        actions={<Button icon={RefreshCw} onClick={() => void data.refetch()} loading={data.isFetching}>{t("filter.refresh")}</Button>}
      />
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label={t("irrigation.assets")} value={data.data?.counts.assets} icon={Wrench} tone="bg-water-soft text-water" />
        <Stat label={t("irrigation.down")} value={data.data?.counts.down} icon={AlertTriangle} tone="bg-critical-soft text-critical" />
        <Stat label={t("irrigation.openCases")} value={data.data?.counts.open_cases} icon={ClipboardList} tone="bg-amber-soft text-amber" />
      </div>
      <DataTable
          rows={data.data?.assets}
          columns={columns}
          rowKey={(row) => `${row.scheme_id ?? 0}-${row.asset}`}
          caption={t("irrigation.title")}
          loading={data.isPending}
          error={data.error ? data.error.message : null}
          onRetry={() => void data.refetch()}
          emptyMessage={t("irrigation.empty")}
          searchText={(row) => `${row.asset} ${row.scheme ?? ""} ${row.sector ?? ""} ${row.bottleneck ?? ""}`}
          onRowClick={setSelected}
          initialSort={{ key: "status", direction: "asc" }}
        />
      {data.data && data.data.never_reported.length > 0 && (
        <Card>
          <CardHeader title={t("irrigation.never")} note={t("irrigation.neverNote")} />
          <ul className="grid gap-2 p-5 sm:grid-cols-2 lg:grid-cols-3">
            {data.data.never_reported.map((item) => (
              <li key={`${item.scheme}-${item.asset}`} className="flex items-center gap-2 rounded-control border border-line px-3 py-2 text-sm">
                <CircleCheck aria-hidden className="h-4 w-4 text-muted" />
                <span className="min-w-0">
                  <span className="block truncate font-semibold">{item.asset}</span>
                  <span className="text-xs text-muted">{[item.scheme, item.asset_type].filter(Boolean).join(" · ")}</span>
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
      <AssetDrawer asset={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
