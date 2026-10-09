import { Bug, CloudRain, Droplets, Sprout, Wrench } from "lucide-react";
import { DataState } from "@/components/feedback/DataState";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { useI18n } from "@/i18n";
import { relativeTime } from "@/lib/format";
import type { RecentReport } from "@/services/api/schemas";

const ICON = { pest: Bug, harvest: Sprout, rain: CloudRain, fault: Wrench, water: Droplets } as const;
const TINT = { pest: "text-amber bg-amber-soft", fault: "text-critical bg-critical-soft", rain: "text-water bg-water-soft" } as const;

export function RecentReports({ reports }: { reports: RecentReport[] }) {
  const { t, lang } = useI18n();
  return (
    <Card aria-labelledby="recent-title">
      <CardHeader id="recent-title" title={t("section.recent")} note={t("section.recentNote")} />
      {reports.length === 0 ? (
        <DataState kind="empty" message={t("section.recentEmpty")} />
      ) : (
        <ul className="grid divide-y divide-line md:grid-cols-2 md:divide-y-0">
          {reports.map((report, index) => {
            const Icon = ICON[report.kind as keyof typeof ICON] ?? Droplets;
            const tint = TINT[report.kind as keyof typeof TINT] ?? "text-primary bg-mint";
            return (
              <li key={`${report.created_at}-${index}`} className="flex items-center gap-3 px-5 py-3 md:border-b md:border-line">
                <span aria-hidden className={`grid h-8 w-8 shrink-0 place-items-center rounded-control ${tint}`}>
                  <Icon className="h-4 w-4" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-ink">{report.label}</span>
                  <span className="block text-xs text-muted">{[report.sector, relativeTime(report.created_at, lang)].filter(Boolean).join(" · ")}</span>
                </span>
                {report.origin === "demo" && <Badge tone="warning">{t("source.demo")}</Badge>}
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
