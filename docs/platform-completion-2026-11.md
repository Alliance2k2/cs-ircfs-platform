# November completion: operations, privacy and consistent evidence

> Latest verification: [9 November engineering validation](engineering-validation-2026-11-09.md). Added safe malformed-number USSD handling and bounded receipt streaming. Current local totals are 339 backend, 61 frontend and 25 browser checks; prior results below are historical. Docker and hosted verification remain outstanding; external activation requirements remain open.

> Updated stabilization/security/evidence results and external blockers: [6 November engineering validation](engineering-validation-2026-11-06.md). No field activation or hosted green CI is inferred from local tests.

This is the current status, superseding the remaining technical gaps in Batch 6. The existing landing page is `/`, dashboard `/app/`, and reference management `/app/management`. Local demonstration access is available at `http://localhost:8000`; development bypass must remain disabled on a hosted pilot.

## Implemented

- Rainfall maps, monthly summaries, trends and advice now use dated observations and the same daily gauge aggregation. Rejected reports are excluded, repeated gauge/day readings use the latest reading, unidentified gauges are excluded, and missing rainfall stays missing. Receipt-time activity counts remain separate. Scientific anomalies still require complete verified evidence and approved references.
- React management supports adding, editing and deactivating asset inventory and grievance categories. Referenced names cannot be silently renamed. Asset cells must fit confirmed scheme coverage. Classic registry tools remain linked for historical workflows.
- Delivery operations provides a masked, searchable queue and audited reconciliation. Provider callbacks are authenticated, idempotent and journaled without recipient/message data. Early receipts can be correlated after the send response arrives. Late/duplicate callbacks cannot regress delivered transactions. Unknown outcomes require provider evidence before retry; no automatic resend is assumed safe.
- The optional worker supports continuous processing and cancels stale queued deliveries. Airtime acceptance requires a provider transaction ID. Paid totals include accepted and delivered real transactions, excluding demonstration/dry-run records.
- An optional private reply queue stores a short-lived encrypted route, erases it before a provider call and refuses expired/invalid routes. It remains **disabled** until a district policy and key are configured. This is temporary pseudonymization, not irreversible anonymity; timing and provider records can still correlate activity. Default anonymous replies retain their existing synchronous behavior.
- Staff access to personal records creates bounded audit metadata without copying searched text, phone numbers or message bodies. Older report APIs now enforce note masking for restricted roles too.
- Retention tooling previews profile/message minimization, protects pending deliveries and preserves scientific reports and mutation provenance. Read-access audit expiry is separate from scientific audit history. Apply requires an explicit policy reference and database confirmation.
- Readiness indicators report actual evidence counts, missing references and inventory gaps. Descriptive yield sample ranges are shown without claiming a population confidence interval, causal impact or authorization to train ML.
- Persistent dark mode is available in the dashboard; print styling remains light. Dashboard script CSP is enforced while classic pages retain their compatibility policy.
- A complete Kinyarwanda review pack, district inventory importer and read-only deployment verifier are available. Exported draft strings are **not native-reviewed translations**.

## Database and release

Run `alembic upgrade head` from `backend/` using the intended deployment environment before starting this version. Head is **20261102_28**: recipient-free delivery receipts and nullable encrypted routing fields. Back up the intended database before operational migrations. Downgrading revision 28 removes its receipt/routing data; do not downgrade while a worker is active.

No live provider, production database or district retention policy was activated during implementation. The local demonstration database was upgraded without resetting its reports.

## Operator commands

Run these from `backend/` with the intended environment selected. Preview commands do not send messages or apply data changes:

```powershell
python scripts/process_delivery_outbox.py
python scripts/retention.py
python scripts/import_reference_inventory.py ../docs/pilot/reference-inventory-template.json
python scripts/translation_review.py --output ../docs/pilot/kinyarwanda-review.json
python scripts/verify_deployment.py https://YOUR-DEPLOYMENT --environment production
```

The inventory template intentionally contains no invented district records and requires a real `source_reference`. Populate it with approved records before importing. Native reviewers must supply reviewer/evidence references, `review_status: approved_native_review`, every current key, approved translations and unchanged interpolation placeholders:

```powershell
python scripts/translation_review.py --check-reviewed reviewed-pack.json
python scripts/translation_review.py --check-reviewed reviewed-pack.json --apply-reviewed
python scripts/import_reference_inventory.py district-inventory.json --apply --confirm-database DATABASE_NAME
python scripts/retention.py --apply --policy-reference REVIEWED_POLICY --confirm-database DATABASE_NAME
```

