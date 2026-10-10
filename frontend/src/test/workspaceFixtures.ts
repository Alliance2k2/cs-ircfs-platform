/** Small API answers for the workspace tests, shaped like the backend's. */
export const REFERENCE = {
  sectors: [{ id: 1, name: "Ngeruka" }, { id: 2, name: "Mareba" }],
  "irrigation-schemes": [{ id: 1, name: "PADAB", is_active: true, implementing_partner: "PADAB", hectares_developed: null, baseline_yield_target_tons: null, baseline_source: null }],
  cells: [{ id: 40, name: "Rutonde", sector_id: 1 }],
};

export const actNow = [
  { item_type: "infrastructure", item_id: 5, priority: "critical", title: "PADAB Pumping Station 1 is offline", status: "open", scheme_id: 1, cell_id: 40,
    created_at: "2026-10-09T08:00:00Z", assigned_to_account_id: null, assigned_to_field_user_id: null, due_at: null, details: "Motor overheats." },
  { item_type: "community_feedback", item_id: 3, priority: "medium", title: "Water Pricing", status: "open", scheme_id: 1, cell_id: 40,
    created_at: "2026-10-08T08:00:00Z", assigned_to_account_id: null, assigned_to_field_user_id: null, due_at: null, details: "Fees are too high." },
];

export const incidentCase = {
  id: 5, source_type: "infrastructure", source_id: 9, priority: "critical", status: "open", assigned_to_account_id: null,
  due_at: null, action_taken: null, reporter_notified_at: null, created_at: "2026-10-09T08:00:00Z",
};

export function fieldReport(overrides: Record<string, unknown> = {}) {
  return {
    id: 11, source: "crop", kind: "pest", title: "Fall armyworm on Maize", crop: "Maize", pest: "Fall armyworm", severity: 4,
    expected_tons: null, reported_tons: null, rainfall_mm: null, asset: null, condition: null, bottleneck: null,
    scheme_id: 1, scheme: "PADAB", cell_id: 40, cell: "Rutonde", sector_id: 1, sector: "Ngeruka",
    reporter_id: 2, reporter: "+250788000001", reporter_role: "farmer", data_origin: "field",
    verification_status: "unverified", verified_at: null, verification_note: null, flags: ["possible_duplicate"],
    created_at: "2026-10-09T08:00:00Z", ...overrides,
  };
}

export const reportDetail = {
  ...fieldReport(), notes: "Leaves eaten", latitude: -2.3, longitude: 30.1, case: { id: 5, priority: "high", status: "open" }, verification_history: [],
};
