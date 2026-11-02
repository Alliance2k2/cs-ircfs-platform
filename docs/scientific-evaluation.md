# Scientific evaluation and report corrections

Updated 2 November 2026. This describes the implemented scientific-evidence milestone, not field approval.

## Measurement records

Crop records retain `expected_harvest_tons`, `reported_harvest_tons`, cultivated area, season and dates. They now also carry harvested area, original observed quantity and its unit (`kg` or `t`), observation type (`farmer_estimate`, `measured`, `historical_reference`), data source/method, reference year and optional reporting date. `created_at` is the ingestion timestamp. Sector is derived from the recorded cell.

`reported_harvest_tons` remains the canonical mass field for API compatibility. When an original quantity/unit is supplied the API converts it to tonnes and rejects a conflicting canonical value. Expected quantities remain explicitly in tonnes. Non-finite numbers, negative quantities, invalid date order, future harvest dates and harvested area greater than cultivated area are rejected. Statistical outlier flags remain review hints, not automatic rejection.

Legacy cultivated area is never copied into harvested area. Legacy observations remain readable but do not become measured/verified observations automatically. A mathematical yield returned for a single report is not evidence of verification; verification and provenance are separate fields.

## Official targets

`scheme_baselines` holds immutable target versions: scheme, crop, season, reference year, expected yield, `t/ha` or `kg/ha`, official source, document reference, data origin, verification state, approval date/account and an optional superseded version ID.

- Administrators create unapproved versions in Administration > Scheme baselines > Official crop and season targets.
- Approval is a separate explicit action with its date. Future approval dates and demonstration targets are refused.
- Replacing an approved crop/season/year target requires its current version ID. A draft replacement leaves the current approved version in force.
- Approved rows are retained. There is no edit or delete endpoint. Approval changes are audited, and PostgreSQL serializes approvals per scheme.
- Legacy fields on `irrigation_schemes` remain available for existing clients; they are not converted into approved baselines.
- Multiple crops/seasons/years remain separate. No official values are seeded by this milestone.

APIs: `GET|POST /api/v1/scheme-baselines`; `POST /api/v1/scheme-baselines/{id}/approve`. Creation and approval require administrator access; analysts can read targets.

## Calculation policy

For each current approved target, use only matching scheme, normalized crop name, season and reference year. Observations must be current, field/import origin, verified, measured, sourced, have a valid harvest date, and have paired non-negative observed tonnes and positive harvested hectares. Explicit original units must agree with canonical tonnes. Historical references and farmer estimates are not measured outcomes.

```
observed yield (t/ha) = sum(eligible observed tonnes) / sum(eligible harvested hectares)
achievement (%) = 100 * observed yield / approved target yield (t/ha)
```

This is area-weighted, not the average of farmer percentages. Zero observed production is a valid zero-percent result. Missing area is never treated as zero production. Quantities and areas from different incomplete records cannot be paired.

`services/yield_evaluation.py` is shared by evaluation, executive overview and classic scheme performance. Missing requirements produce `null`, not invented percentages. When multiple comparable groups have results, the headline is null and each crop/season/year comparison is shown separately. Evaluation CSV includes one row per baseline comparison, with observed/target yield, harvested area, sample size and source document. The executive overview uses its selected report window and sector scope; evaluation uses its selected report window; classic scheme performance retains its all-time window.

Results describe the verified measured sample. They are neither whole-scheme production estimates nor causal investment-impact estimates. No ML model is trained or deployed.

## Evidence origins and verification

The shared evidence predicate excludes demo, simulator and superseded field records from report-derived scientific figures. Demonstration reports remain inspectable in Field reports and channel operations. A mixed database notice says demo rows exist but are excluded; it does not relabel real figures as demonstration results. Descriptive counts/harvest totals can include unverified or rejected reports and are not verified outcomes; the yield service excludes them. Registry and message-delivery totals are operational records, not scientific outcomes.

## Corrections

`POST /api/v1/field-reports/{crop|infrastructure}/{id}/corrections` accepts `reason` and a `changes` object using the source report's input fields. Staff can correct only records within their permitted cells and cannot move replacements outside that scope. Reporter references are checked against scoped access too.

A correction creates a new unverified record and links the original with `superseded_by_id`. Original measurements and verification decisions remain intact. The original report's timestamp is retained on the replacement to preserve observation/reporting chronology; audit timestamps record when the correction occurred. Original and replacement have audit entries. A superseded report cannot be verified or corrected again; subsequent corrections target its replacement. Existing incident cases and their history follow the replacement without triggering another alert. Both records remain readable in Field reports; current evidence counts only the replacement.

Quality checks examine duplicate candidates before applying verification/origin display filters. A flagged unusual measurement can still be verified after review.

## Migrations and compatibility

- `20261102_22`: nullable measurement/provenance fields and the baseline version table.
- `20261102_23`: correction/supersession metadata on crop and infrastructure reports.

Upgrade with Alembic through the normal deployment process, after backup and review. No shared database was migrated during development. SQLite tests verify schema/model parity, upgrade/downgrade, and that legacy quantities/areas/targets survive without invented harvested area or approvals. PostgreSQL/PostGIS and production upgrade checks remain required in CI/staging. Downgrades remove new columns/tables and are inappropriate once new evidence has been collected unless it has been preserved elsewhere.

## Field validation still required

Official feasibility-study documents, measurement/verification protocols, staff approval ownership, Kinyarwanda review of new labels, cooperative testing and planner acceptance remain external requirements. New scientific labels use the existing English fallback pending native-speaker review. USSD/SMS collection continues unchanged; detailed measured observations are completed through staff correction/API workflows.

Rainfall references/anomalies, maintenance/downtime records, multi-sector scheme coverage, full simulator participant isolation, delivery outbox/retries and ML dataset readiness are later milestones. None is represented as complete here.
