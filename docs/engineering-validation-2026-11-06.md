# Engineering validation - 6 November 2026

Final packaging/review continued on 7 November 2026.

## Executive engineering summary

Work is on `fix/pilot-stabilization-20261106`, based on merged main `7e0c1d5`. The existing architecture, public layout, records and migration revisions are preserved. Unrelated local PDF/script files are untouched. No real messages, credential rotation, production migration, DNS/billing action or deployment was performed.

The simulator failure has been reproduced and corrected without deleting onboarding or evidence-isolation assertions. Additional verified fixes address rainfall input failures, historical-data readability, callback bounds, log privacy, production CORS, build-context exclusions, hosted inventory integrity and a mobile accessibility defect. The platform is a candidate for isolated staging validation, not approved for real participant data or field activation. Hosted CI and a new Docker build require publishing this branch; the actual hosted URL is still missing.

## Architecture and audit scope

| Subsystem | Actual architecture and reviewed behavior |
| --- | --- |
| Public website | Buildless HTML/CSS/JS in `dashboard/`, served by FastAPI; approved original layout retained |
| Staff workspace | React/TypeScript/Vite at `/app/`, TanStack Query, local fonts, role-aware navigation |
| Authentication | Email/PBKDF2 and Google ID-token verification; pending registration, approved roles, scoped access, hashed expiring sessions, httpOnly SameSite cookies; production requires Secure cookies |
| Backend/data | FastAPI, SQLAlchemy, Alembic; SQLite for disposable tests/demo, PostgreSQL/PostGIS for hosted records; migration head remains `20261102_28` |
| Field channels | Kinyarwanda-first stateless USSD full-path requests; SMS keywords; gateway token/IP checks, phone throttling and persisted deduplication |
| Delivery/privacy | Dry-run defaults, claimed outbox, receipt journal, unknown-outcome review, optional encrypted temporary routing, read/mutation audit, retention preview/apply policy gates |
| Evidence | Origin/verification/supersession exclusions, measured area/yield units, approved crop/season/year targets, dated gauges, missing-value handling, rainfall references and traceable exports |
| Deployment | Multi-stage Node/Python Dockerfile, PostGIS Compose/Render configuration, health/readiness, read-only deployment verifier and backup/restore procedures |

Reviewed README, roadmap/completion/activation documents, CI workflow, models/migrations, callback/auth/privacy/delivery/scientific/geospatial services, frontend workflows, environment examples, container configuration and operator scripts. GitHub has no open issues/PRs returned by the scoped issue search. Historical main CI failed the simulator; its successful backend/build/Docker results are not represented as verification of this new revision.

## Dependency-aware implementation and verified fixes

1. **Stabilization.** The unchanged browser test passed with a fresh caller (6 checks including setup), then failed with the same caller on both the original attempt and retry (5 setups passed, one workflow failed). Returning callers correctly skip onboarding. Each test attempt now owns a fresh caller. The test waits for the exact rainfall-entry prompt, rather than the main menu's Report rainfall text. The UI disables in-flight answer/caller/hang-up/redial controls, resets local state on caller changes and uses UUID session identifiers. Two new UI regressions first failed and then passed; the final redial regression also passed. Three repeated browser attempts subsequently passed on one database.
2. **Scientific input reliability.** Phone handlers accepted up to 500 mm while the write schema allowed 300 mm. Invalid readings could be stored and later fail response validation. Both phone channels now use the existing shared 300 mm application limit. Tests cover non-finite/negative/out-of-range inputs, zero/300 boundaries and restarting a stateless session. Historical finite unusual readings remain readable without clamping/deleting originals, retain quality flags, and cannot be newly submitted through the strict write schema. This limit is an application validation rule, not an approved local climatological threshold.
3. **Security/backend.** Database error logs no longer print SQL/driver parameters. Raw Uvicorn access logs are disabled in favor of query-free request logs; launcher/container flags reinforce this. Callback bodies are stream-bounded to 16 KiB even without Content-Length. Session/message IDs are bounded to PostgreSQL's 120-character column width before writes. Production rejects wildcard credentialed CORS. In-process Alembic configuration preserves application loggers. Container context excludes credentials, local auth state, logs, backups and tool state; database dumps are Git-ignored. Initial four logging/body-bound regressions failed before the fixes.
4. **Inventory/evidence integrity.** Hosted USSD no longer presents hardcoded development pump names as confirmed scheme assets. Retiring all configured assets cannot resurrect examples. Hosted empty inventories end safely without a report; active configured entries remain usable. The new unavailable-inventory Kinyarwanda line is a draft requiring native review.
5. **Accessibility.** Axe found a critical unnamed mobile search button because its visible text is hidden on narrow screens. It now has the existing translated accessible label and a mobile keyboard search/navigation regression. Desktop initially had no automated violations. Final rebuilt checks had zero automated A/AA violations and no horizontal overflow at both 390px and 1440px. Screenshots: [mobile](images/stabilization-20261106/simulator-390.jpg), [desktop](images/stabilization-20261106/simulator-1440.jpg). This is not a manual WCAG certification.

