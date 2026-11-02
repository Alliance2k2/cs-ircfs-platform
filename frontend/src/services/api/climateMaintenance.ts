import { z } from "zod";

export const rainfallReferenceSchema = z.object({
  id: z.number(), sector_id: z.number().nullable(), scheme_id: z.number().nullable(),
  period_start: z.string(), period_end: z.string(), reference_start_year: z.number(), reference_end_year: z.number(),
  mean_rainfall_mm: z.number(), source: z.string(), document_reference: z.string(), data_origin: z.string(), approved_at: z.string().nullable(),
});
const summarySchema = z.object({
  daily: z.array(z.object({ date: z.string(), mean_mm: z.number().nullable(), gauges: z.number(), verified_gauges: z.number() })),
  observed_days: z.number(), missing_days: z.number(), gauges: z.number(), complete_verified_gauges: z.number(),
  coverage_percent: z.number().nullable(), partial_total_mm: z.number().nullable(), verified_complete_total_mm: z.number().nullable(),
  legacy_date_reports: z.number(), unknown_gauge_reports: z.number(), method: z.string(),
});
export const rainfallAnalysisSchema = z.object({
  start: z.string(), end: z.string(), generated_at: z.string(), summary: summarySchema, seven_day: summarySchema,
  anomaly: z.object({ status: z.string(), difference_mm: z.number().nullable(), percent: z.number().nullable(),
    reference: z.object({ source: z.string(), document_reference: z.string(), reference_start_year: z.number(), reference_end_year: z.number() }).nullable() }),
  by_sector: z.array(z.object({ id: z.number().nullable(), name: z.string(), partial_total_mm: z.number().nullable(), missing_days: z.number(), gauges: z.number() })),
  by_scheme: z.array(z.object({ id: z.number().nullable(), name: z.string(), partial_total_mm: z.number().nullable(), missing_days: z.number(), gauges: z.number() })),
});
export const maintenanceHistorySchema = z.object({
  start: z.string(), end: z.string(), as_of: z.string(), method: z.string(),
  assets: z.array(z.object({
    id: z.number(), name: z.string(), scheme_id: z.number().nullable(), scheme: z.string().nullable(), cell_id: z.number().nullable(),
    recorded_downtime_hours: z.number().nullable(), outage_count: z.number(), open_outages: z.number(), recurrent_categories: z.array(z.string()),
    outages: z.array(z.object({ id: z.number(), started_at: z.string(), ended_at: z.string().nullable(), category: z.string(), repair_status: z.string(),
      description: z.string().nullable(), source: z.string() })),
    maintenance: z.array(z.object({ id: z.number(), outage_id: z.number().nullable(), performed_at: z.string(), kind: z.string(), action: z.string().nullable(), source: z.string(), restored: z.boolean() })),
  })),
});
