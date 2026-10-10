import { ArrowDownLeft, ArrowUpRight, Coins, EyeOff, RefreshCw, Smartphone } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { DataTable, type Column } from "@/components/data/DataTable";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";
import { formatDate, formatTime, parseTimestamp } from "@/lib/format";
import { useApi } from "@/services/api/hooks";
import { activitySchema } from "@/services/api/workspaces";
import type { z } from "zod";

type Activity = z.infer<typeof activitySchema>;
type Tab = "inbound" | "outbound" | "rewards";

/** Inbound USSD and SMS, outbound SMS and airtime rewards: what actually went through the phone channels. */
export function ChannelsPage() {
  const { t, lang } = useI18n();
  const activity = useApi("channels/activity?limit=200", activitySchema, { refetchInterval: 30_000 });
  const [tab, setTab] = useState<Tab>("inbound");
  const data = activity.data;
  const when = (value: string) => `${formatDate(value, lang)} ${formatTime(parseTimestamp(value), lang)}`;
  const hidden = <span className="inline-flex items-center gap-1 text-xs text-muted"><EyeOff aria-hidden className="h-3.5 w-3.5" />{t("channels.hidden")}</span>;

  const inbound: Column<Activity["inbound"][number]>[] = [
    { key: "when", header: t("label.date"), render: (row) => when(row.created_at), sortValue: (row) => row.created_at },
    {
      key: "channel", header: t("channels.channel"), primary: true,
      render: (row) => (
        <span className="flex flex-wrap gap-1">
          <Badge tone={row.channel === "ussd" ? "brand" : "water"}>{row.channel.toUpperCase()}</Badge>
          {row.data_origin === "simulator" && <Badge tone="warning">{t("channels.simulator")}</Badge>}
        </span>
      ),
    },
    { key: "phone", header: t("channels.phone"), render: (row) => <span className="font-mono text-xs">{row.phone_number ?? "—"}</span> },
    { key: "text", header: t("channels.text"), className: "max-w-xs", render: (row) => (row.text === null && !data?.personal_data ? hidden : <span className="break-words font-mono text-xs">{row.text ?? "—"}</span>) },
    { key: "reply", header: t("channels.reply"), className: "max-w-sm", render: (row) => (row.reply === null && !data?.personal_data ? hidden : <span className="line-clamp-3 text-xs">{row.reply ?? "—"}</span>) },
    { key: "record", header: t("channels.record"), render: (row) => (row.record_type ? row.record_type.replaceAll("_", " ") : "—") },
  ];
  const outbound: Column<Activity["outbound"][number]>[] = [
    { key: "when", header: t("label.date"), render: (row) => when(row.created_at), sortValue: (row) => row.created_at },
    { key: "phone", header: t("channels.phone"), primary: true, render: (row) => <span className="font-mono text-xs">{row.phone_number ?? "—"}</span> },
    { key: "purpose", header: t("channels.purpose"), render: (row) => (row.purpose ?? "advisory").replaceAll("_", " ") },
    { key: "status", header: t("label.status"), render: (row) => <Badge tone={row.status === "sent" || row.status === "delivered" ? "good" : row.status === "failed" ? "critical" : "neutral"}>{row.status}</Badge>, sortValue: (row) => row.status },
    { key: "message", header: t("channels.text"), className: "max-w-md", render: (row) => (row.message === null && !data?.personal_data ? hidden : <span className="line-clamp-3 text-xs">{row.message ?? "—"}</span>) },
  ];
  const rewards: Column<Activity["rewards"][number]>[] = [
    { key: "when", header: t("label.date"), render: (row) => when(row.created_at), sortValue: (row) => row.created_at },
    { key: "phone", header: t("channels.phone"), primary: true, render: (row) => <span className="font-mono text-xs">{row.phone_number ?? "—"}</span> },
    { key: "amount", header: t("channels.amount"), render: (row) => `${row.amount_rwf} RWF`, sortValue: (row) => row.amount_rwf },
    { key: "reason", header: t("channels.reason"), render: (row) => row.reason },
    { key: "status", header: t("label.status"), render: (row) => <Badge tone={row.status === "paid" ? "good" : row.status === "failed" ? "critical" : "neutral"}>{row.status}</Badge> },
  ];

  const tabs: { id: Tab; label: string; icon: typeof Coins; count: number | undefined }[] = [
    { id: "inbound", label: t("channels.inbound"), icon: ArrowDownLeft, count: data?.inbound.length },
    { id: "outbound", label: t("channels.outbound"), icon: ArrowUpRight, count: data?.outbound.length },
    { id: "rewards", label: t("channels.rewards"), icon: Coins, count: data?.rewards.length },
  ];
  const common = {
    loading: activity.isPending,
    error: activity.error ? activity.error.message : null,
    onRetry: () => void activity.refetch(),
    emptyMessage: t("channels.empty"),
    initialSort: { key: "when", direction: "desc" as const },
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("channels.eyebrow")}
        title={t("channels.title")}
        description={t("channels.description")}
        updatedAt={activity.dataUpdatedAt}
        actions={
          <>
            <Button icon={RefreshCw} onClick={() => void activity.refetch()} loading={activity.isFetching}>{t("filter.refresh")}</Button>
            <Link to="/simulator" className="inline-flex h-10 items-center gap-2 rounded-control bg-primary px-4 text-sm font-semibold text-white hover:bg-primary-strong">
              <Smartphone aria-hidden className="h-4 w-4" />
              {t("nav.simulator")}
            </Link>
          </>
        }
      />
      {data && (
        <p className="text-sm text-muted">
          {t("channels.codes", { ussd: data.service_code, sms: data.sms_shortcode })}
          {!data.personal_data && <span className="ml-1 font-semibold text-ink">{t("channels.masked")}</span>}
        </p>
      )}
      <div role="tablist" aria-label={t("channels.title")} className="flex flex-wrap gap-2">
        {tabs.map((item) => (
          <button key={item.id} type="button" role="tab" aria-selected={tab === item.id} onClick={() => setTab(item.id)}
            className={cx("inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold", tab === item.id ? "border-forest bg-forest text-white" : "border-line bg-surface text-forest hover:bg-canvas")}>
            <item.icon aria-hidden className="h-4 w-4" />
            {item.label}
            {item.count !== undefined && <span className="rounded-full bg-white/20 px-1.5 text-2xs">{item.count}</span>}
          </button>
        ))}
      </div>
      <div role="tabpanel">
        {tab === "inbound" && <DataTable rows={data?.inbound} columns={inbound} rowKey={(row) => row.id} caption={t("channels.inbound")} searchText={(row) => `${row.text ?? ""} ${row.reply ?? ""} ${row.phone_number ?? ""}`} {...common} />}
        {tab === "outbound" && <DataTable rows={data?.outbound} columns={outbound} rowKey={(row) => row.id} caption={t("channels.outbound")} searchText={(row) => `${row.message ?? ""} ${row.purpose ?? ""}`} {...common} />}
        {tab === "rewards" && <DataTable rows={data?.rewards} columns={rewards} rowKey={(row) => row.id} caption={t("channels.rewards")} searchText={(row) => row.reason} {...common} />}
      </div>
      <p className="text-xs text-muted">{t("channels.limit")}</p>
    </div>
  );
}