Retention is pseudonymization/minimization, not a promise that all linkage is irrecoverable. Review backups, exports, provider records and accounts separately. Scientific records remain, and linked operational activity totals can change when expired links are removed. `MESSAGE_RETENTION_DAYS` defaults to 30, `FIELD_USER_RETENTION_DAYS` to 730, and personal-read audit expiry uses `AUDIT_LOG_RETENTION_DAYS`; district approval is needed before applying these defaults.

After approved telecom configuration and acceptance, an operator can schedule `process_delivery_outbox.py --send --watch --interval 10` or enable the optional Compose `delivery` profile. These can incur provider charges and were not run here. `--recover-stale` marks abandoned claims unknown; it never sends them. Review unknown outcomes in Channels → Delivery review against provider transaction records.

Configure provider receipt URLs as `/api/v1/delivery/sms?token=SHARED_SECRET` and `/api/v1/delivery/airtime?token=SHARED_SECRET` over HTTPS. Use a secret of at least 24 characters and the configured callback IP allowlist. Avoid exposing token-bearing URLs in proxy/access logs. SMS payloads require `id` and `status`; airtime requires `requestId` and `status`. Confirm the account's actual callback format in a real-phone sandbox rehearsal before live use. Acceptance and delivery are distinct; see the provider's [callback setup](https://help.africastalking.com/en/articles/2206161-how-do-i-configure-my-callback-url) and [airtime status guide](https://blog.africastalking.com/africas-talking-airtime-api-basic-usage-guide-b849fe6c88f).

Private queued replies additionally require `ANONYMOUS_REPLY_QUEUE_ENABLED`, a valid `ANONYMOUS_REPLY_ENCRYPTION_KEY` and `ANONYMOUS_REPLY_POLICY_REFERENCE`. Protect the key outside source control, approve custody/rotation procedures, and drain or expire old routes before rotation. TTL defaults to 300 seconds. Fernet authenticates encrypted data but exposes its timestamp; review the [Fernet specification and limitations](https://cryptography.io/en/latest/fernet/). No key is generated or checked into this repository.

The deployment verifier checks health/readiness, built dashboard, script policy, disabled demo bypass and blocked anonymous personal endpoints. Optional administrator checks read `DEPLOYMENT_CHECK_API_KEY` from the environment. It does not certify telecom, institutional acceptance or all security properties. CI can run it after an explicitly configured deployment URL becomes ready.

## External work still required

| Requirement | Required input or approval |
| --- | --- |
| Hosted release verification | Actual staging/production URL and authorized hosting configuration; none is recorded in this repository |
| Scientific evidence | Official crop/season targets, historical rainfall references, measured field observations and measurement/agronomy protocols |
| District inventory | Verified asset locations, service areas and sourced reference manifest |
| Telecom | Approved credentials/short code, callback configuration, real feature-phone tests and delivery/billing reconciliation |
| Privacy | Approved retention periods, private-reply policy, key custody and review of historical profiles touched by older simulator versions |
| Language and acceptance | Native Kinyarwanda review, accessibility/usability sessions and signed staff pilot acceptance |
| ML | Sufficient eligible field evidence and an independently reviewed validation/sampling design; no model trained on demonstration data |

These inputs cannot be invented or replaced by passing automated tests.

## Verification recorded for this revision

- Backend: **298 passed**, including migrations, privacy operations, scope/masking, reference validation, rainfall consistency, receipt races and private route expiry/erasure.
- Frontend: **59 passed**; lint, TypeScript and production build passed.
- Chrome: **24 passed** in the complete regression run, including dark-mode persistence, mobile management, role navigation, account approval, reporting and delivery reconciliation.
- PostgreSQL 18.6 / PostGIS 3.6.2: migration 28 upgrade, zero schema differences, downgrade/upgrade and rollback-only spatial/scientific workflow checks passed.
- Read-only deployment-check rehearsal passed against the isolated authentication-enabled browser test server. Optional administrator-secret checks were not run. This is not an online-production acceptance result.
- Local demonstration readiness, management, queue and schema checks passed. No retention apply, inventory import, private queue activation or live telecom send was performed.

Established build notices remain for public-font paths and the Mapbox chunk size. The tests report existing dependency deprecation warnings; these did not fail validation.

Release review: [pull request #13](https://github.com/Alliance2k2/cs-ircfs-platform/pull/13). GitHub CI results are tracked on that request.
