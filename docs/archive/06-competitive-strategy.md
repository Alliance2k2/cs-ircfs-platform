# Competitive Strategy — Making CS-IRCFS Stand Out

## The winning idea

CS-IRCFS should not compete as another data-collection app. Its differentiator is a **closed-loop, low-bandwidth outcome-verification system**:

1. A farmer, monitor, or operator reports a real local condition.
2. The platform validates it and connects it to PADAB or APEFA.
3. The planner sees the issue, location, urgency, and pattern.
4. A responsible person records action and resolution.
5. The reporter/community receives a useful response or advisory.
6. The dashboard proves whether the irrigation investment is improving production and livelihoods.

This is valuable to every stakeholder: farmers receive information and follow-up; cooperatives gain visibility; district teams gain prioritised evidence; funders can see measurable outcomes.

## Product pillars

| Pillar | Why it matters | CS-IRCFS implementation |
| --- | --- | --- |
| Offline inclusion | The people closest to the problem may have feature phones and intermittent connectivity. | Kinyarwanda-first USSD/SMS, numeric prompts, short flows, optional Data Champions. |
| Verified outcomes | A report count does not show whether an irrigation investment works. | Link reports, assets, yield targets, and actual harvest to each scheme. |
| Action, not a dashboard only | Trust is lost when people report problems but hear nothing back. | Case owner, deadline, status, action record, and SMS closure notification. |
| Local intelligence | Generic forecasts and categories are less useful locally. | Scheme-specific asset lists, rainfall reports, local pest patterns, transparent thresholds. |
| Trustworthy data | Poor input leads to poor decisions. | Clear validation, deduplication, reporter context, audit trail, and planner review. |
| Scale without redesign | A pilot needs a credible path beyond the first schemes. | A reusable scheme/location data model, API, Docker deployment, and documented onboarding. |

## High-impact features to include in the competition MVP

### 1. The “Act Now” planner queue

Instead of showing only tables, display the most urgent cases first:

- Pump or canal reported offline
- Pest/disease report with high severity
- Repeated rainfall/drought signal in one cell
- Community grievance that has exceeded its response target

Each item needs: location, scheme, report time, severity, owner, status, and a one-click route to the case record. This turns data into a prioritised work list.

**Initial implementation:** available at `GET /api/v1/analytics/act-now`. It currently ranks offline infrastructure as critical, faulty infrastructure and severity-4/5 pest reports as high/critical, and unresolved community feedback as medium. These transparent pilot rules will be reviewed with District Planners before live use.

### 2. Scheme outcome scorecard

Create one clear page for PADAB and one for APEFA. Include:

- active farmers/reporters and report freshness
- crop area and reported harvest compared with a verified target
- infrastructure uptime/downtime and unresolved technical cases
- rainfall trend and pest-risk reports
- open/resolved grievances and median resolution time

Show the reporting coverage and missing-data warning beside every result. A score is credible only when it explains its evidence.

### 3. Closed-loop case management

Every irrigation failure, pest alert, or grievance should receive a unique case ID and follow this path:

```text
new report → triage → assigned owner → action recorded → resolved → reporter notified → verified/closed
```

The platform should record status history, not merely the latest status. Add an overdue indicator using an agreed service-level target (for example, 48 hours for a critical pump issue); do not activate targets until Bugesera confirms them.

### 4. “You give data, you get value” replies

After submission, return a simple confirmation and, when appropriate, a locally approved advisory. Examples: report reference number, next market/extension clinic date, pest-scouting instruction, or irrigation notice. Advice must be approved by agricultural officers; do not generate agricultural instructions without review.

### 5. Community Data Champion toolkit

Provide trained cooperative leaders or youth monitors with a lightweight workflow:

- weekly data-quality checklist
- rain-gauge recording card
- pump/canal incident checklist
- onboarding/help script in Kinyarwanda
- monthly cooperative scorecard

This makes adoption an organised community activity rather than an individual-phone experiment.

### 6. Map plus evidence, not map decoration

Use the map to answer a decision question: *where should the district act next?* Map assets, report clusters, rainfall points, pest alerts, and unresolved cases. Every map point must open the underlying report and its case history.

## Features for the next version

| Feature | Value | Prerequisite |
| --- | --- | --- |
| SMS keyword parser | Faster reporting on any feature phone | Tested Kinyarwanda keywords and gateway integration. |
| Rainfall/drought alert | Early response to water stress | Sufficient local observations and agronomist-approved thresholds. |
| Pest heatmap | Faster extension support | Controlled pest vocabulary, severity rules, and enough reports. |
| Yield-performance model | Verifies investment outcomes | Official baseline/target yields and complete harvest reports. |
| Irrigation scheduling advice | Helps conserve water | Local weather data, validated rules, and officer approval. |
| Public accountability summary | Builds trust | Privacy review and district approval for aggregate publication. |

## What judges should see in a live demonstration

1. A farmer submits an irrigation problem through a simulated Kinyarwanda USSD menu.
2. The report appears immediately in the planner's **Act Now** queue and on the map.
3. A planner assigns it, records a repair action, and closes the case.
4. The farmer receives a simulated SMS resolution notice.
5. The PADAB/APEFA scorecard updates the operational and accountability indicators.

That short story demonstrates inclusion, real-time operations, accountability, GIS, analytics, and scalability in one flow.

## Success measures for the competition pilot

- Reporting adoption: active reporters / registered reporters.
- Completion: successfully submitted USSD/SMS reports / initiated sessions.
- Data quality: valid reports / total reports; duplicate and error rate.
- Responsiveness: median time from report to triage, action, and closure.
- Infrastructure reliability: downtime reports, resolved incidents, and time offline.
- Outcome evidence: reported harvest compared to verified scheme target, with coverage shown.
- Trust: percentage of reporters receiving a response and satisfaction feedback.

## Decisions we can build around now

| Decision | Safe working assumption |
| --- | --- |
| Pilot focus | Start with PADAB and APEFA, then add schemes through configuration. |
| User language | Kinyarwanda-first; English dashboard labels can be added for institutional users. |
| Channels | Build a USSD/SMS simulator first; attach a live gateway later. |
| Data source | Use clearly labelled sample data until official scheme records are verified. |
| Analytics | Begin with transparent counts, trends, and rule-based alerts—not opaque AI. |
| Privacy | Minimise personal data; anonymous grievances are protected and not shown publicly. |

## Information that must be confirmed before production

- Telecom/gateway partner, shortcode, pricing, and reverse-billing feasibility.
- Approved USSD/SMS wording and local consent notice.
- Pilot cooperatives, Data Champions, scheme assets, locations, and district case owners.
- Official PADAB/APEFA target data and permitted use of historical documents.
- Service-level response targets and escalation procedures.
- Agricultural advice content, forecast data source, and validation owner.
- Data-retention, access, and incident-response policy.
