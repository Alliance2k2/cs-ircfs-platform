import type { AdviceLevel } from "@/services/api/schemas";

/** Irrigation advice level -> colour token. Kept apart from SectorMap so importing it does not load Mapbox GL. */
export const LEVEL_TOKEN: Record<AdviceLevel, string> = {
  irrigate_more: "amber",
  normal: "primary",
  reduce: "water",
  no_data: "muted",
};
