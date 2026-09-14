# Delivery Roadmap and Backlog

## Phase 0 — Discovery and field design (months 1–2)

Confirm Kinyarwanda wording, USSD/SMS provider and shortcode/sandbox, supported report types, administrative boundaries, PADAB/APEFA asset and baseline data, reporting units, privacy/consent, planner workflow, and pilot cooperatives in Bugesera. Run field surveys in the priority sectors, including Nyamata and Ruhuha where applicable.

**Done when:** inception report, signed-off field forms, USSD wireframes and Kinyarwanda scripts, data dictionary, role permissions, and pilot plan exist.

## Phase 1 — Technical foundation (months 3–4)

Create the FastAPI project, PostgreSQL/PostGIS schema, authentication, roles, migrations, seed geography, audit logging, Docker setup, and automated tests.

**Done when:** authorised users can create/read validated records through documented APIs.

## Phase 2 — Community reporting (months 3–4)

Implement the three USSD paths, SMS parser, idempotent gateway webhooks, confirmation messages, and report storage.

**Done when:** a farmer/monitor can submit each report type using a basic phone and it appears correctly in the database.

## Phase 3 — District dashboard and GIS (months 3–4)

Build KPIs, report lists/detail, filters, feedback follow-up, PADAB/APEFA views, and Leaflet map layers.

**Done when:** a planner can find, filter, map, and follow up a report without database access.

## Phase 4 — Pilot, analytics, and handover (months 5–6)

Add harvest performance, bottleneck classification, trends, and exportable planning insights. Keep irrigation recommendations explicitly experimental until validated.

**Done when:** analytics use validated data, document their calculation, and show interpretable results.

## Phase 5 — Test, improve, and deploy (months 5–6)

Test registration, USSD, SMS, API, storage, validation, dashboard, maps, feedback, and security. Conduct the Bugesera pilot; review the defined indicators; improve and retest. Deploy via Docker with backups, monitoring, documentation, and training.

**End-to-end acceptance test:** a community report flows from USSD/SMS → API → database → dashboard/map → responsible planner follow-up and, where appropriate, a reporter notification.

## Six-month required outputs

| Month | Output |
| --- | --- |
| 1 | Inception report: work plan, field findings, and USSD wireframes. |
| 3 | Mid-term progress note with field-test results and refinements. |
| 4 | Functional USSD/SMS prototype, database, and dashboard. |
| 5 | Pilot report and refined platform based on three Bugesera cooperatives. |
| 6 | Final report, Docker deployment package, training materials, and district handover documentation. |

## Prioritised MVP

| Priority | Deliverable |
| --- | --- |
| Must | Roles/users, locations, crop reports, irrigation/rainfall reports, feedback, validation, planner dashboard, map, and follow-up. |
| Should | SMS parsing, dashboard filters/exports, KPI trends, audit trail, Docker, backups, monitoring. |
| Later | Harvest-performance analytics, bottleneck classification, forecast-based irrigation recommendations. |
