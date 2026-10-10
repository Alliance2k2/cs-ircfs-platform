import { z } from "zod";

/** Response schemas for the workspace APIs (backend/app/api/routes). Keep in step with the backend. */
const ts = z.string();
const status = z.enum(["open", "triaged", "assigned", "in_progress", "resolved", "closed"]);
export type CaseStatus = z.infer<typeof status>;
export const STATUSES = status.options;

export const actNowItemSchema = z.object({
  item_type: z.string(),
  item_id: z.number(),
  priority: z.string(),
  title: z.string(),
  status: z.string(),
  scheme_id: z.number().nullable(),
  cell_id: z.number().nullable(),
  created_at: ts,
  assigned_to_account_id: z.number().nullable().optional(),
  assigned_to_field_user_id: z.number().nullable().optional(),
  due_at: ts.nullable().optional(),
  details: z.string().nullable().optional(),
});
export type ActNowItem = z.infer<typeof actNowItemSchema>;

export const caseSchema = z.object({
  id: z.number(),
  source_type: z.string(),
  source_id: z.number(),
  priority: z.string(),
  status,
  assigned_to_account_id: z.number().nullable(),
  due_at: ts.nullable(),
  action_taken: z.string().nullable(),
  reporter_notified_at: ts.nullable(),
  created_at: ts,
});
export type IncidentCase = z.infer<typeof caseSchema>;

export const eventSchema = z.object({
  id: z.number(),
  previous_status: status.nullable(),
  new_status: status,
  action_taken: z.string().nullable(),
  changed_by_account_id: z.number().nullable(),
  created_at: ts,
});
export type StatusEvent = z.infer<typeof eventSchema>;

export const feedbackSchema = z.object({
  id: z.number(),
  scheme_id: z.number().nullable(),
  cell_id: z.number().nullable(),
  category: z.string(),
  message: z.string(),
  status,
  assigned_to_field_user_id: z.number().nullable(),
  due_at: ts.nullable(),
  action_taken: z.string().nullable(),
  created_at: ts,
  updated_at: ts,
});
export type Feedback = z.infer<typeof feedbackSchema>;

export const notificationSchema = z.object({ recipients: z.number(), preview: z.boolean().optional(), message: z.string().optional() }).passthrough();

export const assigneeSchema = z.object({ id: z.number(), full_name: z.string(), role: z.string(), area: z.string() });
export type Assignee = z.infer<typeof assigneeSchema>;

export const fieldReportSchema = z.object({
  id: z.number(),
  source: z.enum(["crop", "infrastructure"]),
  kind: z.enum(["harvest", "pest", "rain", "asset"]),
  title: z.string(),
  crop: z.string().nullable(),
  pest: z.string().nullable(),
  severity: z.number().nullable(),
  expected_tons: z.number().nullable(),
  reported_tons: z.number().nullable(),
  rainfall_mm: z.number().nullable(),
  asset: z.string().nullable(),
  condition: z.string().nullable(),
  bottleneck: z.string().nullable(),
  scheme_id: z.number().nullable(),
  scheme: z.string().nullable(),
  cell_id: z.number().nullable(),
  cell: z.string().nullable(),
  sector_id: z.number().nullable(),
  sector: z.string().nullable(),
  reporter_id: z.number().nullable(),
  reporter: z.string().nullable(),
  reporter_role: z.string().nullable(),
  data_origin: z.string(),
  verification_status: z.enum(["unverified", "verified", "rejected"]),
  verified_at: ts.nullable(),
  verification_note: z.string().nullable(),
  flags: z.array(z.string()),
  created_at: ts,
});
export type FieldReport = z.infer<typeof fieldReportSchema>;

export const fieldReportListSchema = z.object({ reports: z.array(fieldReportSchema), personal_data: z.boolean(), truncated: z.boolean() });

export const fieldReportDetailSchema = fieldReportSchema.extend({
  notes: z.string().nullable(),
  latitude: z.number().nullable(),
  longitude: z.number().nullable(),
  case: z.object({ id: z.number(), priority: z.string(), status: z.string() }).nullable(),
  verification_history: z.array(z.object({ action: z.string(), by: z.string(), detail: z.string().nullable(), at: ts })),
});
export type FieldReportDetail = z.infer<typeof fieldReportDetailSchema>;

