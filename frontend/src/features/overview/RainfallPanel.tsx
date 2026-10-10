import { useQuery } from "@tanstack/react-query";
import { CloudRain, MapPinOff, TriangleAlert } from "lucide-react";
import { lazy, Suspense } from "react";
import { LEVEL_TOKEN } from "@/components/maps/levels";
import { Card, CardHeader } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { useI18n } from "@/i18n";
import { formatNumber } from "@/lib/format";
import { tokenColor } from "@/lib/tokens";
import { apiGet } from "@/services/api/client";
import { mapConfigSchema, type AdviceLevel, type RainfallRow } from "@/services/api/schemas";

// Mapbox GL is the heaviest dependency: load it only when a token exists and this panel renders.
const SectorMap = lazy(() => import("@/components/maps/SectorMap"));
const ORDER: AdviceLevel[] = ["irrigate_more", "reduce", "normal", "no_data"];

export function RainfallPanel({ rows }: { rows: RainfallRow[] }) {
  const { t, lang } = useI18n();
  const sorted = [...rows].sort((a, b) => ORDER.indexOf(a.level) - ORDER.indexOf(b.level) || a.sector.localeCompare(b.sector));
  const uncalibrated = rows.some((row) => row.level !== "no_data" && !row.threshold_source);
  const mapConfig = useQuery({
    queryKey: ["map-config"],
    queryFn: ({ signal }) => apiGet("public/map-config", mapConfigSchema, signal),
    staleTime: Infinity,
  });
  const token = mapConfig.data?.mapbox_token;

  return (
    <Card className="flex flex-col" aria-labelledby="rain-title">
      <CardHeader id="rain-title" title={t("section.map")} note={t("section.mapNote")} />
      <div className="h-[22rem] p-3">
        {mapConfig.isPending ? (
          <Skeleton className="h-full w-full" />
        ) : token ? (
          <Suspense fallback={<Skeleton className="h-full w-full" />}>
            <SectorMap rows={rows} token={token} style={mapConfig.data?.style ?? "mapbox://styles/mapbox/light-v11"} />
          </Suspense>
        ) : (
          <div role="status" className="flex h-full flex-col items-center justify-center gap-2 rounded-control border border-dashed border-line bg-canvas px-6 text-center">
            <MapPinOff aria-hidden className="h-6 w-6 text-muted" />
            <p className="max-w-xs text-sm text-muted">{t("map.noToken")}</p>
          </div>
        )}
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 px-5 pb-3 text-xs text-muted" aria-label={t("section.map")}>
        {ORDER.map((level) => (
          <li key={level} className="flex items-center gap-1.5">
            <span aria-hidden className="h-2.5 w-2.5 rounded-full" style={{ background: tokenColor(LEVEL_TOKEN[level]) }} />
            {t(`advice.${level}`)}
          </li>
        ))}
      </ul>
      <ul className="max-h-64 divide-y divide-line overflow-y-auto border-t border-line">
        {sorted.map((row) => (
          <li key={row.sector_id} className="flex items-center gap-3 px-5 py-2.5">
            <span aria-hidden className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: tokenColor(LEVEL_TOKEN[row.level]) }} />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold text-ink">{row.sector}</span>
              <span className="block text-xs text-muted">
                {t(`advice.${row.level}`)}
                {row.forecast_mm_7d !== null && ` · ${t("advice.forecast", { mm: formatNumber(row.forecast_mm_7d, lang) })}`}
              </span>
            </span>
            {row.rainfall_mm_7d !== null && (
              <span className="tabular inline-flex items-center gap-1 text-sm font-bold text-water">
                <CloudRain aria-hidden className="h-4 w-4" />
                {formatNumber(row.rainfall_mm_7d, lang)} mm
              </span>
            )}
          </li>
        ))}
      </ul>
      {uncalibrated && (
        <p className="flex gap-2 border-t border-line bg-amber-soft/60 px-5 py-2.5 text-xs text-amber">
          <TriangleAlert aria-hidden className="mt-px h-4 w-4 shrink-0" />
          {t("advice.unvalidated")}
        </p>
      )}
    </Card>
  );
}
