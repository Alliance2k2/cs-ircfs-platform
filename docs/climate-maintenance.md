# Climate evidence and maintenance milestone

Updated 2 November 2026. Implements Batch 5 after validating the previous scientific-evidence migrations on an isolated local PostgreSQL/PostGIS cluster. The existing application, API fields, rule-based advice, and classic pages are preserved.

## Daily and seasonal rainfall evidence

Irrigation/climate reports now accept `observation_date`, `gauge_code`, and `data_source`. The date represents the day of the reported daily gauge measurement; the field protocol must define how gauges are read. USSD/SMS rainfall prompts already ask for today's reading, so those channels now record the Africa/Kigali date and channel source. Old records are not assigned invented observation dates.

`GET /api/v1/climate/rainfall?start=YYYY-MM-DD&end=YYYY-MM-DD` returns daily means, a seven-day summary ending on `end`, selected-period totals, coverage, sector/scheme summaries, missing-data counts, and reference comparability. Select at most one `sector_id` or `scheme_id`. The interval can contain 1-366 past/current days, allowing the planner to specify a seasonal interval without inventing a local season calendar.

- A recorded zero is a measurement; an absent day is null, never zero.
- Gauge identity uses explicit gauge code plus cell, or reporter plus cell. Unidentified readings are counted as unidentified and excluded from gauge totals.
- The latest non-rejected submission for each gauge/day replaces earlier submissions in the analytical view; originals remain stored. An unverified newer reading does not inherit an older verification decision.
- Demonstration, simulator, rejected and superseded observations do not enter these totals.
- Legacy rows can appear descriptively on their Kigali receipt day, labelled as legacy-date records. They cannot support a verified anomaly.
- The partial total sums daily means across the gauges reporting on each day. It is explicitly partial and can combine different reporting subsets. Coverage is relative to gauges observed in this interval, not a complete district rain-gauge inventory.
- A comparable total averages only gauges having a verified, sourced, explicitly dated reading on every day of the selected interval. Missing zero-rain days must be recorded explicitly, not guessed.
- Source measurements are not clamped for these evidence summaries. Existing advice retains its conservative caps and rule thresholds. Advice uses observation dates where present, rejects rejected readings, and falls back to receipt dates only for legacy observations.

The existing monthly activity trend still uses receipt dates and its previous aggregation; the Climate page labels that distinction. Use the new dated evidence panel for reference comparisons. Alignment of all legacy monthly/report/map rainfall calculations remains follow-up work.

## Historical references and anomalies

`rainfall_references` stores one sourced historical mean depth (mm) for a precisely defined comparison date window and either a sector or scheme. It records historical reference years, source/document reference, data origin, and administrator approval date/account. Reference years must precede the comparison interval. No historical rainfall values are seeded, trained, downloaded or inferred.

- `GET /api/v1/climate/references`: accessible references.
- `POST /api/v1/climate/references`: administrator creates an unapproved immutable document record.
- `POST /api/v1/climate/references/{id}/approve`: separate explicit administrator approval. Demonstration references cannot be approved.

Select a reference explicitly; the dashboard fills its comparison dates/location. The API checks exact location and date-window equality, approval, real origin, and complete verified gauge evidence. Otherwise it returns a missing-data/comparability explanation. A sector-restricted view cannot establish a full-scheme anomaly. Reference records are retained; a corrected document is another explicit record, not an overwritten value.

```
difference (mm) = complete verified gauge mean total - approved historical mean total
anomaly (%) = 100 * difference / approved historical mean total
```

A zero historical mean permits an absolute difference but no percentage. Results describe the observed gauge sample, not a complete spatial rainfall estimate or a validated drought prediction. Field staff must verify instrument coverage, reading protocols, historical reference suitability, and local interpretation.

Forecasts with missing daily values or an incomplete seven-day series are unavailable, rather than being summed with nulls silently converted to zero. A genuine seven-day zero forecast remains valid. Advice labels starting values versus sourced historical calibration and explicitly states that agronomist approval is not recorded; no new crop-specific advice is issued.

## Recorded outages and maintenance

`scheme_assets.cell_id` can hold an administrator-verified asset location. Existing assets retain null locations until staff enter verified cells through the asset inventory API/classic Management page. Sector-restricted staff cannot claim an unlocated asset merely by supplying a cell.

`asset_outages` records an inventory asset ID, cell, explicit start, bottleneck category, description, source, origin, reporting account, repair status and optional end. `asset_maintenance` holds immutable inspection, preventive maintenance and repair events with performed time, source and action. All input times require a timezone; dashboard entry/display is in Africa/Kigali.

- `GET /api/v1/irrigation/maintenance?start=...&end=...`: scoped inventory, outage history, maintenance, recorded downtime, open intervals and recurring categories (three or more recorded incidents in the selected period).
- `POST /api/v1/irrigation/outages`: staff records an explicit outage, with overlap prevention serialized per inventory asset on PostgreSQL.
- `POST /api/v1/irrigation/maintenance`: staff records an inspection or repair. A repair with `restored=true` must reference the same asset, cell and origin as an open outage. It closes that interval. Completion cannot precede its start or already-recorded inspections.

