# Data model

The schema is created and changed **only** through Alembic migrations in `backend/migrations/versions/`. The current head is `20261006_08`. Do not run the sample `CREATE TABLE` SQL from the architecture document. The column names differ, as shown at the end of this page.

## Tables

| Table | Key fields | Purpose |
| --- | --- | --- |
| `sectors`, `cells` | name, latitude/longitude, PostGIS `boundary` | Bugesera's 15 sectors and 72 cells |
| `irrigation_schemes` | name, implementing_partner, hectares_developed, **baseline_yield_target_tons**, **baseline_source**, sector_id, is_active | PADAB and APEFA Solar; the outcome-verification baseline |
| `users` | **phone_number** (USSD identity), full_name, role, cooperative_name, cell_id, is_active, PostGIS `location` | Farmers, monitors, cooperative leaders, officers, planners |
| `citizen_science_logs` | reporter_id, scheme_id, cell_id, crop_type, planting_date, expected_harvest_tons, reported_harvest_tons, pest_or_disease, severity 1–5, notes | Module 1: harvests and pest/disease alerts |
| `irrigation_climate_logs` | reporter_id, scheme_id, cell_id, infrastructure_name, operational_status, bottleneck_category, fault_description, rainfall_mm | Module 2: asset health and rain gauges |
| `community_feedback` | scheme_id, cell_id, category, message, status, assigned_to_user_id, due_at, action_taken (`reporter_id` empty for anonymous grievances) | Module 3: grievance log |
| `community_feedback_events` | feedback_id, previous/new status, action_taken | Feedback audit trail |
| `incident_cases`, `incident_events` | source report, priority, status, owner, deadline, action, reporter_notified_at | Act Now cases from severe pests and faulty or offline assets |
| `nutrition_surveys` | reporter_id, cell_id, meals_per_day, ate_protein_or_vegetables, food_sufficient, **stunting_risk_score 1–5** | Household Nutrition Tracker |
| `inbound_messages` | phone_number, channel (ussd/sms), session_id, text, reply, record_type, record_id | Every USSD step and SMS received, and what it created |
| `advisory_messages` | phone_number, message, status (sent/dry_run/failed), **purpose** (auto_reply, advisory, irrigation_schedule, close_loop), cell_id | Every SMS sent to citizens |
| `incentive_rewards` | user_id, amount_rwf, reason, status | Airtime micro-bonuses |
| `platform_accounts`, `auth_sessions` | email, role, status; SHA-256 token hash and expiry | Web sign-in for staff |
| `farms` | farmer_id, PostGIS boundary | Optional farm plots |

## Relationships

```text
sectors → cells → users → (citizen_science_logs, irrigation_climate_logs, nutrition_surveys, incentive_rewards)
sectors → irrigation_schemes → (citizen_science_logs, irrigation_climate_logs, community_feedback)
cells → community_feedback → community_feedback_events
crop / irrigation report → incident_cases → incident_events
platform_accounts → auth_sessions
```

## Rules

- Severity 4 creates a **high** case and severity 5 a **critical** case.
- An `offline` asset creates a critical case and a `faulty` asset a high case.
- An anonymous grievance stores the cell (so closing-the-loop SMS can reach the community) but never the reporter.
- Stunting risk: 1 + 2 (one meal a day) or 1 (two meals) + 1 (no protein or vegetables) + 1 (not enough food), capped at 5.
- Rainfall per sector: each gauge's 7-day total, averaged across the gauges in the sector.
- A yield target cannot be saved without its source.

## Names compared with the architecture's sample SQL

| Sample SQL | Implemented |
| --- | --- |
| `sector_id`, `user_id`, `log_id` (primary keys) | `id` |
| `sector_name`, `scheme_name` | `name` |
| `feasibility_yield_target_tons` | `baseline_yield_target_tons` + `baseline_source` |
| `estimated_harvest_tons` | `expected_harvest_tons` (+ `reported_harvest_tons`) |
| `pest_infestation_reported`, `pest_type` | `pest_or_disease` + `severity` |
| `stunting_risk_score` on crop logs | `nutrition_surveys.stunting_risk_score` |
| `status` (irrigation) | `operational_status` |
| `message_text`, `is_resolved`, `resolved_at` | `message`, `status` workflow + `community_feedback_events` |
