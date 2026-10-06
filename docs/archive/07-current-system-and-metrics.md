# Current system, evidence, and boundaries

## Operating journey

```text
Demonstration form or API report
    → validation and storage
    → high-severity crop or faulty/offline irrigation case
    → Act Now queue
    → planner status, owner, deadline, and action
    → resolution and immutable case event
    → simulated response timestamp (no SMS sent)
```

Community feedback has its own status and history endpoints. USSD/SMS provider webhooks, individual sign-in, verified scheme targets, and live outgoing notifications are not implemented.

## Live dashboard metric definitions

| Metric | Current calculation | Important limit |
| --- | --- | --- |
| Registered farmers | Count of users with the farmer role | Includes inactive users; account for activity in a future coverage metric. |
| Total reports | Crop reports plus irrigation/climate reports | Feedback cases are excluded. |
| Active schemes | Schemes with `is_active=true` | Scheme records require official verification. |
| Open complaints | Feedback whose status is neither resolved nor closed | No agreed response-time target yet. |
| Faulty/offline assets | Number of irrigation reports marked faulty or offline | Counts reports, not distinct physical assets. |
| Act Now | Open incident cases and unresolved feedback | Priorities are transparent pilot rules, not validated service targets. |

Dashboard figures shown before connecting the API are labelled demonstration data. Outcome verification and response-health panels are placeholders until field records and metric definitions are approved.

## Next production gates

1. Replace role-wide API keys with individual authentication and record-level area/ownership checks.
2. Confirm official PADAB/APEFA schemes, assets, boundaries, baselines, and reporting units.
3. Connect approved USSD/SMS provider webhooks with idempotent submission, consent, and delivery tracking.
4. Define retention, safeguarding, backup, monitoring, and incident-response procedures.
5. Run migrations and integration tests against the actual PostgreSQL/PostGIS deployment configuration.
