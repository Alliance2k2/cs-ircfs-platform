import type { Feature, FeatureCollection, Geometry, Point, Position } from "geojson";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { useEffect, useRef } from "react";
import { useI18n } from "@/i18n";
import { tokenColor } from "@/lib/tokens";
import type { RainfallRow } from "@/services/api/schemas";
import { LEVEL_TOKEN } from "./levels";

const DISTRICT_CENTRE: [number, number] = [30.15, -2.22]; // longitude, latitude

interface SectorMapProps {
  rows: RainfallRow[];
  token: string;
  style: string;
}

/** Sector points as GeoJSON. Only coordinates stored in the platform are used; nothing is invented. */
function sectorFeatures(rows: RainfallRow[]): FeatureCollection<Point> {
  return {
    type: "FeatureCollection",
    features: rows
      .filter((row) => row.latitude !== null && row.longitude !== null)
      .map((row): Feature<Point> => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [row.longitude as number, row.latitude as number] },
        properties: { sector: row.sector, level: row.level, readings: row.readings, rainfall: row.rainfall_mm_7d },
      })),
  };
}

/** The bounding box of any GeoJSON, to frame Bugesera without hard-coding it. */
function bounds(geo: FeatureCollection<Geometry>): mapboxgl.LngLatBoundsLike | null {
  let west = Infinity, south = Infinity, east = -Infinity, north = -Infinity;
  const visit = (value: unknown) => {
    if (Array.isArray(value) && typeof value[0] === "number") {
      const [x = 0, y = 0] = value as Position;
      west = Math.min(west, x); south = Math.min(south, y);
      east = Math.max(east, x); north = Math.max(north, y);
    } else if (Array.isArray(value)) {
      value.forEach(visit);
    }
  };
  geo.features.forEach((feature) => {
    if (feature.geometry && "coordinates" in feature.geometry) visit(feature.geometry.coordinates);
  });
  return Number.isFinite(west) ? [[west, south], [east, north]] : null;
}

/**
 * Bugesera's boundary with one circle per sector, coloured by this week's irrigation
 * advice and sized by the number of rain-gauge readings.
 */
export default function SectorMap({ rows, token, style }: SectorMapProps) {
  const { t } = useI18n();
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const latestRows = useRef(rows);
  latestRows.current = rows;
  const translate = useRef(t);
  translate.current = t;

  useEffect(() => {
    if (!container.current) return;
    mapboxgl.accessToken = token;
    const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    const instance = new mapboxgl.Map({
      container: container.current,
      style,
      center: DISTRICT_CENTRE,
      zoom: 9.2,
      cooperativeGestures: true, // scrolling the page never hijacks the map
    });
    map.current = instance;
    instance.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "top-left");
    const popup = new mapboxgl.Popup({ closeButton: false, closeOnClick: false, offset: 12 });

    instance.on("load", async () => {
      instance.addSource("sectors", { type: "geojson", data: sectorFeatures(latestRows.current) });
      try {
        const response = await fetch("/app/data/bugesera-boundary.geojson");
        const boundary = (await response.json()) as FeatureCollection<Geometry>;
        instance.addSource("boundary", { type: "geojson", data: boundary });
        instance.addLayer({ id: "boundary-fill", type: "fill", source: "boundary", paint: { "fill-color": tokenColor("forest"), "fill-opacity": 0.05 } });
        instance.addLayer({ id: "boundary-line", type: "line", source: "boundary", paint: { "line-color": tokenColor("forest"), "line-width": 2 } });
        const box = bounds(boundary);
        if (box) instance.fitBounds(box, { padding: 16, animate: !reduceMotion });
      } catch {
        /* the sector circles still show without the outline */
      }
      instance.addLayer({
        id: "sectors",
        type: "circle",
        source: "sectors",
        paint: {
          "circle-color": [
            "match", ["get", "level"],
            "irrigate_more", tokenColor(LEVEL_TOKEN.irrigate_more),
            "reduce", tokenColor(LEVEL_TOKEN.reduce),
            "normal", tokenColor(LEVEL_TOKEN.normal),
            tokenColor(LEVEL_TOKEN.no_data),
          ],
          "circle-radius": ["+", 6, ["*", ["min", ["get", "readings"], 20], 0.4]],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
          "circle-opacity": 0.9,
        },
      });
      instance.on("mouseenter", "sectors", (event) => {
        const feature = event.features?.[0];
        if (!feature || feature.geometry.type !== "Point") return;
        instance.getCanvas().style.cursor = "pointer";
        const { sector, level, rainfall } = feature.properties as { sector: string; level: keyof typeof LEVEL_TOKEN; rainfall: number | null };
        const content = document.createElement("div");
        const name = document.createElement("strong");
        name.textContent = sector; // textContent: names from the database are never parsed as HTML
        const detail = `${translate.current(`advice.${level}`)}${rainfall !== null && rainfall !== undefined ? ` · ${rainfall} mm` : ""}`;
        content.append(name, document.createElement("br"), detail);
        popup.setLngLat(feature.geometry.coordinates as [number, number]).setDOMContent(content).addTo(instance);
      });
      instance.on("mouseleave", "sectors", () => {
        instance.getCanvas().style.cursor = "";
        popup.remove();
      });
    });

    return () => {
      popup.remove();
      instance.remove();
      map.current = null;
    };
  }, [token, style]);

  // New figures (filters, auto-refresh) update the circles without rebuilding the map.
  useEffect(() => {
    const source = map.current?.getSource("sectors") as mapboxgl.GeoJSONSource | undefined;
    source?.setData(sectorFeatures(rows));
  }, [rows]);

  return <div ref={container} role="img" aria-label={t("map.label")} className="h-full w-full overflow-hidden rounded-control" />;
}
