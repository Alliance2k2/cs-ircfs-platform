import type { IControl } from "mapbox-gl";

export type BaseMap = "map" | "satellite" | "terrain";
export interface MapView {
  base: BaseMap;
  threeD: boolean;
}

/** "map" uses MAPBOX_STYLE from the server; the others are Mapbox's own styles. */
export const BASE_STYLES: Partial<Record<BaseMap, string>> = {
  satellite: "mapbox://styles/mapbox/satellite-streets-v12",
  terrain: "mapbox://styles/mapbox/outdoors-v12",
};
export const BASE_LABELS: Record<BaseMap, string> = { map: "Map", satellite: "Satellite", terrain: "Terrain" };
/** Bugesera's hills are gentle; lift them so the 3D relief reads clearly. */
export const TERRAIN_EXAGGERATION = 1.8;
const STORAGE_KEY = "cs_ircfs_map_view"; // shared with the classic Map page

export function loadMapView(): MapView {
  try {
    const saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "{}") as Partial<MapView>;
    return { base: saved.base && saved.base in BASE_LABELS ? saved.base : "map", threeD: saved.threeD === true };
  } catch {
    return { base: "map", threeD: false };
  }
}

export function saveMapView(view: MapView) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(view));
  } catch {
    /* storage blocked: the choice lasts for this visit */
  }
}

/** Map / Satellite / Terrain and 3D, as one Mapbox control in the map's corner. */
export class ViewControl implements IControl {
  private container: HTMLDivElement | null = null;
  private buttons: [BaseMap, HTMLButtonElement][] = [];
  private threeD: HTMLButtonElement | null = null;

  constructor(
    private readonly view: () => MapView,
    private readonly onBase: (base: BaseMap) => void,
    private readonly onThreeD: () => void,
  ) {}

  onAdd(): HTMLElement {
    const container = document.createElement("div");
    container.className = "mapboxgl-ctrl cs-view-ctrl";
    const group = document.createElement("div");
    group.className = "cs-view-bases";
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", "Base map");
    this.buttons = (Object.keys(BASE_LABELS) as BaseMap[]).map((base) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = BASE_LABELS[base];
      button.addEventListener("click", () => {
        this.onBase(base);
        this.update();
      });
      group.append(button);
      return [base, button];
    });
    const threeD = document.createElement("button");
    threeD.type = "button";
    threeD.className = "cs-view-3d";
    threeD.textContent = "3D";
    threeD.title = "Tilt the map and show the land's relief";
    threeD.addEventListener("click", () => {
      this.onThreeD();
      this.update();
    });
    container.append(group, threeD);
    this.container = container;
    this.threeD = threeD;
    this.update();
    return container;
  }

  update() {
    const view = this.view();
    this.buttons.forEach(([base, button]) => button.setAttribute("aria-pressed", String(view.base === base)));
    this.threeD?.setAttribute("aria-pressed", String(view.threeD));
  }

  onRemove() {
    this.container?.remove();
    this.container = null;
  }
}
