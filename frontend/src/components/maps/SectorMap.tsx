import type { GeoJsonObject } from "geojson";
import type { LatLngBoundsExpression } from "leaflet";
import { useEffect, useState } from "react";
import { CircleMarker, GeoJSON, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import { useI18n } from "@/i18n";
import { tokenColor } from "@/lib/tokens";
import type { RainfallRow } from "@/services/api/schemas";
import { LEVEL_TOKEN } from "./levels";

const DISTRICT_CENTRE: [number, number] = [-2.22, 30.15];

function FitBounds({ bounds }: { bounds: LatLngBoundsExpression | null }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) map.fitBounds(bounds, { padding: [12, 12] });
  }, [map, bounds]);
  return null;
}

/**
 * Bugesera's boundary with one circle per sector, coloured by this week's irrigation
 * advice. Only coordinates stored in the platform are used; nothing is invented.
 */
export default function SectorMap({ rows }: { rows: RainfallRow[] }) {
  const { t } = useI18n();
  const [boundary, setBoundary] = useState<GeoJsonObject | null>(null);
  const [bounds, setBounds] = useState<LatLngBoundsExpression | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/app/data/bugesera-boundary.geojson", { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : null))
      .then((geo: GeoJsonObject | null) => setBoundary(geo))
      .catch(() => undefined); // the circles still show without the outline
    return () => controller.abort();
  }, []);

  return (
    <div role="img" aria-label={t("map.label")} className="h-full w-full">
      <MapContainer center={DISTRICT_CENTRE} zoom={10} scrollWheelZoom={false} className="h-full w-full rounded-control" attributionControl>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap contributors" maxZoom={18} opacity={0.55} />
        {boundary && (
          <GeoJSON
            data={boundary}
            interactive={false}
            style={{ color: tokenColor("forest"), weight: 2, fillColor: tokenColor("forest"), fillOpacity: 0.04 }}
            eventHandlers={{ add: (event) => setBounds(event.target.getBounds()) }}
          />
        )}
        <FitBounds bounds={bounds} />
        {rows
          .filter((row) => row.latitude !== null && row.longitude !== null)
          .map((row) => (
            <CircleMarker
              key={row.sector_id}
              center={[row.latitude as number, row.longitude as number]}
              radius={6 + Math.min(row.readings, 20) * 0.4}
              pathOptions={{ color: "#fff", weight: 2, fillColor: tokenColor(LEVEL_TOKEN[row.level]), fillOpacity: 0.9 }}
            >
              <Tooltip direction="top" className="cs-tip">
                <strong>{row.sector}</strong>
                <br />
                {t(`advice.${row.level}`)}
                {row.rainfall_mm_7d !== null && ` · ${row.rainfall_mm_7d} mm`}
              </Tooltip>
            </CircleMarker>
          ))}
      </MapContainer>
    </div>
  );
}