The public website was not redesigned. No production records or migration history were deleted or reset.

## File-level change log

| Files | Reason |
| --- | --- |
| `frontend/src/features/simulator/SimulatorPage.tsx` | Pending-action protection, caller/session separation and UUIDs |
| `frontend/src/features/simulator/SimulatorPage.test.tsx` | Delayed response, caller change and redial regressions |
| `frontend/e2e/07-simulator.spec.ts` | Isolated caller per attempt; exact prompt and returning-user assertions |
| `frontend/src/components/navigation/TopBar.tsx`, `frontend/e2e/10-navigation-reports.spec.ts` | Named mobile search and keyboard regression |
| `backend/app/services/ussd.py`, `backend/app/services/sms_keywords.py` | Consistent rainfall bounds; hosted inventory safeguards |
| `backend/app/schemas/reports.py`, `backend/tests/test_workspaces.py` | Read original unusual historical values; preserve flags; reject new invalid writes |
| `backend/app/api/routes/channels.py` | Streamed body and identifier limits |
| `backend/app/core/config.py` | Reject production wildcard CORS |
| `backend/app/main.py`, `backend/app/core/logging.py` | Remove sensitive exception/query logging |
| `backend/migrations/env.py`, `backend/tests/test_migrations.py` | Preserve logging during migrations; no revision/schema change |
| `backend/tests/test_stabilization_security.py`, `test_ussd.py`, `test_ussd_inventory.py` | Security, invalid-input/recovery and configured-inventory regressions |
| `Dockerfile`, `start-local.ps1`, `backend/scripts/run_e2e_server.py` | Explicitly suppress raw access URLs |
| `.dockerignore`, `.gitignore` | Keep local auth/credential/backup artifacts out of builds/Git |
| `README.md`, `docs/roadmap.md`, `platform-completion-2026-11.md`, `production-activation-checklist.md`, `security.md`, `testing.md`, `deployment.md`, `architecture.md`, this report and the staging/native-review checklists | Current evidence, operators, statuses and remaining approvals |

## Actual test results

Local environment: Windows, Python 3.13.9 in repository `.venv`, Node v24.20.0, installed Chrome; isolated SQLite test databases and PostgreSQL 18.6/PostGIS 3.6.2 on localhost port 55439. CI uses Linux/Python 3.12/Node 22/Chromium and must be checked separately. Full output is in ignored `backend/.pytest-tmp/stabilization-*.log`, with concise outcomes retained here.

| Command/check | Actual result |
| --- | --- |
| `cd backend; ../.venv/Scripts/python.exe -m pytest -q` | Initial expanded run: 316 passed, 2 failed. Follow-up: 322 passed (234.02s). Final inventory-inclusive run: **325 passed**, 13 existing deprecation warnings (221.55s) |
| `npm test -- --maxWorkers=1 --no-file-parallelism` | 61 passed, 17 files (140.30s); no retries. Final simulator-specific rerun: 2 passed (10.88s) |
| `npm run build` | TypeScript and production Vite build passed; final accessibility build passed (57.10s) |
| `npm run lint` | Passed; final check after the mobile label also passed |
| `PYTHON=../.venv/Scripts/python.exe npm run e2e` | 24 passed (2.9m), zero retries. Final run including new mobile test: **25 passed** (2.7m), zero retries |
| `npx playwright test --config ../backend/.pytest-tmp/playwright-stabilization.config.ts 07-simulator --repeat-each=3` | 8 passed: 5 sign-in setups and 3 independent simulator runs (48.5s) |
| PostGIS: `alembic upgrade head`, `check_schema.py`, `alembic downgrade -1`, upgrade again, `check_postgis_workflows.py` | Passed: zero schema differences, spatial round trip, row-lock query, synthetic yield/rainfall/downtime calculations. Workflow fixtures rolled back |
| Native `pg_dump -Fc`, restore into a different fresh database | Passed: archive header and synthetic marker/valid SRID-4326 geometry preserved. No application data accessed |
| Existing PowerShell binary-redirection pattern, harmless byte fixture | Preserved bytes on this Windows runtime; no unsupported backup-script defect claimed |
| `python scripts/verify_deployment.py http://127.0.0.1:8772 --environment staging` | All 12 read-only checks passed, optional admin checks not run. A first attempt during the rebuild correctly reported the missing build; rerun after completion passed |
| Tracked-text credential signature scan | 356 files, zero signature candidate files; no secret values printed. This is not proof that historical/provider credentials were rotated |
| `python scripts/translation_review.py --output .pytest-tmp/kinyarwanda-stabilization-review.json` | 697 keys, 39 draft translations, 658 English fallbacks, zero native approvals. Initial sandbox write denial resolved with scoped permission |
| Docker CLI/build | BLOCKED locally: Docker executable/daemon unavailable. New hosted CI build not yet run |

