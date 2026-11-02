# Scientific-evidence implementation report

2 November 2026. Implements the approved Batches 1-4. No commits, pushes, live telecom sends, production deployments or shared-database migrations were performed. Existing user edits to public/sign-in pages remain untouched.

## Changes delivered

- Distinct harvested/cultivated area, original harvest units/quantity, measurement provenance, reference year and reporting date, preserving all legacy columns and records.
- Immutable crop/season/year baseline versions with documented source and separate administrator approval. Draft replacements do not retire approved versions; demonstration targets cannot be approved.
- Shared area-weighted verified-sample yield calculations across evaluation, executive overview and classic scheme performance. kg and t are converted consistently; legacy forecasts/whole-scheme totals cannot establish achievement. Multiple comparable groups are kept separate.
- Demo, simulator and superseded reports excluded from shared scientific-evidence queries, including report-linked case statistics. Operational registries/messages are distinct from scientific outcomes.
- Original-preserving corrections, audit reasons/history, new verification on replacement, preserved observation chronology and follow-up case history, with no repeated alerts. Scoped report creation and correction prevent out-of-area writes.
- Existing Administration, Field reports, Evaluation and classic dashboard updated. Added baseline and correction forms, comparison/source details, export cap notice and correct overview heading hierarchy.
- Evaluation CSV includes each comparable group with its official source, document reference, measured yield, target yield, harvested area and sample size.
- No additional dependencies or ML models introduced.

## Migrations

`20261102_22_scientific_evidence.py` extends crop records and adds `scheme_baselines`. `20261102_23_report_corrections.py` adds supersession metadata. Current head: `20261102_23`. Existing area is never assumed to be harvested area and legacy targets are never promoted to approved official targets.

## Verification

Frontend: TypeScript and ESLint passed; 52 unit tests passed; production build passed. Browser workflows: 20 passed, including five sign-in setup tests and the new synthetic target approval / verified yield / CSV download flow. The browser server uses a guarded disposable SQLite database and disables telecom, weather, scheduler and Mapbox services. Its synthetic field-origin fixtures exist only in that disposable test database; production/demo seed behavior is unchanged.

Backend: 229 passed, including SQLite migration tests; 10 existing dependency/Alembic deprecation warnings. SQLite tests cover fresh schema parity, upgrade/downgrade and preservation of legacy values, plus scientific eligibility, zero yield, unit conversion, baseline version approval, scope, corrections, case history and grouped CSV source completeness.

Unverified locally: PostgreSQL/PostGIS runtime behavior and concurrent row-lock behavior (CI/staging required), Docker image build (Docker command unavailable), live telecom and real feature phones. Build retains existing font-resolution and large Mapbox chunk warnings; browser font requests succeeded. Frontend tests retain an existing nested-button warning in the account table. Backend retains dependency/Alembic deprecation warnings.

## Deployment and field requirements

Before an approved deployment: back up and rehearse migration on staging/PostGIS, apply Alembic upgrade head, rebuild frontend and run schema/smoke checks. Do not downgrade after collecting new evidence without preserving new columns/tables elsewhere. Enter official targets from source documents and approve only after district review. Confirm measurement/verification protocol, approval ownership, native-speaker translations, privacy review and planner/cooperative acceptance. Telecom remains dry-run unless separately authorized.

## Remaining milestones

Climate reference series/anomalies and coverage-aware reporting; maintenance/downtime records; multi-sector scheme coverage; full simulator participant isolation; durable outbound delivery; bounded/protected operational metrics; retention operations and data-readiness assessment for any future ML. These remain pending, not complete. Detailed fields are currently completed through staff correction/API workflows; USSD/SMS menus remain unchanged. Field-report CSV retains a visible 500-record cap. New scientific strings use English fallback until Kinyarwanda field review.

## Files changed by this milestone

- `README.md`
- `backend/app/api/routes/baselines.py`
- `backend/app/api/routes/evaluation.py`
- `backend/app/api/routes/field_reports.py`
- `backend/app/api/routes/reports.py`
- `backend/app/db/models.py`
- `backend/app/main.py`
- `backend/app/schemas/baselines.py`
- `backend/app/schemas/reports.py`
- `backend/app/services/analytics.py`
- `backend/app/services/cooperatives.py`
- `backend/app/services/evaluation.py`
- `backend/app/services/evidence.py`
- `backend/app/services/executive.py`
- `backend/app/services/field_reports.py`
- `backend/app/services/references.py`
- `backend/app/services/reporting.py`
- `backend/app/services/yield_evaluation.py`
- `backend/migrations/versions/20261102_22_scientific_evidence.py`
- `backend/migrations/versions/20261102_23_report_corrections.py`
- `backend/scripts/run_e2e_server.py`
- `backend/tests/test_analytics.py`
- `backend/tests/test_executive.py`
- `backend/tests/test_migrations.py`
- `backend/tests/test_reports.py`
- `backend/tests/test_scientific_evidence.py`
- `backend/tests/test_workspaces.py`
- `dashboard/assets/js/app.js`
- `docs/architecture.md`
- `docs/data-model.md`
- `docs/deployment.md`
- `docs/implementation-2026-11.md`
- `docs/remaining-work.md`
- `docs/roadmap.md`
- `docs/scientific-evaluation.md`
- `docs/security.md`
- `docs/testing.md`
- `docs/workspaces.md`
- `frontend/e2e/09-evaluation.spec.ts`
- `frontend/src/features/admin/AdminPage.tsx`
- `frontend/src/features/admin/BaselineManager.tsx`
- `frontend/src/features/evaluation/EvaluationPage.tsx`
- `frontend/src/features/field-reports/CorrectionForm.tsx`
- `frontend/src/features/field-reports/FieldReportsPage.tsx`
- `frontend/src/features/field-reports/ReportDrawer.tsx`
- `frontend/src/features/overview/OverviewHero.tsx`
- `frontend/src/features/overview/OverviewPage.tsx`
- `frontend/src/features/scientific-evidence.test.tsx`
- `frontend/src/i18n/en.workspaces.ts`
- `frontend/src/services/api/workspaces.ts`
