# Replacement for Section 7 — Implemented Database Schema

**Status:** Implemented schema, checked against the configured PostgreSQL/PostGIS database at Alembic revision `20260914_04` on 14 September 2026. This describes tables and relationships, not verified pilot data or completed outcome analysis.

The platform stores people, administrative locations, irrigation schemes, observations, feedback, and planner actions in related tables. A report can reference a reporter, cell, and scheme; these links are optional in the current API. PostgreSQL stores the relational records, while PostGIS provides `POINT` and `MULTIPOLYGON` columns for mapped locations and boundaries. The database contains two named **reference** schemes, PADAB and APEFA Solar, with no verified area, yield target, or boundaries. It has no sectors, cells, or report records, so the schema's presence must not be described as a completed field dataset.

| Table | Key implemented fields | Purpose |
| --- | --- | --- |
| `sectors` | `id`, `name`, `latitude`, `longitude`, `boundary` | Sector reference records and optional PostGIS boundary. |
| `cells` | `id`, `name`, `sector_id`, `latitude`, `longitude`, `boundary` | Cells belonging to sectors. |
| `irrigation_schemes` | `id`, `name`, `implementing_partner`, `hectares_developed`, `baseline_yield_target_tons`, `baseline_source`, `sector_id`, `latitude`, `longitude`, `boundary`, `is_active` | Scheme identity and optional, sourced baseline fields. PADAB and APEFA Solar currently exist as inactive reference records only. |
| `users` | `id`, `phone_number`, `full_name`, `role`, `cooperative_name`, `cell_id`, `is_active`, `location`, `created_at` | Farmers, monitors, cooperative leaders, officers, planners, and administrators. `location` is a PostGIS point. |
| `farms` | `id`, `farmer_id`, `name`, `boundary`, `created_at` | Optional farm boundaries linked to a farmer. |
| `citizen_science_logs` | `id`, `reporter_id`, `scheme_id`, `cell_id`, `crop_type`, `planting_date`, `expected_harvest_tons`, `reported_harvest_tons`, `pest_or_disease`, `severity`, `notes`, `created_at` | Crop production and pest/disease observations. Expected and reported harvest values are separate, in tons. |
| `irrigation_climate_logs` | `id`, `reporter_id`, `scheme_id`, `cell_id`, `infrastructure_name`, `operational_status`, `bottleneck_category`, `fault_description`, `rainfall_mm`, `created_at` | Irrigation-asset and rainfall observations. Rainfall can be absent; an absent measurement is not recorded as zero. |
| `community_feedback` | `id`, `reporter_id`, `scheme_id`, `cell_id`, `category`, `message`, `status`, `assigned_to_user_id`, `due_at`, `action_taken`, `created_at`, `updated_at` | Feedback cases, including submissions without a reporter ID. A missing reporter ID does not by itself provide a complete anonymous-grievance safeguard. |
| `community_feedback_events` | `id`, `feedback_id`, `previous_status`, `new_status`, `action_taken`, `changed_by_user_id`, `created_at` | History of feedback status changes. |
| `incident_cases` | `id`, `source_type`, `source_id`, `priority`, `status`, `assigned_to_user_id`, `due_at`, `action_taken`, `reporter_notified_at`, timestamps | Planner cases created from high-severity crop reports and faulty/offline irrigation reports. The notification timestamp records a simulation; no SMS is sent. |
| `incident_events` | `id`, `case_id`, `previous_status`, `new_status`, `action_taken`, `changed_by_user_id`, `created_at` | History of incident-case changes. |

## Relationships and data rules

```text
sectors → cells → users
sectors → irrigation_schemes
users → farms
users / cells / irrigation_schemes → citizen_science_logs
users / cells / irrigation_schemes → irrigation_climate_logs
users / cells / irrigation_schemes → community_feedback
community_feedback → community_feedback_events
crop or irrigation report → incident_cases → incident_events
```

Foreign keys link these records; the implemented `cells.sector_id` foreign key does **not** declare the `ON DELETE CASCADE` behavior shown in the old sample SQL. API validation limits roles, selected status and category values, planting dates, rainfall, severity, and numeric ranges. A complete production data-quality and privacy policy still requires field confirmation.

## Differences from the former sample SQL

The former SQL used names such as `sector_id`, `scheme_id`, `user_id`, `log_id`, `sector_name`, `feasibility_yield_target_tons`, `estimated_harvest_tons`, `message_text`, and `is_resolved`. These are **not** the column names in the running database. It also showed `pest_infestation_reported` and `stunting_risk_score`, neither of which exists. The current schema adds PostGIS geometry, actual reported harvest, feedback status history, incident cases, and assignment fields, all absent from the sample. The original block is therefore an early design example and must not be presented as SQL that creates or documents the current database.

The schema should be created and updated through Alembic migrations in `backend/migrations/`, not by running the old `CREATE TABLE` block. This section can replace the old sample in a submission, with the table detail adjusted to the required document length.
