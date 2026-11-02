# November 2026: coverage, training isolation and delivery reliability

This milestone extends the existing platform. It does not activate telecom providers or certify field readiness. The public landing page remains at `/`; the complete dashboard remains at `/app/`.

## Implemented

- `scheme_sector_coverage` represents multiple sectors per scheme. The API exposes `coverage_sector_ids`; Administration → Scheme baselines edits the complete service area. Existing single-sector assignments are preserved by migration. Unknown/duplicate sectors and inconsistent primary-sector input are rejected before changes are saved. Only active schemes participate in automatic assignment; overlapping matches leave the scheme unassigned rather than choosing arbitrarily. Climate-reference visibility recognizes additional coverage sectors.
- The simulator now creates a separate, staff-specific profile with a non-dialable `sim-…` identity. Real caller consent, opt-out and location are never loaded into that profile or changed by training. Training profiles are inactive by default and excluded from farmer counts, registries, maps, cooperative participation/training and broadcast recipients. API edits and real report references cannot activate/use them. Training and gateway idempotency keys are separated by origin; simulator session IDs are also staff-specific. All simulator provider calls remain dry-run.
- Ordinary live SMS and airtime rewards are queued in their existing database tables with the business transaction. Reward creation no longer commits a partially processed incoming report. The dispatcher claims one committed row atomically before a provider request. Provider failures/timeouts and abandoned claims become `unknown` and are not automatically resent. `sent` means provider acceptance; handset delivery is not confirmed.
- Broadcast dispatch rechecks opt-out/active status. Simulated/non-dialable recipients cannot be dispatched. Dry-run messages/rewards never enter the live queue.
- Metrics require an administrator. Route templates replace raw request paths; a hard bound prevents unbounded route-label growth.
- Farmer summaries now show actual schemes, complaints and current asset conditions. Repeated old faults no longer inflate the summary after a repair. Dry-run airtime is excluded from paid-reward totals.
- Mobile table cards use separate Open and action buttons, removing invalid nested buttons. The operations page explains queued, accepted, unknown and dry-run delivery states.

## Database and compatibility

Apply Alembic through `20261102_27` before running the new backend. Revisions 25–27 add coverage, participant provenance/origin-aware inbound uniqueness, and delivery attempt metadata. Existing caller profiles default to `field`: their historical provenance cannot safely be inferred. Future demo seeds label participants `demo`. Historical callers touched by the old simulator require an operator review; migrations do not silently delete or relabel them.

The legacy `sector_id` remains one member of explicit coverage for older clients. Sending `coverage_sector_ids: []` clears coverage and the legacy primary. Downgrading coverage necessarily retains only the legacy primary sector; export service areas before an operational rollback.

## Operating the delivery outbox

From `backend/`, with the intended environment selected:

```powershell
# Read-only summary; no network calls.
python scripts/process_delivery_outbox.py

# After telecom approval: schedule this command periodically with one or more workers.
# It can charge the configured SMS/airtime account. This was NOT run during implementation.
python scripts/process_delivery_outbox.py --send --limit 100

# Recovery after a worker crash: mark claims older than five minutes unknown.
# This changes states but never sends or requeues a message.
python scripts/process_delivery_outbox.py --recover-stale
```

Without a scheduled dispatcher, live messages remain queued. `unknown` requires matching the provider's records before any manually approved resend. Historical `pending` airtime is not automatically replayed. There is no claim of exactly-once delivery across a network failure.

Anonymous grievance SMS replies remain synchronous: storing a queued recipient beside the grievance reply would break the existing anonymity guarantee. An approved private reply design is required before extending durable delivery to those replies. Signed provider delivery callbacks, automatic safe retries, reconciliation UI and queue alerting remain follow-up work. Do not interpret acceptance as handset receipt.

## Remaining work after this milestone

| Area | Remaining work |
| --- | --- |
| Scientific inputs | Official approved crop/season baselines and exact-period rainfall references; measurement and agronomy protocols |
| Telecom | Credentials/short code, real-phone sandbox acceptance, delivery callbacks, reconciliation and a scheduled outbox worker |
| Geography | Verified service areas and asset cells/boundaries; no service area was invented from a scheme name |
| Rainfall compatibility | Align every older activity/trend/map calculation with dated observations and coverage-aware scientific analysis |
| Management | Move remaining classic category/inventory tools into React; seed only district-approved production reference inventory |
| Privacy operations | District-approved retention/anonymization operations, personal-data read auditing and review of historical simulator-touched profiles |
| Language/accessibility | Native Kinyarwanda review for newer workspaces; staff usability testing and wider assistive-technology checks |
| Analytics/ML | Formal quality/uncertainty policy and data-readiness assessment; no ML training on demonstration/simulator data |
| Pilot/deployment | Staging rehearsal, authenticated staff accounts, provider acceptance, official data entry and district handover approval |

These are tracked gaps, not claims of completion or field validation. No production deployment, live SMS/airtime, configured application database migration, or repository push was performed.

## Final verification

- Backend: **278 tests passed**, including migrations, profile isolation, rollback-safe reward creation, outbox claims/recovery, authorization and corrected summaries.
- Frontend: **57 tests passed**, type check, lint and production build passed. Unit tests used two workers with file parallelism disabled after resource contention caused timeouts in an earlier concurrent run.
- Chrome: **22 end-to-end tests passed** on the final build, including the new multi-sector administration/mobile workflow.
- PostgreSQL **18.6** / PostGIS **3.6.2**: migrated the disposable localhost validation database, verified **zero schema differences**, downgraded all three new revisions and re-upgraded; existing spatial, yield, climate and maintenance workflow checks passed with rolled-back fixtures. The disposable cluster was stopped afterwards.
- Local platform: restarted through the corrected `start-local.ps1 -Demo`; landing, dashboard, health, readiness and scheme endpoints returned HTTP 200. Counts remained 25 caller profiles, 56 crop reports and 70 irrigation reports before/after restart. Only the isolated demo database was migrated.
- Existing build notices remain for public font URL resolution and the large Mapbox chunk. No field/telecom acceptance, production CI run or deployment is implied by these local checks.
