import { DataState } from "@/components/feedback/DataState";
import { Badge, type Tone } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { useI18n } from "@/i18n";
import { relativeTime } from "@/lib/format";
import type { Asset, SchemeRow } from "@/services/api/schemas";

const TONE: Record<string, Tone> = { operational: "good", faulty: "warning", offline: "critical" };
const VISIBLE = 6;

export function AssetHealth({ assets, schemes }: { assets: Asset[]; schemes: SchemeRow[] }) {
  const { t, lang } = useI18n();
  const schemeName = new Map(schemes.map((scheme) => [scheme.scheme_id, scheme.name]));
  const status = (value: string) => (value === "operational" || value === "faulty" || value === "offline" ? t(`status.${value}`) : value);

  return (
    <Card className="flex flex-col" aria-labelledby="assets-title">
      <CardHeader id="assets-title" title={t("section.assets")} note={t("section.assetsNote")} />
      {assets.length === 0 ? (
        <DataState kind="empty" message={t("section.assetsEmpty")} />
      ) : (
        <ul className="divide-y divide-line">
          {assets.slice(0, VISIBLE).map((asset) => (
            <li key={`${asset.scheme_id}-${asset.asset}`} className="flex items-start justify-between gap-3 px-5 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-ink">{asset.asset}</p>
                <p className="mt-0.5 truncate text-xs text-muted">
                  {[asset.scheme_id ? schemeName.get(asset.scheme_id) : null, asset.bottleneck, relativeTime(asset.reported_at, lang)]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
              <Badge tone={TONE[asset.status] ?? "neutral"}>{status(asset.status)}</Badge>
            </li>
          ))}
          {assets.length > VISIBLE && (
            <li className="px-5 py-2.5 text-xs text-muted">{t("section.assetsMore", { n: assets.length - VISIBLE })}</li>
          )}
        </ul>
      )}
    </Card>
  );
}
