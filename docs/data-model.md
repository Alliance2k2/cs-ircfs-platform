# Data model

The schema is created and changed **only** through Alembic migrations in `backend/migrations/versions/`. The current head is `20261011_17`. Do not run the sample `CREATE TABLE` SQL from the architecture document. The column names differ, as shown at the end of this page.

## Tables

| Table | Key fields | Purpose |
| --- | --- | --- |
| `sectors`, `cells` | name, latitude/longitude, PostGIS `boundary` | Bugesera's 15 sectors and 72 cells |
| `irrigation_schemes` | name, implementing_partner, hectares_developed, **baseline_yield_target_tons**, **baseline_source**, sector_id, is_active | PADAB and APEFA Solar; the outcome-verification baseline |
| `field_users` | **phone_number** (USSD identity), full_name, role, cooperative_name (legacy), **cooperative_id**, **is_data_champion**, **trained_at**, **training_notes**, cell_id, is_active, PostGIS `location` | USSD/SMS callers: farmers, monitors, cooperative leaders. Never web accounts |
| `cooperatives` | name (unique), sector_id, irrigation_scheme_id, **is_pilot**, contact_field_user_id (validated in the API, no FK) | Farmer cooperatives: the Data Champion pilot, participation ranking for Inteko z'Abaturage |
| `advisory_thresholds` | sector_id (unique), **dry_mm**, **wet_mm**, **source**, valid_from | Calibrated per-sector rainfall thresholds; override the `.env` defaults when present |
| `grievance_categories` | code (unique), label_rw, label_en, sort_order, is_active | USSD option 5 menu, edited in Management; `label_en` is what `community_feedback.category` stores |
| `scheme_assets` | scheme_id, name_rw, name_en, asset_type, is_active | USSD option 4 asset inventory, seeded from the PADAB/APEFA lists |
| `bottleneck_baselines` | scheme_id, asset_name, category, finding_date, description, source | Imported AfDB evaluation findings; a category is flagged only above its baseline |
| `citizen_science_logs` | reporter_id, scheme_id, cell_id, crop_type, crop_variety, planting_date, expected_harvest_month, expected_harvest_tons, reported_harvest_tons, pest_or_disease, severity 1–5, notes | Module 1: harvests and pest/disease alerts |
| `irrigation_climate_logs` | reporter_id, scheme_id, cell_id, infrastructure_name, operational_status, bottleneck_category, fault_description, rainfall_mm | Module 2: asset health and rain gauges |
| `community_feedback` | scheme_id, cell_id, category, message, status, assigned_to_field_user_id, due_at, action_taken (`reporter_id` always empty: grievances are anonymous) | Module 3: grievance log |
| `community_feedback_events` | feedback_id, previous/new status, action_taken | Feedback audit trail |
| `incident_cases`, `incident_events` | source_type/source_id (crop or infrastructure), priority, status, assigned_to_account_id, deadline, action, reporter_notified_at | Act Now cases from severe pests and faulty or offline assets |
| `nutrition_surveys` | reporter_id, cell_id, meals_per_day, ate_protein_or_vegetables, food_sufficient, **stunting_risk_score 1–5** | Household Nutrition Tracker |
| `inbound_messages` | phone_number (`withheld` for grievance sessions), channel (ussd/sms), session_id, text, reply, record_type, record_id (empty for grievances) | Every USSD step and SMS received, and what it created |
| `advisory_messages` | phone_number (`withheld` for grievance acknowledgements), message, status (sent/dry_run/failed), **purpose** (auto_reply, advisory, irrigation_schedule, close_loop), cell_id | Every SMS sent to citizens |
| `incentive_rewards` | field_user_id, amount_rwf, reason, status | Airtime micro-bonuses |
| `platform_accounts`, `auth_sessions` | email, role, status; SHA-256 token hash and expiry | Web sign-in for staff (never field users) |
| `account_sectors` | account_id, sector_id | Area-level access: the sectors an account works in (none = whole district) |
| `advice_runs` | week_key (Monday of week, Africa/Kigali), sector_id, recipients, status (sent/partial/dry_run/failed/queued) | Weekly automatic irrigation advice: one row per sector per week, guarantees idempotency |

### Migration integrity (October 2026)

- `20260911_01` is frozen: it lists every baseline table explicitly instead of calling `create_all()` on the current models, so it can no longer change when the models change. `community_feedback_events` moved to `20260929_05`, after `platform_accounts`, which it references (a fresh PostgreSQL failed before).
- `20261011_17` points case assignments (`incident_cases.assigned_to_account_id`, `incident_events.changed_by_account_id`) at `platform_accounts` instead of `field_users`, makes the older `created_at` columns NOT NULL and renames one index.
- `tests/test_migrations.py` checks that a fresh database equals the models, that an existing database keeps its data through the upgrade, and that the newest revision downgrades and upgrades. `scripts/check_schema.py` runs the same comparison against any database; CI runs it on a clean PostGIS server.

### Data origin

`citizen_science_logs`, `irrigation_climate_logs`, `nutrition_surveys`, `community_feedback` and `inbound_messages` carry **`data_origin`** (migration `20261010_16`):

| Value | Written by | Counted as evidence |
| --- | --- | --- |
| `field` | USSD/SMS gateway callbacks and staff API calls (default) | Yes |
| `import` | Historical-data import scripts (reserved) | Yes, labelled as imported |
| `demo` | `scripts/seed_demo_data.py` | Shown, with a "Demonstration data" label (`demo_mode` in the API) |
| `simulator` | The on-screen phone simulator | No: left out of public and executive figures |

## Relationships

```text
sectors → cells → field_users → (citizen_science_logs, irrigation_climate_logs, nutrition_surveys, incentive_rewards)
sectors → cooperatives → field_users (cooperative_id; reports by members roll up into cooperative participation)
sectors → advisory_thresholds (calibrated rainfall thresholds per sector)
irrigation_schemes → (scheme_assets, bottleneck_baselines)
sectors → irrigation_schemes → (citizen_science_logs, irrigation_climate_logs, community_feedback)
cells → community_feedback → community_feedback_events
crop / irrigation report → incident_cases → incident_events
platform_accounts → auth_sessions
platform_accounts ↔ sectors (account_sectors)
```

## Rules

- Severity 4 creates a **high** case and severity 5 a **critical** case.
- An `offline` asset creates a critical case and a `faulty` asset a high case.
- An anonymous grievance stores the cell (so closing-the-loop SMS can reach the community) but never the reporter. The message logs keep the grievance's USSD session and SMS acknowledgement without the phone number.
- Stunting risk: 1 + 2 (one meal a day) or 1 (two meals) + 1 (no protein or vegetables) + 1 (not enough food), capped at 5.
- Rainfall per sector: each gauge's 7-day total, averaged across the gauges in the sector.
- A yield target cannot be saved without its source.
- A calibrated rainfall threshold cannot be saved without its source CSV, and a category is auto-flagged only above its imported historical baseline (window, count and share come from `BOTTLENECK_*` settings).

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
