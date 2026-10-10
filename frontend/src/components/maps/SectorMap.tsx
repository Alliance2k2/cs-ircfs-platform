import type { Feature, FeatureCollection, Geometry, Point, Position } from "geojson";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { useEffect, useRef } from "react";
import { useI18n } from "@/i18n";
import { tokenColor } from "@/lib/tokens";
import type { RainfallRow } from "@/services/api/schemas";
import { LEVEL_TOKEN } from "./levels";
import { BASE_STYLES, loadMapView, saveMapView, TERRAIN_EXAGGERATION, ViewControl, type BaseMap, type MapView } from "./viewControl";

const DISTRICT_CENTRE: [number, number] = [30.15, -2.22]; // longitude, latitude
const TILT = { pitch: 62, bearing: -18 };
const FLAT = { pitch: 0, bearing: 0 };

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
export function bounds(geo: FeatureCollection<Geometry>): mapboxgl.LngLatBoundsLike | null {
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

const reduceMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

/**
 * Bugesera's boundary with one circle per sector, coloured by this week's irrigation
 * advice and sized by the number of rain-gauge readings. Map, satellite or terrain base,
 * flat or 3D, chosen in the map's corner and remembered on this device.
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
    let view: MapView = loadMapView();
    let boundary: FeatureCollection<Geometry> | null = null;
    const styleFor = (base: BaseMap) => BASE_STYLES[base] ?? style;

    const instance = new mapboxgl.Map({
      container: container.current,
      style: styleFor(view.base),
      center: DISTRICT_CENTRE,
      zoom: 9.2,
      maxPitch: 75,
      cooperativeGestures: true, // scrolling the page never hijacks the map
      ...(view.threeD ? TILT : FLAT),
    });
    map.current = instance;
    instance.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), "top-right");

    const applyThreeD = (move: boolean) => {
      if (view.threeD) {
        if (!instance.getSource("mapbox-dem")) {
          instance.addSource("mapbox-dem", { type: "raster-dem", url: "mapbox://mapbox.mapbox-terrain-dem-v1", tileSize: 512, maxzoom: 14 });
        }
        instance.setTerrain({ source: "mapbox-dem", exaggeration: TERRAIN_EXAGGERATION });
        instance.setFog({ range: [1, 12], color: "#eef4f0", "horizon-blend": 0.08 });
      } else {
        instance.setTerrain(null);
        instance.setFog(null as unknown as mapboxgl.FogSpecification);
      }
      if (!move) return;
      const camera = view.threeD ? TILT : FLAT;
      if (reduceMotion()) instance.jumpTo(camera);
      else instance.easeTo({ ...camera, duration: 900 });
    };

    const control = new ViewControl(
      () => view,
      (base) => {
        if (base === view.base) return;
        view = { ...view, base };
        saveMapView(view);
        instance.setStyle(styleFor(base)); // "style.load" redraws our layers
      },
      () => {
        view = { ...view, threeD: !view.threeD };
        saveMapView(view);
        applyThreeD(true);
      },
    );
    instance.addControl(control, "top-left");

    // Each style load (the first and every base-map switch) redraws the platform's layers.
    const addLayers = () => {
      const satellite = view.base === "satellite";
      if (!instance.getSource("sectors")) instance.addSource("sectors", { type: "geojson", data: sectorFeatures(latestRows.current) });
      if (boundary && !instance.getSource("boundary")) {
        instance.addSource("boundary", { type: "geojson", data: boundary });
        instance.addLayer({ id: "boundary-fill", type: "fill", source: "boundary", paint: { "fill-color": tokenColor("forest"), "fill-opacity": satellite ? 0.03 : 0.05 } });
        instance.addLayer({ id: "boundary-line", type: "line", source: "boundary", paint: { "line-color": satellite ? "#ffffff" : tokenColor("forest"), "line-width": 2 } });
      }
      if (!instance.getLayer("sectors")) {
        instance.addLayer({
          id: "sectors",
          type: "circle",
          source: "sectors",
          paint: {
            "circle-color": [
              "match", ["get", "level"],
              "irrigate_more", tokenColor(LEVEL_TOKEN.irrigate_more),
              "irrigate_less", tokenColor(LEVEL_TOKEN.irrigate_less),
              "normal", tokenColor(LEVEL_TOKEN.normal),
              tokenColor(LEVEL_TOKEN.no_data),
            ],
            "circle-radius": ["+", 6, ["*", ["min", ["get", "readings"], 20], 0.4]],
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 2,
            "circle-opacity": 0.92,
          },
        });
      }
      applyThreeD(false);
    };
    instance.on("style.load", addLayers);

    const popup = new mapboxgl.Popup({ closeButton: false, closeOnClick: false, offset: 12 });
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

    // The district outline: drawn once loaded, and kept for later base-map switches.
    fetch("/app/data/bugesera-boundary.geojson")
      .then((response) => response.json() as Promise<FeatureCollection<Geometry>>)
      .then((geo) => {
        boundary = geo;
        const draw = () => {
          addLayers();
          if (instance.getLayer("sectors")) instance.moveLayer("sectors"); // keep the circles on top of the outline
          const box = bounds(geo);
          if (box) instance.fitBounds(box, { padding: 16, ...(view.threeD ? TILT : FLAT), animate: !reduceMotion() });
        };
        if (instance.isStyleLoaded()) draw();
        else instance.once("style.load", draw);
      })
      .catch(() => undefined); // the sector circles still show without the outline

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
