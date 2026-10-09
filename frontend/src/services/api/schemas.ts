import { z } from "zod";

/** Mirrors backend/app/services/executive.py. Keep the two in step. */
export const metricSource = z.enum(["live_unverified", "platform", "documented", "demo", "missing"]);
export type MetricSource = z.infer<typeof metricSource>;

export const metricSchema = z.object({
  key: z.string(),
  label: z.string(),
  value: z.number().nullable(),
  unit: z.string(),
  period: z.string(),
  definition: z.string(),
  source: metricSource,
  note: z.string().nullable(),
});
export type Metric = z.infer<typeof metricSchema>;

const timestamp = z.string();

export const schemeRowSchema = z.object({
  scheme_id: z.number(),
  name: z.string(),
  implementing_partner: z.string().nullable(),
  hectares_developed: z.number().nullable(),
  reports: z.number(),
  pest_alerts: z.number(),
  fault_reports: z.number(),
  assets_down: z.number(),
  assets_reported: z.number(),
  open_grievances: z.number(),
  reported_harvest: metricSchema,
  yield_target: metricSchema,
  yield_achievement: metricSchema,
});
export type SchemeRow = z.infer<typeof schemeRowSchema>;

export const assetSchema = z.object({
  asset: z.string(),
  scheme_id: z.number().nullable(),
  status: z.string(),
  down: z.boolean(),
  bottleneck: z.string().nullable(),
  description: z.string().nullable(),
  cell_id: z.number().nullable(),
  reported_at: timestamp,
});
export type Asset = z.infer<typeof assetSchema>;

export const adviceLevel = z.enum(["irrigate_more", "normal", "reduce", "no_data"]);
export type AdviceLevel = z.infer<typeof adviceLevel>;

export const rainfallRowSchema = z.object({
  sector_id: z.number(),
  sector: z.string(),
  rainfall_mm_7d: z.number().nullable(),
  readings: z.number(),
  forecast_mm_7d: z.number().nullable(),
  level: adviceLevel.catch("no_data"),
  advice: z.string(),
  threshold_source: z.string().nullable(),
  latitude: z.number().nullable(),
  longitude: z.number().nullable(),
});
export type RainfallRow = z.infer<typeof rainfallRowSchema>;

export const priorityActionSchema = z.object({
  item_type: z.string(),
  item_id: z.number(),
  priority: z.string(),
  title: z.string(),
  status: z.string(),
  sector: z.string().nullable(),
  scheme_id: z.number().nullable(),
  created_at: timestamp,
  due_at: timestamp.nullable(),
  assigned: z.boolean(),
});
export type PriorityAction = z.infer<typeof priorityActionSchema>;

export const recentReportSchema = z.object({
  kind: z.string(),
  label: z.string(),
  sector: z.string().nullable(),
  created_at: timestamp,
  origin: z.string(),
});
export type RecentReport = z.infer<typeof recentReportSchema>;

export const executiveOverviewSchema = z.object({
  generated_at: timestamp,
  period: z.object({ days: z.number(), start: timestamp, end: timestamp }),
  filters: z.object({ scheme_id: z.number().nullable(), sector_id: z.number().nullable() }),
  demo_mode: z.boolean(),
  metrics: z.array(metricSchema),
  schemes: z.array(schemeRowSchema),
  assets: z.array(assetSchema),
  rainfall: z.array(rainfallRowSchema),
  priority_actions: z.array(priorityActionSchema).nullable(),
  recent_reports: z.array(recentReportSchema),
});
export type ExecutiveOverview = z.infer<typeof executiveOverviewSchema>;

export const roleSchema = z.enum([
  "farmer",
  "citizen_science_monitor",
  "cooperative_leader",
  "district_officer",
  "district_planner",
  "administrator",
]);
export type Role = z.infer<typeof roleSchema>;

export const accountSchema = z.object({
  id: z.number(),
  email: z.string(),
  full_name: z.string(),
  role: roleSchema,
  status: z.string(),
  sector_ids: z.array(z.number()),
  area: z.string(),
});
export type Account = z.infer<typeof accountSchema>;

export const authConfigSchema = z.object({
  google_client_id: z.string().nullable(),
  development_bypass: z.boolean().default(false),
});

export const schemeSchema = z.object({ id: z.number(), name: z.string(), is_active: z.boolean() });
export const sectorSchema = z.object({ id: z.number(), name: z.string() });
