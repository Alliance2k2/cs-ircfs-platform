# CS-IRCFS Platform Blueprint

This is the consolidated platform vision from the original plan and `cs-ircfs-platform-architecture.docx`.

## The platform's competitive purpose

CS-IRCFS is an outcome-verification and decision-support platform for two flagship irrigation investments in Bugesera:

| Scheme | Area described in the architecture brief | What the platform verifies |
| --- | --- | --- |
| PADAB | Mwesa Valley; 650 ha, two pumping stations, 65.5 km of canals | Crop/yield outcomes, water-infrastructure health, bottlenecks, and community impacts. |
| APEFA Solar Irrigation | Ngeruka and Mareba sectors | Crop/yield outcomes, solar-irrigation performance, rainfall conditions, bottlenecks, and feedback. |

These figures are source requirements from the supplied architecture document. They must be confirmed with scheme owners and authoritative records before they are displayed publicly or used to calibrate a model.

## End-to-end operating model

```text
Community user or designated operator
          │  (free, Kinyarwanda-first USSD/SMS)
          ▼
USSD/SMS gateway and secure webhooks
          ▼
FastAPI validation, identity/role checks, and workflow rules
          ▼
PostgreSQL + PostGIS: reports tied to a cell and irrigation scheme
          ▼
Planner dashboard: KPIs, maps, alerts, trends, case follow-up
          ▼
District action + SMS acknowledgement or targeted advisory
```

## Three functional modules

### 1. Citizen Science and Food Security

- Monthly crop updates: crop variety, planting date, expected harvest, and actual harvest.
- Pest/disease alert: structured keyword or menu selection, location, crop, severity, and optional description.
- Household nutrition survey: short, consent-based questions about food access and feeding frequency.
- Yield benchmarking: compare reported harvest against a scheme-specific, verified yield target.

### 2. Irrigation Resilience and Climate Monitoring

- Operator infrastructure health reports: asset, status, downtime, fault, and bottleneck category.
- Cooperative rain-gauge network: daily rainfall in millimetres, location, and observer.
- Irrigation-condition reports: water availability, canal/pump condition, and infrastructure issue.
- A future scheduling assistant may send SMS advice from defined, locally validated rainfall and water thresholds. It is advisory only until agronomic validation is complete.

### 3. Community Feedback and Service Delivery

- A grievance/feedback channel for input distribution, water pricing, resettlement or downstream impact, and other operational issues.
- Anonymous submissions must be supported without exposing the reporter to planners; abuse-prevention and safeguarding rules are required.
- Case workflow: `open → triaged → assigned → in progress → resolved → closed`.
- Closing the loop: send a case update to the reporter, and only send a cell-wide update when the responsible authority approves it and it contains no personal data.

## Low-bandwidth experience principles

- Kinyarwanda first; short prompts, plain language, and numeric choices.
- Keep a USSD journey within three menu levels where possible.
- Prefer lists and numeric inputs over free text; allow an escape path for unusual incidents.
- Reverse-billed USSD/SMS is a pilot requirement to validate with the selected telecom/gateway partner.
- Community Data Champions (cooperative leaders or trained youth) support onboarding, rain gauges, and infrastructure checklists.
- Return value to reporters: confirmation, relevant local advisory, and resolution updates.

Example opening menu:

```text
Kaze kuri CS-IRCFS. Hitamo:
1. Rapora umusaruro / ikibazo cy'indwara
2. Rapora amazi n'imvura
3. Tanga ikibazo cyangwa igitekerezo
```

## Dashboard experience

The landing page should answer four questions immediately: Are schemes functioning? Are crops performing against expected outcomes? Where are risks concentrated? Which community cases need action?

Core views:

- KPI overview: users, reports, active schemes, unresolved cases, service downtime, and report freshness.
- Scheme comparison: PADAB vs APEFA by area, crop reports, yield performance, irrigation status, and unresolved issues.
- Map: scheme boundaries/assets, pest alerts, rainfall observations, farmer reports, and infrastructure incidents.
- Alert queue: high-severity pest clusters, offline pumps, prolonged downtime, extreme rainfall/drought signals, and overdue grievances.
- Case follow-up: owner, action, deadline, status history, and reporter notification status.

## Responsible analytics rules

- All reported harvest comparisons show the data source, reporting period, number of reports, and missing-data caveat.
- Initial bottleneck flags are decision-support signals, not automatic conclusions; a planner confirms the classification.
- Forecast inputs, agronomic thresholds, historical PADAB/APEFA records, and any health/nutrition scoring must be authorised, versioned, tested, and reviewed by domain experts before use.
- Data from household nutrition or grievances is sensitive: collect only what is necessary, obtain consent, restrict access, and set retention/deletion rules.