Dates cannot be in the future. Duplicate completion and overlapping outages are refused. Demonstration events cannot close real outages. Open intervals are clipped at the requested period end or current time. Overlapping imported intervals are counted once, not added twice. No outage records means unknown downtime, not zero or continuous uptime. There is no invented availability percentage, and a repair does not fabricate a new operational-condition report. No original fault report is converted into an outage interval or repair event.

Maintenance history survives asset deactivation; assets with report/outage/maintenance history cannot be deleted through the inventory API. Writes are audited. Monitors have read-only access and do not receive free-text descriptions/actions; sector-scoped access follows verified asset and event cells. No SMS, case alert or reward is sent by these recording endpoints.

## Database and validation

Migration `20261102_24_climate_maintenance.py` adds nullable observation/source and asset-cell fields plus three new tables. It does not backfill dates, locations, historical means, outages or repairs. Apply it through Alembic after backup and staging review. Current migration head is `20261102_24`.

Local PostgreSQL 18.6 / PostGIS 3.6.2 validation used a newly initialized cluster bound only to 127.0.0.1:55439 and a separate `batch5_validation` database. Previous migrations and the new upgrade/downgrade/upgrade passed schema comparison with zero differences. The cluster was stopped after validation. No configured application database, shared database, credentials, or live infrastructure was modified.

`backend/scripts/check_postgis_workflows.py` accepts only an explicitly supplied `POSTGIS_VALIDATION_URL` on localhost with a database name ending `_validation`; it never uses the configured `DATABASE_URL`. It verifies spatial round trip, row-lock query execution, yield=75%, rainfall anomaly=50%, and downtime=6h with clearly synthetic fixtures in a transaction, then rolls them back. This checks real PostgreSQL types and service queries, not contention under concurrent workers. CI now runs this check on its dedicated PostGIS 16 validation database; local PostgreSQL 18 does not replace CI/staging validation of the production version.

## Remaining requirements

- Obtain approved historical reference documents and actual outage/repair logs; nothing is fabricated to fill these gaps.
- Agree gauge identities, reading protocol, coverage thresholds, seasonal date windows and maintenance recording ownership with field staff.
- Review the new English labels/forms with Kinyarwanda-speaking staff; these additions currently display in English.
- Real feature-phone/provider validation and production rollout remain separate approvals.
- Batch 6 remains pending: explicit multi-sector scheme coverage (including APEFA Mareba), deeper simulator participant isolation, durable outbound delivery, operational metrics and retention improvements.
- Existing font/chunk build warnings and the account-table nested-button warning remain unrelated follow-up work. Docker is unavailable locally; the CI Docker job remains the build check.

## Final test results and changed files

263 backend tests, 56 frontend tests and 21 browser tests passed. TypeScript, ESLint, production frontend build and diff whitespace checks passed. PostgreSQL/PostGIS schema and service checks passed as described above; all synthetic workflow fixtures were rolled back and the disposable server was stopped. Existing font/map-chunk build warnings, account-table nested-button warning and backend dependency/Alembic deprecations remain.

No commits, pushes, deployments, application-database migrations or live messages were performed. Prior user edits to public/sign-in pages remain untouched. The following files were added or modified for Batch 5 (earlier milestone changes remain in the working tree):

- `.github/workflows/ci.yml`
- `backend/app/api/routes/calibration.py`
- `backend/app/api/routes/climate.py`
- `backend/app/api/routes/maintenance.py`
- `backend/app/db/models.py`
- `backend/app/main.py`
- `backend/app/schemas/calibration.py`
- `backend/app/schemas/climate_maintenance.py`
- `backend/app/schemas/reports.py`
- `backend/app/services/advisory.py`
- `backend/app/services/climate.py`
- `backend/app/services/field_reports.py`
- `backend/app/services/forecast.py`
- `backend/app/services/maintenance.py`
- `backend/app/services/rainfall.py`
- `backend/app/services/sms_keywords.py`
- `backend/app/services/ussd.py`
- `backend/migrations/versions/20261102_24_climate_maintenance.py`
- `backend/scripts/check_postgis_workflows.py`
- `backend/tests/test_climate_maintenance.py`
- `backend/tests/test_migrations.py`
- `frontend/e2e/11-climate-maintenance.spec.ts`
- `frontend/src/features/climate-maintenance.test.tsx`
- `frontend/src/features/climate/ClimatePage.tsx`
- `frontend/src/features/climate/RainfallChart.tsx`
- `frontend/src/features/climate/RainfallRecords.tsx`
- `frontend/src/features/field-reports/CorrectionForm.tsx`
- `frontend/src/features/irrigation/IrrigationPage.tsx`
- `frontend/src/features/irrigation/MaintenancePanel.tsx`
- `frontend/src/services/api/climateMaintenance.ts`
- `frontend/src/services/api/workspaces.ts`
- `README.md`
- `docs/architecture.md`
- `docs/climate-maintenance.md`
- `docs/data-model.md`
- `docs/deployment.md`
- `docs/remaining-work.md`
- `docs/roadmap.md`
- `docs/security.md`
- `docs/testing.md`
- `docs/workspaces.md`