const openCase = z.object({ id: z.number(), priority: z.string(), status: z.string() });
export const assetRowSchema = z.object({
  asset: z.string(),
  scheme_id: z.number().nullable(),
  scheme: z.string().nullable(),
  status: z.string(),
  down: z.boolean(),
  bottleneck: z.string().nullable(),
  description: z.string().nullable(),
  sector: z.string().nullable(),
  reports: z.number(),
  fault_reports: z.number(),
  open_cases: z.array(openCase),
  reported_at: ts,
});
export type AssetRow = z.infer<typeof assetRowSchema>;
export const assetsSchema = z.object({
  assets: z.array(assetRowSchema),
  never_reported: z.array(z.object({ asset: z.string(), scheme: z.string().nullable(), asset_type: z.string().nullable() })),
  counts: z.object({ assets: z.number(), down: z.number(), open_cases: z.number() }),
});
export const assetHistorySchema = z.object({
  asset: z.string(),
  scheme: z.string().nullable(),
  history: z.array(z.object({
    id: z.number(), condition: z.string().nullable(), bottleneck: z.string().nullable(), description: z.string().nullable(),
    sector: z.string().nullable(), data_origin: z.string(), verification_status: z.string(), created_at: ts, case: openCase.nullable(),
  })),
});

export const scheduleRowSchema = z.object({
  sector_id: z.number(),
  sector: z.string(),
  level: z.string(),
  rainfall_mm_7d: z.number().nullable(),
  forecast_mm_7d: z.number().nullable(),
  readings: z.number(),
  message_en: z.string(),
  message_rw: z.string(),
  threshold_dry_mm: z.number(),
  threshold_wet_mm: z.number(),
  threshold_source: z.string().nullable(),
});
export type ScheduleRow = z.infer<typeof scheduleRowSchema>;
export const weeklyAdviceSchema = z.object({
  enabled: z.boolean(), weekday: z.string(), time: z.string(), week_key: z.string(),
  last_run: z.object({ week_key: z.string(), sectors: z.number(), recipients: z.number() }).nullable(),
});
export const broadcastSchema = z.object({
  preview: z.boolean(),
  sectors: z.array(z.object({ sector: z.string(), level: z.string(), recipients: z.number() })),
  total_recipients: z.number(),
});

export const trendsSchema = z.object({
  months: z.array(z.object({
    month: z.string(), label: z.string(), reports: z.number(), severe_pests: z.number(), rain_readings: z.number(), asset_faults: z.number(),
    grievances: z.number(), cases_opened: z.number(), cases_resolved: z.number(), expected_tons: z.number(), reported_tons: z.number(),
    plantings: z.number(), households: z.number(), average_risk: z.number().nullable(), rainfall_mm: z.number().nullable(),
  })),
});
export type TrendMonth = z.infer<typeof trendsSchema>["months"][number];

export const nutritionSchema = z.object({
  households: z.number(),
  average_risk: z.number().nullable(),
  high_risk_households: z.number(),
  one_meal_households: z.number(),
  food_insufficient: z.number(),
  min_households_per_group: z.number(),
  by_cell: z.array(z.object({
    cell_id: z.number().nullable(), cell: z.string(), households: z.number(), suppressed: z.boolean(),
    average_risk: z.number().nullable(), high_risk: z.number().nullable(), latitude: z.number().nullable(), longitude: z.number().nullable(),
  })),
});

