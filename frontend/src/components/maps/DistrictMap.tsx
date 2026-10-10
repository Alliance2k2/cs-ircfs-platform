import type { FeatureCollection, Geometry, Point } from "geojson";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { useEffect, useRef } from "react";
import { tokenColor } from "@/lib/tokens";
import { bounds } from "./SectorMap";
import { BASE_STYLES, loadMapView, saveMapView, TERRAIN_EXAGGERATION, ViewControl, type BaseMap, type MapView } from "./viewControl";

export type LayerId = "infrastructure" | "crops" | "heat" | "rain" | "food";
export type MapLayers = Record<LayerId, FeatureCollection<Point>>;

const CENTRE: [number, number] = [30.15, -2.22];
const TILT = { pitch: 62, bearing: -18 };
const FLAT = { pitch: 0, bearing: 0 };
const reduceMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
const empty = (): FeatureCollection<Point> => ({ type: "FeatureCollection", features: [] });

/** Mapbox layer ids drawn for each platform layer. */
const LAYER_IDS: Record<LayerId, string[]> = {
  heat: ["heat"],
  food: ["food"],
  rain: ["rain"],
  crops: ["crops"],
  infrastructure: ["infrastructure"],
};

interface DistrictMapProps {
  token: string;
  style: string;
  layers: MapLayers;
  visible: Set<LayerId>;
  label: string;
}

/**
 * Every mapped layer of the platform on one Mapbox map. Points come only from coordinates
 * stored with records; household and grievance locations are never sent to the browser.
 */
