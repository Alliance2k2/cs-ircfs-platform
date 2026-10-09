import type { ExecutiveOverview, Metric } from "@/services/api/schemas";

export const metric = (overrides: Partial<Metric> = {}): Metric => ({
  key: "citizen_reports",
  label: "Citizen reports",
  value: 126,
  unit: "reports",
  period: "Last 30 days",
  definition: "Crop, pest, rainfall and infrastructure reports received.",
  source: "live_unverified",
  note: null,
  ...overrides,
});

export const overview = (overrides: Partial<ExecutiveOverview> = {}): ExecutiveOverview => ({
  generated_at: "2026-10-09T10:00:00Z",
  period: { days: 30, start: "2026-09-09T10:00:00Z", end: "2026-10-09T10:00:00Z" },
  filters: { scheme_id: null, sector_id: null },
  demo_mode: false,
  metrics: [
    metric(),
    metric({ key: "rainfall_7d", label: "Rainfall, 7 days", value: null, unit: "mm", source: "missing", note: "No rain-gauge readings in the last 7 days" }),
  ],
  schemes: [
    {
      scheme_id: 1,
      name: "PADAB",
      implementing_partner: "AfDB",
      hectares_developed: 650,
      reports: 12,
      pest_alerts: 2,
      fault_reports: 3,
      assets_down: 1,
      assets_reported: 3,
      open_grievances: 1,
      reported_harvest: metric({ key: "reported_harvest", label: "Reported harvest", value: 8.5, unit: "t" }),
      yield_target: metric({ key: "yield_target", label: "Yield target", value: null, unit: "t", source: "missing", note: "No documented target entered yet" }),
      yield_achievement: metric({ key: "yield_achievement", label: "Yield achievement", value: null, unit: "%", source: "missing", note: "Not calculated." }),
    },
  ],
  assets: [
    {
      asset: "PADAB Pumping Station 1",
      scheme_id: 1,
      status: "offline",
      down: true,
      bottleneck: "technical",
      description: null,
      cell_id: 1,
      reported_at: "2026-10-08T10:00:00Z",
    },
  ],
  rainfall: [
    {
      sector_id: 1,
      sector: "Ngeruka",
      rainfall_mm_7d: 6,
      readings: 4,
      forecast_mm_7d: 21,
      level: "irrigate_more",
      advice: "Dry",
      threshold_source: null,
      latitude: -2.3,
      longitude: 30.1,
    },
  ],
  priority_actions: [
    {
      item_type: "infrastructure",
      item_id: 4,
      priority: "critical",
      title: "PADAB Pumping Station 1 is offline",
      status: "open",
      sector: "Mayange",
      scheme_id: 1,
      created_at: "2026-10-08T10:00:00Z",
      due_at: null,
      assigned: false,
    },
  ],
  recent_reports: [{ kind: "pest", label: "Fall armyworm on Maize, severity 5", sector: "Nyamata", created_at: "2026-10-09T09:00:00Z", origin: "field" }],
  ...overrides,
});
