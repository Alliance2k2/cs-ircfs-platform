import { ClipboardList, CloudRain, ListChecks, MapPinned, Siren, Timer, Users, Wrench, type LucideIcon } from "lucide-react";
import type { Accent } from "@/components/ui/MetricCard";

/** Icon and accent per headline figure (keys from backend/app/services/executive.py). */
export const METRIC_STYLE: Record<string, { icon: LucideIcon; accent: Accent }> = {
  citizen_reports: { icon: ClipboardList, accent: "green" },
  active_reporters: { icon: Users, accent: "blue" },
  reporting_coverage: { icon: MapPinned, accent: "teal" },
  critical_incidents: { icon: Siren, accent: "coral" },
  open_actions: { icon: ListChecks, accent: "gold" },
  assets_down: { icon: Wrench, accent: "coral" },
  rainfall_7d: { icon: CloudRain, accent: "blue" },
  median_days_to_resolve: { icon: Timer, accent: "violet" },
};