Existing warnings: Starlette/httpx deprecation; Alembic path-separator deprecation; Vite runtime font-resolution notices and a large Mapbox chunk. No new dependency was introduced. No real-device, carrier, load/concurrency or hosted performance certification is claimed.

## Security findings and residual risks

**Fixed and regression-tested:** SQL/driver detail in error logs; raw callback query tokens in Uvicorn logs; unbounded channel bodies; oversized callback IDs; production wildcard CORS; example/retired asset fallback; inconsistent rainfall acceptance; migration-side logger disabling; simulator pending/caller state bugs. Build-context exclusion changes are implemented, but a new Docker image still needs hosted validation.

**Verified existing controls:** full suite covers roles and sector scopes, account approval and session/logout behavior, gateway secret/IP checks, duplicate/retry guards, delivery journal reconciliation, anonymous-report masking, personal-read audit, policy-gated retention/private replies, origin exclusions and scientific provenance. SameSite cookies and JSON state-changing endpoints are existing CSRF boundaries, not a claim of an exhaustive penetration test. Classic-page CSP remains report-only; the React script policy is enforced. Reverse proxies must separately redact query tokens from their access logs.

**External action required:** revoke/replace the previously exposed Africa's Talking key, verify its history and callback configuration, restrict new credentials and confirm rotation in the provider console. No rotation or revocation was performed or claimed. Fix Google OAuth authorized origins in the owning Cloud account. Native translation/consent review, privacy/retention ownership and evidence approval remain prerequisites.

## Workstream status and deployment readiness

| Workstream | Classification | Remaining dependency |
| --- | --- | --- |
| Simulator fix, UI regressions, channel validation | COMPLETED locally | New hosted CI must execute this branch |
| Auth/privacy/delivery/science regression coverage | COMPLETED locally | Live/provider/device/official-data acceptance not established |
| PostGIS migrations/schema/spatial/restore rehearsal | COMPLETED locally | Hosted database and encrypted off-site restore rehearsal |
| Docker context/runtime hardening | IMPLEMENTED / NOT VERIFIED as a new image | Docker unavailable locally; publish CI with approval |
| Hosted green CI | BLOCKED | Approval to push branch/open PR; existing main has a historical simulator failure |
| Hosted staging deployment smoke | BLOCKED | Actual service URL, hosting access and deployment authorization |
| Kinyarwanda | BLOCKED for native approval; fallback verified | 658 missing dashboard drafts; no phone language selector/persistence exists (live USSD is RW-first, simulator English is an aid) |
| Official geography/assets/baselines | BLOCKED | Approved district boundaries, manifests, crop/season/year targets and reference windows |
| Carrier SMS/USSD/billing acceptance | BLOCKED | Rotated credentials, approved code, callback provisioning, real devices and explicit live-send approval |
| Load, concurrent-worker contention, hosted mobile performance | PENDING | Controlled staging workload and representative devices |
| Production/field activation | BLOCKED | Institutional/privacy/operational sign-off; never inferred from passing tests |

## Staging, rollback and next actions

Use [the staging checklist](staging-smoke-checklist.md) and existing [deployment guide](deployment.md). Build before starting the release, verify the configured Git commit/branch, inject secrets outside Git, back up the intended database, migrate before serving, verify `/ready`, and keep delivery/forecast schedulers off during controlled smoke checks. Restore only into an isolated named database for rehearsal. For rollback, stop workers and redeploy the previously verified application artifact only after confirming schema compatibility; do not blindly downgrade away receipt/audit data or overwrite a production database.

Top three next actions, in dependency order:

1. Approve publishing the stabilization branch/PR, then verify all hosted CI jobs including Docker; do not merge a red pipeline.
2. Rotate exposed provider credentials and validate a separately configured HTTPS staging deployment with backups and an actual URL, keeping messages dry-run.
3. Supply official inventories/baselines and native-reviewed Kinyarwanda/consent, then authorize a small real-device rehearsal before any field activation.