const requirement = z.object({ item: z.string(), met: z.boolean(), note: z.string().nullable() });
export const evaluationSchema = z.object({
  generated_at: ts,
  period_days: z.number(),
  method: z.string(),
  questions: z.array(z.object({ id: z.number(), question: z.string(), section: z.string() })),
  schemes: z.array(z.object({
    scheme_id: z.number(), name: z.string(), implementing_partner: z.string().nullable(), hectares_developed: z.number().nullable(),
    documentation: z.object({ target_tons: z.number().nullable(), target_source: z.string().nullable(), state: z.enum(["documented", "demo", "missing"]) }),
    outcomes: z.object({
      harvest_reports: z.number(), reported_tons: z.number(), expected_tons: z.number(), pest_alerts: z.number(), severe_pest_alerts: z.number(),
      crops: z.array(z.object({ crop: z.string(), reports: z.number(), with_reported_tons: z.number(), reported_tons: z.number(), expected_tons: z.number() })),
      yield_achievement: z.object({ value: z.number().nullable(), computable: z.boolean(), formula: z.string(), requirements: z.array(requirement) }),
    }),
    bottlenecks: z.object({
      window_days: z.number().nullable(), by_category: z.record(z.number()), flagged: z.array(z.string()), above_baseline: z.array(z.string()),
      assets_reported: z.number(), assets_down: z.number(), fault_reports: z.number(),
    }),
    feedback: z.object({ grievances: z.number(), open: z.number(), resolved: z.number(), by_category: z.record(z.number()) }),
    downstream: z.object({ grievances: z.number(), open: z.number() }),
    evidence: z.object({
      reports: z.number(), located_percent: z.number().nullable(), verified_percent: z.number().nullable(), rejected: z.number(),
      demo_percent: z.number().nullable(), months_with_reports: z.number(), months_in_period: z.number(), last_report_at: ts.nullable(),
    }),
  })),
});
export type Evaluation = z.infer<typeof evaluationSchema>;

export const participationSchema = z.object({
  id: z.number(), name: z.string(), sector_id: z.number().nullable(), is_pilot: z.boolean(), members: z.number(), data_champions: z.number(),
  reports_30d: z.number(), active_reporters_30d: z.number(), last_report_at: ts.nullable(),
});
export const trainingSchema = z.object({
  trained_monitors: z.number(), target: z.number(), percent: z.number(), monitors_total: z.number(), data_champions: z.number(),
  pilot_cooperatives: z.number(), pilot_target: z.number(),
});

export const activitySchema = z.object({
  inbound: z.array(z.object({ id: z.number(), phone_number: z.string().nullable(), channel: z.string(), text: z.string().nullable(), reply: z.string().nullable(),
                               record_type: z.string().nullable(), data_origin: z.string(), created_at: ts })),
  outbound: z.array(z.object({ id: z.number(), phone_number: z.string().nullable(), message: z.string().nullable(), status: z.string(), purpose: z.string().nullable(), created_at: ts })),
  rewards: z.array(z.object({ id: z.number(), phone_number: z.string().nullable(), amount_rwf: z.number(), reason: z.string(), status: z.string(), created_at: ts })),
  personal_data: z.boolean(),
  service_code: z.string(),
  sms_shortcode: z.string(),
});

export const monthlySchema = z.object({
  month: z.string(), label: z.string(), previous_month: z.string(), generated_at: ts,
  figures: z.record(z.object({ value: z.number(), previous: z.number(), change_percent: z.number().nullable() })),
  sectors_reporting: z.number(), sectors_total: z.number(),
  sector_activity: z.array(z.object({ sector: z.string(), reports: z.number() })),
  schemes: z.array(z.object({ name: z.string(), crop_reports: z.number(), expected_tons: z.number(), reported_tons: z.number(),
                              severe_pest_reports: z.number(), asset_faults: z.number(), grievances: z.number() })),
  cases: z.object({ opened: z.number(), resolved_in_month: z.number(), open_at_month_end: z.number(), median_days_to_resolve: z.number().nullable() }),
});

export const accountRowSchema = z.object({
  id: z.number(), email: z.string(), full_name: z.string(), role: z.string(), status: z.string(), created_at: ts, sector_ids: z.array(z.number()),
});
export type AccountRow = z.infer<typeof accountRowSchema>;
export const auditSchema = z.object({
  id: z.number(), actor: z.string(), action: z.string(), entity: z.string(), entity_id: z.number().nullable(),
  detail: z.record(z.unknown()), created_at: ts,
});
export type AuditRow = z.infer<typeof auditSchema>;
export const schemeFullSchema = z.object({
  id: z.number(), name: z.string(), implementing_partner: z.string().nullable(), hectares_developed: z.number().nullable(),
  baseline_yield_target_tons: z.number().nullable(), baseline_source: z.string().nullable(), is_active: z.boolean(),
});
export const cellSchema = z.object({ id: z.number(), name: z.string(), sector_id: z.number() });
export const fieldUserSchema = z.object({
  id: z.number(), full_name: z.string().nullable(), role: z.string(), cooperative_name: z.string().nullable(), cell_id: z.number().nullable(), is_active: z.boolean(),
});
export type FieldUserRow = z.infer<typeof fieldUserSchema>;
