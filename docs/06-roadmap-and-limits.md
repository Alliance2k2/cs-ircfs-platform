# Roadmap and current limits

## Status against the six-month plan (Section 5)

| Phase | Deliverable | Status |
| --- | --- | --- |
| Months 1–2 Design | USSD wireframes, Kinyarwanda menu paths | **Done in software:** 6-option menu, ≤3 levels, numeric. Field validation with cooperatives is still needed |
| Months 3–4 Development | Backend, Africa's Talking integration, PostgreSQL, Leaflet dashboard | **Done.** Gateway runs in dry-run until credentials are issued |
| Months 5–6 Pilot & handover | Pilot with 3 cooperatives, Docker, training and handover docs | **Ready to start:** Docker Compose, operations guide, demo script. The pilot itself is fieldwork |

## Known limits (be open about these)

1. **Live telecom delivery.** SMS and airtime are recorded with status `dry_run` until Africa's Talking credentials and a short code are approved. The USSD and SMS callbacks are complete.
2. **Real baselines.** PADAB and APEFA yield targets are not in the system. The demo uses labelled placeholder values. Scheme performance shows "Target needed" until the official figures are entered.
3. **Calibration.** Irrigation-advice thresholds (10 mm / 40 mm per 7 days) are starting values. They must be calibrated from Mwesa Valley and Ngeruka/Mareba history (Section 9.2).
4. **Kinyarwanda review.** Every phone screen and the dashboard translations need review by native speakers in the field team.
5. **Area-level access.** Roles control what someone can do, but not which sectors they can see. Add this if officers should be limited to their own area.
6. **Caller location.** A first-time caller is registered without a cell. Until a planner adds it, their reports are not mapped. A later improvement: a one-time "choose your sector" USSD step.
7. **Duplicate protection.** A repeated identical SMS creates a second report. Add de-duplication by provider message ID before scale-up.

## Suggested next steps

1. Apply for an Africa's Talking sandbox account. Point it at a tunnel (`ngrok`) and test on real phones with one cooperative.
2. Enter the official PADAB and APEFA figures, with sources.
3. Train 3 cooperative Data Champions with the phone simulator, then on their own phones.
4. Run the 3-cooperative pilot. Export monthly CSVs from Platform Management for the pilot report.
5. Hand over with `infrastructure/` and these docs.