export default function DistrictMap({ token, style, layers, visible, label }: DistrictMapProps) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const latest = useRef({ layers, visible });
  latest.current = { layers, visible };

  useEffect(() => {
    if (!container.current) return;
    mapboxgl.accessToken = token;
    let view: MapView = loadMapView();
    let boundary: FeatureCollection<Geometry> | null = null;
    const styleFor = (base: BaseMap) => BASE_STYLES[base] ?? style;
    const instance = new mapboxgl.Map({
      container: container.current,
      style: styleFor(view.base),
      center: CENTRE,
      zoom: 9.2,
      maxPitch: 75,
      cooperativeGestures: true,
      ...(view.threeD ? TILT : FLAT),
    });
    map.current = instance;
    instance.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), "top-right");

    const applyThreeD = (move: boolean) => {
      if (view.threeD) {
        if (!instance.getSource("mapbox-dem")) instance.addSource("mapbox-dem", { type: "raster-dem", url: "mapbox://mapbox.mapbox-terrain-dem-v1", tileSize: 512, maxzoom: 14 });
        instance.setTerrain({ source: "mapbox-dem", exaggeration: TERRAIN_EXAGGERATION });
      } else {
        instance.setTerrain(null);
      }
      if (move) {
        const camera = view.threeD ? TILT : FLAT;
        if (reduceMotion()) instance.jumpTo(camera);
        else instance.easeTo({ ...camera, duration: 900 });
      }
    };
    instance.addControl(new ViewControl(
      () => view,
      (base) => {
        if (base === view.base) return;
        view = { ...view, base };
        saveMapView(view);
        instance.setStyle(styleFor(base));
      },
      () => {
        view = { ...view, threeD: !view.threeD };
        saveMapView(view);
        applyThreeD(true);
      },
    ), "top-left");

    const draw = () => {
      const data = latest.current.layers;
      const satellite = view.base === "satellite";
      if (boundary && !instance.getSource("boundary")) {
        instance.addSource("boundary", { type: "geojson", data: boundary });
        instance.addLayer({ id: "boundary-line", type: "line", source: "boundary", paint: { "line-color": satellite ? "#ffffff" : tokenColor("forest"), "line-width": 2 } });
      }
      (Object.keys(LAYER_IDS) as LayerId[]).forEach((id) => {
        if (!instance.getSource(id)) instance.addSource(id, { type: "geojson", data: data[id] ?? empty() });
      });
      if (!instance.getLayer("heat")) {
        instance.addLayer({
          id: "heat", type: "heatmap", source: "heat",
          paint: {
            "heatmap-weight": ["get", "weight"],
            "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 8, 18, 14, 40],
            "heatmap-opacity": 0.75,
            "heatmap-color": ["interpolate", ["linear"], ["heatmap-density"], 0, "rgba(0,0,0,0)", 0.3, tokenColor("amber", 0.6), 0.7, tokenColor("critical", 0.8), 1, tokenColor("critical")],
          },
        });
      }
      const circle = (id: LayerId, color: mapboxgl.ExpressionSpecification | string, radius: mapboxgl.ExpressionSpecification | number) => {
        if (instance.getLayer(id)) return;
        instance.addLayer({ id, type: "circle", source: id, paint: { "circle-color": color, "circle-radius": radius, "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.5, "circle-opacity": 0.9 } });
      };
      circle("food", ["interpolate", ["linear"], ["get", "risk"], 1, tokenColor("fresh"), 3, tokenColor("amber"), 5, tokenColor("critical")], ["+", 7, ["min", ["get", "households"], 15]]);
      circle("rain", tokenColor("water"), ["+", 4, ["*", ["min", ["get", "mm"], 40], 0.25]]);
      circle("crops", ["case", ["==", ["get", "status"], "pest alert"], tokenColor("critical"), tokenColor("primary")], 5);
      circle("infrastructure", ["match", ["get", "status"], "faulty", tokenColor("amber"), "offline", tokenColor("critical"), tokenColor("forest")], 8);
      syncVisibility();
      applyThreeD(false);
    };
    const syncVisibility = () => {
      (Object.keys(LAYER_IDS) as LayerId[]).forEach((id) =>
        LAYER_IDS[id].forEach((layer) => instance.getLayer(layer) && instance.setLayoutProperty(layer, "visibility", latest.current.visible.has(id) ? "visible" : "none")));
    };
    instance.on("style.load", draw);

    const popup = new mapboxgl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
    (["infrastructure", "crops", "rain", "food"] as const).forEach((id) => {
      instance.on("mouseenter", id, (event) => {
        const feature = event.features?.[0];
        if (!feature || feature.geometry.type !== "Point") return;
        instance.getCanvas().style.cursor = "pointer";
        const { title, detail } = feature.properties as { title: string; detail?: string };
        const content = document.createElement("div");
        const name = document.createElement("strong");
        name.textContent = title; // never parsed as HTML
        content.append(name);
        if (detail) content.append(document.createElement("br"), detail);
        popup.setLngLat(feature.geometry.coordinates as [number, number]).setDOMContent(content).addTo(instance);
      });
      instance.on("mouseleave", id, () => {
        instance.getCanvas().style.cursor = "";
        popup.remove();
      });
    });

    fetch("/app/data/bugesera-boundary.geojson")
      .then((response) => response.json() as Promise<FeatureCollection<Geometry>>)
      .then((geo) => {
        boundary = geo;
        const fit = () => {
          draw();
          (["heat", "food", "rain", "crops", "infrastructure"] as const).forEach((id) => instance.getLayer(id) && instance.moveLayer(id));
          const box = bounds(geo);
          if (box) instance.fitBounds(box, { padding: 16, ...(view.threeD ? TILT : FLAT), animate: !reduceMotion() });
        };
        if (instance.isStyleLoaded()) fit();
        else instance.once("style.load", fit);
      })
      .catch(() => undefined);

    (instance as mapboxgl.Map & { syncVisibility?: () => void }).syncVisibility = syncVisibility;
    return () => {
      popup.remove();
      instance.remove();
      map.current = null;
    };
  }, [token, style]);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    (Object.keys(layers) as LayerId[]).forEach((id) => (instance.getSource(id) as mapboxgl.GeoJSONSource | undefined)?.setData(layers[id]));
  }, [layers]);

  useEffect(() => {
    (map.current as (mapboxgl.Map & { syncVisibility?: () => void }) | null)?.syncVisibility?.();
  }, [visible]);

  return <div ref={container} role="img" aria-label={label} className="h-full w-full overflow-hidden rounded-control" />;
}
