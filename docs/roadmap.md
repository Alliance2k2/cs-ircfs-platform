# Roadmap

> Latest: [9 November validation](engineering-validation-2026-11-09.md). Malformed USSD choice handling and streamed delivery-receipt limits are COMPLETED locally; 339 backend, 61 frontend and 25 browser checks pass. PostGIS migration/schema/restore rehearsals pass. Docker is IMPLEMENTED / NOT VERIFIED; hosted CI/staging, credential rotation, telecom/native review and institutional data remain BLOCKED. Selectable/persisted field USSD language remains PENDING. Earlier counts below are historical.

> Current workstream classifications and verified results: [6 November engineering validation](engineering-validation-2026-11-06.md). Earlier Ready/Complete entries below describe software milestones, not current field or production approval.

> Current implementation and operator instructions: [November completion](platform-completion-2026-11.md). This supersedes earlier remaining-work lists; official data, native review, telecom acceptance and hosted verification still require external inputs.

## Status

| Phase | Deliverable | Status |
| --- | --- | --- |
| Design | Six-option USSD and dashboard workflows | IMPLEMENTED / NOT VERIFIED for native/carrier acceptance; local automated flows pass |
| Development | Backend, dashboard, PostGIS and privacy controls | COMPLETED locally: 325 backend, 61 frontend and 25 browser checks; hosted CI/Docker publication pending |
| Pilot and handover | Three-cooperative pilot and hosted operations | BLOCKED: institutional approval, official inputs, devices, rotated credentials and hosted verification remain required |

## Known limitations

1. **Live telecom delivery.** Outgoing SMS and airtime are recorded with status `dry_run` until Africa's Talking production credentials and a short code are approved. Callback code is implemented and tested with dry-run fixtures; real-provider sandbox acceptance remains unverified.
2. **Scheme baselines.** Official PADAB and APEFA Solar yield targets must be entered, with their sources, in Administration → Scheme baselines (`/app/admin`). Until then, the evaluation lab marks them "Not entered" or "Demonstration value" and does not compute yield achievement.
3. **Threshold calibration.** The irrigation-advice thresholds (10 mm and 40 mm over 7 days) are starting values, to be calibrated against Mwesa Valley and Ngeruka/Mareba rainfall records.
4. **Kinyarwanda review.** Phone screens and interface translations should be reviewed by native speakers before the pilot. The current dashboard inventory has 39 Kinyarwanda drafts and 658 English fallbacks; none is native-approved (see [the review checklist](pilot/kinyarwanda-review-checklist.md)).
5. **Area-level access covers records, not totals.** An account limited to some sectors sees cases, grievances, people, reports and messages from those sectors only. District totals, trends, the monthly report and maps of counts stay district-wide, as they contain no personal data. Records without a cell are visible only to district-wide accounts.
6. **Location of SMS-only users.** USSD callers choose their sector and cell on their first call. A person who only uses SMS has no cell until they name a sector in a message (for example `NYAMATA IMVURA 12`) or an administrator adds it.
7. **Forecast availability.** The Open-Meteo forecast requires internet access from the server. Without it, irrigation advice uses rain-gauge readings alone.

## Next steps

1. Obtain Africa's Talking production credentials and a short code; test on real phones with one cooperative.
2. Enter the official PADAB and APEFA Solar figures, with sources.
3. Train cooperative Data Champions, first with the phone simulator and then on their own phones.
4. Run the three-cooperative pilot and use the monthly report for pilot reporting.
5. Hand over to the district IT unit with the `infrastructure/` stack and this documentation.

## November 2026 evidence milestone

Implemented: sourced/versioned target approval; harvested-area measurements and kg/t conversion; comparable verified sample yields; demo/simulator/superseded report exclusion; immutable report correction workflow; existing React/classic integration. Official target entry, measurement-protocol approval and field validation remain pending. Next technical milestones: climate references and infrastructure maintenance, multi-sector GIS relationships, deeper telecom/participant isolation and durable outbound delivery. No ML training is justified by repository code alone.

## Batch 5: climate and maintenance (November 2026)

Batch 5 climate evidence and explicit maintenance are implemented with local SQLite/PostGIS and browser validation. Next technical priority is Batch 6: scheme coverage relationships, simulator isolation and durable delivery. Official historical references and maintenance records, staff acceptance, Kinyarwanda review and production-version staging rehearsal remain prerequisites for real pilot reporting.

## Batch 6 status

Coverage relationships, participant isolation, transactional ordinary-SMS/airtime dispatch, bounded protected metrics, corrected summaries and local startup safety are implemented. Remaining technical and external acceptance work is explicitly listed in [Batch 6 platform reliability](batch6-platform-reliability.md); the older next-priority statements above are historical. Official data entry and field readiness are not claimed complete.
