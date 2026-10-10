import { useQuery } from "@tanstack/react-query";
import type { Feature, FeatureCollection, Point } from "geojson";
import { MapPinOff, RefreshCw } from "lucide-react";
import { lazy, Suspense, useMemo, useState } from "react";
import { z } from "zod";
import type { LayerId, MapLayers } from "@/components/maps/DistrictMap";
import { PageHeader } from "@/components/layout/PageHeader";
import { DataState } from "@/components/feedback/DataState";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { canAccess } from "@/app/access";
import { useSession } from "@/app/providers/SessionProvider";
import { useI18n } from "@/i18n";
import { cx } from "@/lib/cx";
import { tokenColor } from "@/lib/tokens";
import { apiGet } from "@/services/api/client";
import { useApi } from "@/services/api/hooks";
import { mapConfigSchema } from "@/services/api/schemas";
import { nutritionSchema } from "@/services/api/workspaces";

const DistrictMap = lazy(() => import("@/components/maps/DistrictMap"));

const mapDataSchema = z.object({
  features: z.array(z.object({
    id: z.string(), feature_type: z.string(), name: z.string(), latitude: z.number(), longitude: z.number(),
    status: z.string().nullable(), scheme_id: z.number().nullable(), details: z.string().nullable(),
  })),
  spatial_available: z.boolean(),
});
const heatSchema = z.array(z.object({ latitude: z.number(), longitude: z.number(), weight: z.number(), pest: z.string().nullable(), crop: z.string().nullable(), severity: z.number().nullable() }));

const point = (longitude: number, latitude: number, properties: Record<string, unknown>): Feature<Point> => ({ type: "Feature", geometry: { type: "Point", coordinates: [longitude, latitude] }, properties });
const collection = (features: Feature<Point>[]): FeatureCollection<Point> => ({ type: "FeatureCollection", features });

const LAYERS: { id: LayerId; color: string; analyst?: boolean }[] = [
  { id: "infrastructure", color: "forest" },
  { id: "crops", color: "primary" },
  { id: "heat", color: "critical", analyst: true },
  { id: "rain", color: "water" },
  { id: "food", color: "amber", analyst: true },
];

/** All mapped evidence on one map, with layers to switch on and off. */
export function MapPage() {
  const { t } = useI18n();
  const { role } = useSession();
  const analyst = canAccess(role, "analyst");
  const config = useQuery({ queryKey: ["map-config"], queryFn: ({ signal }) => apiGet("public/map-config", mapConfigSchema, signal), staleTime: Infinity });
  const data = useApi("map-data", mapDataSchema);
  const heat = useApi(analyst ? "analytics/pest-heatmap?days=90" : null, heatSchema);
  const food = useApi(analyst ? "analytics/nutrition-summary" : null, nutritionSchema);
  const available = LAYERS.filter((layer) => analyst || !layer.analyst);
  const [visible, setVisible] = useState<Set<LayerId>>(new Set(["infrastructure", "crops", "rain"]));

  const layers = useMemo<MapLayers>(() => {
    const features = data.data?.features ?? [];
    const of = (type: string) => features.filter((item) => item.feature_type === type);
    return {
      infrastructure: collection(of("irrigation").map((item) => point(item.longitude, item.latitude, { title: item.name, status: item.status, detail: [item.status, item.details].filter(Boolean).join(" · ") }))),
      crops: collection(of("crop").map((item) => point(item.longitude, item.latitude, { title: item.name, status: item.status, detail: item.details ?? item.status }))),
      rain: collection(of("rainfall").map((item) => point(item.longitude, item.latitude, { title: item.name, mm: Number.parseFloat(item.status ?? "0") || 0, detail: item.status }))),
      heat: collection((heat.data ?? []).map((item) => point(item.longitude, item.latitude, { weight: item.weight }))),
      // Only cells with enough households to show a score; never single households.
      food: collection((food.data?.by_cell ?? []).filter((cell) => !cell.suppressed && cell.latitude !== null && cell.longitude !== null)
        .map((cell) => point(cell.longitude!, cell.latitude!, { title: cell.cell, risk: cell.average_risk ?? 0, households: cell.households, detail: `${cell.households} · ${cell.average_risk ?? "—"} / 5` }))),
    };
  }, [data.data, heat.data, food.data]);

  const count = (id: LayerId) => layers[id].features.length;
  const toggle = (id: LayerId) => setVisible((current) => {
    const next = new Set(current);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  });
  const token = config.data?.mapbox_token;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t("map.eyebrow")}
        title={t("map.title")}
        description={t("map.description")}
        updatedAt={data.dataUpdatedAt}
        actions={<Button icon={RefreshCw} onClick={() => { void data.refetch(); void heat.refetch(); void food.refetch(); }} loading={data.isFetching}>{t("filter.refresh")}</Button>}
      />
      <div className="grid gap-4 lg:grid-cols-[16rem_1fr]">
        <Card className="h-fit p-4">
          <fieldset>
            <legend className="text-2xs font-bold uppercase tracking-wider text-muted">{t("map.layers")}</legend>
            <ul className="mt-2 space-y-1">
              {available.map((layer) => (
                <li key={layer.id}>
                  <label className={cx("flex cursor-pointer items-center gap-3 rounded-control px-2 py-2 text-sm hover:bg-canvas", visible.has(layer.id) ? "text-ink" : "text-muted")}>
                    <input type="checkbox" checked={visible.has(layer.id)} onChange={() => toggle(layer.id)} className="h-4 w-4" />
                    <span aria-hidden className="h-3 w-3 shrink-0 rounded-full" style={{ background: tokenColor(layer.color) }} />
                    <span className="flex-1">{t(`map.layer.${layer.id}`)}</span>
                    <span className="text-xs tabular-nums text-muted">{count(layer.id)}</span>
                  </label>
                </li>
              ))}
            </ul>
          </fieldset>
          <p className="mt-3 text-xs text-muted">{t("map.privacy")}</p>
          {data.data && !data.data.spatial_available && <p className="mt-2 text-xs text-muted">{t("map.pointsOnly")}</p>}
        </Card>
        <Card className="h-[34rem] p-2 lg:h-[40rem]">
          {config.isPending || data.isPending ? (
            <Skeleton className="h-full w-full" />
          ) : data.error ? (
            <DataState kind="error" message={data.error.message} onRetry={() => void data.refetch()} />
          ) : token ? (
            <Suspense fallback={<Skeleton className="h-full w-full" />}>
              <DistrictMap token={token} style={config.data?.style ?? "mapbox://styles/mapbox/light-v11"} layers={layers} visible={visible} label={t("map.title")} />
            </Suspense>
          ) : (
            <div role="status" className="flex h-full flex-col items-center justify-center gap-2 rounded-control border border-dashed border-line bg-canvas px-6 text-center">
              <MapPinOff aria-hidden className="h-6 w-6 text-muted" />
              <p className="max-w-xs text-sm text-muted">{t("map.noToken")}</p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
