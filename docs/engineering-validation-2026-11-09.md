# Engineering validation — 9 November 2026

## Outcome and scope

The platform passes the local backend, frontend and browser suites and disposable PostGIS checks. It is a candidate for controlled staging rehearsal. Docker and hosted CI for this revision remain unverified; production and field activation are blocked by the external gates below.

Work started at `b13180bf7be5c1708a5e90a0da94a34b03f21ce2`, on the existing stabilization branch, then moved to `fix/pilot-validation-20261109`. The unrelated untracked PDF and motivational-letter script were preserved. No live messages, credential changes, production migrations, deployment, DNS or billing actions occurred. Existing migration history is unchanged at `20261102_28`.

## Audit and dependency order

Reviewed README, roadmap, November completion and activation documents; recent commits; CI jobs; simulator browser fixtures; USSD onboarding/menu handling; shared channel parsing and receipt processing; runtime security configuration, authentication/scope and outbound dispatch; migration/schema/spatial validators; Docker/Render/handover configuration; scientific evidence tests and the native-language review checklist. The architecture remains FastAPI/SQLAlchemy/Alembic, PostgreSQL/PostGIS, React/TypeScript/Vite, a classic static dashboard, and Africa's Talking callbacks with dry-run simulation. No redesign or dependency changes were needed.

Execution order: preserve the working tree and inspect historical evidence → run existing checks → reproduce input and receipt defects → implement small fixes with regressions → rerun complete suites → validate isolated PostGIS and backup/restore → record current statuses. External dependencies did not stop independent local verification.

## Simulator investigation

The historical [Actions run](https://github.com/Alliance2k2/cs-ircfs-platform/actions/runs/41892197182) was inspected through connected GitHub tools. Backend, PostGIS, frontend and Docker jobs succeeded; browser workflows failed. Job `126792859396` logs contain the exact expected sector prompt versus received six-option main-menu mismatch.

The existing stabilization commits already isolate callers per browser attempt, wait for the exact rainfall prompt, protect pending simulator actions and assert both onboarding and returning-user behavior. Those fixes were retained. Current full browser validation passes, and three simulator repetitions pass on one disposable server/database. No assertions were removed. New callers choose sector/cell; registered callers correctly skip that step. The stateless USSD path is replayed per callback; a new provider session can restart navigation. Carrier-enforced expiry still requires real-device/provider acceptance; no server-side expiry guarantee is inferred.

## New verified fixes

1. **Invalid numeric menu input.** `str.isdigit()` accepts superscript and circled digits that `int()` cannot convert. Calling `pick(['one'], '\u00b2')` reproduced `ValueError`. Very long decimal strings can also exceed Python's conversion limit. The parser now requires decimal characters and catches conversion failures, returning the established invalid-answer response. Valid decimal input, including leading zeroes, retains its earlier conversion semantics. Twelve callback regressions cover malformed choices at the main/crop/nutrition paths and first-time sector selection; report APIs remain empty for rejected answers.
2. **Delivery-receipt memory bound.** SMS/airtime receipt handling called `request.body()` before the shared streaming limit, buffering the entire payload. It now goes directly through the existing 16 KiB streamed parser. Two regressions verify that processing stops on the second 8,193-byte chunk rather than reading a third chunk, and returns HTTP 413 before database work. Both tests reported failure before the fix; that sandboxed pre-fix process stalled during cleanup and was stopped. Both pass in the final complete suite. Authentication, receipt status mapping and reconciliation are unchanged.

An initial regression draft used the wrong crop-read URL; it was corrected to the existing `/api/v1/citizen-reports` contract before final validation. Initial sandbox/temp and child-process errors were addressed through scoped execution permission and disposable test paths, not application changes.

## File-level change log

| File | Reason |
| --- | --- |
| `backend/app/services/ussd.py` | Reject non-convertible and oversized menu numbers safely |
| `backend/tests/test_ussd.py` | Twelve malformed-choice/onboarding regressions, including absence of scientific writes |
| `backend/app/api/routes/delivery.py` | Remove full-body prebuffering before the shared stream limit |
| `backend/tests/test_stabilization_security.py` | Two early stream-termination regressions for SMS/airtime receipts |
| `README.md` | Link current verification evidence |
| `docs/roadmap.md` | Current workstream counts and remaining acceptance gates |
| `docs/platform-completion-2026-11.md` | Identify current results and retained external dependencies |
| `docs/production-activation-checklist.md` | Record local checks separately from external activation |
| `docs/engineering-validation-2026-11-09.md` | Audit, commands, results, limitations and next actions |

## Executed validation

Environment: Windows, repository Python 3.13.9 virtual environment, Node v24.20.0 and local Chrome. CI targets Linux/Python 3.12/Node 22/Chromium; local success does not certify that environment. Telecom providers stayed dry-run. Commands below use PowerShell syntax and start in the indicated directory.

| Directory and command | Actual result |
| --- | --- |
| `backend`: `../.venv/Scripts/python.exe -m pytest -q` | Initial correct-directory sandbox run: 311 passed, 14 setup errors caused by temp-directory access. An earlier root-directory run also failed the subprocess import test because its working directory was wrong; not treated as an application defect |
| `backend`: `../.venv/Scripts/python.exe -m pytest -q --basetemp=.pytest-tmp/validation-20261109 -o cache_dir=.pytest-tmp/cache-20261109 --tb=short` | Intermediate USSD-inclusive suite: 337 passed |
| `backend`: `../.venv/Scripts/python.exe -m pytest -q --basetemp=.pytest-tmp/final-20261109 -o cache_dir=.pytest-tmp/cache-20261109 --tb=short` | **339 passed**, zero failures, 13 existing deprecation warnings, 253.28 seconds; includes migrations and both receipt regressions |
| `frontend`: `npm run typecheck`; `npm run lint` | Both passed |
| `frontend`: `npm test -- --maxWorkers=1 --no-file-parallelism` | **61 passed**, 17 files, 69.72 seconds; initial sandbox attempt could not spawn esbuild |
| `frontend`: `npm run build` | Passed TypeScript and Vite production build, Vite 47.77 seconds; existing runtime-font-path and large Mapbox-chunk notices remain |
| `frontend`: `$env:PYTHON='../.venv/Scripts/python.exe'; npm run e2e` | **25 passed**, zero retries, 4.4 minutes, including setup/authentication and simulator workflow |
| `frontend`: `npx playwright test 07-simulator --repeat-each=3` with the same `PYTHON` | **8 passed**: five role sign-ins and three simulator attempts, 39.9 seconds. Ignored log: `backend/.pytest-tmp/simulator-repeat-20261109.log` |
| Isolated PostgreSQL: commands below | Upgrade, zero schema differences, downgrade/upgrade, rollback-only spatial/scientific checks passed; PostgreSQL 18.6 / PostGIS 3.6.2 |
| Native `pg_dump -Fc -f`, `createdb`, `pg_restore --exit-on-error` in isolated cluster | Passed; restored revision `20261102_28` and PostGIS `3.6.2` into a second new database. This rehearses the disposable schema, not recovery of production records or encrypted off-site backups |
| Translation inventory via `scripts.translation_review.package()` | 697 keys, 39 Kinyarwanda drafts, 658 English fallbacks, zero approvals |
| Tracked text scan: AWS access-key IDs, private-key headers, GitHub classic tokens and Stripe live-key signatures | 425 tracked text files, zero candidate files; values never printed. Limited signatures are not an exhaustive secret/history audit or proof of provider revocation |
| `git diff --check` | Passed; Git reports line-ending normalization notices |
| `docker version` / container build | **BLOCKED:** Docker executable unavailable; image not built locally |
| GitHub commit workflow lookup | No runs returned for baseline `b13180bf7be5c1708a5e90a0da94a34b03f21ce2`; no new hosted run or publication performed. Scoped open issue/PR search returned no results |

Disposable PostGIS commands used a newly initialized local-only cluster on port 55439; the existing service on 5432 and application database were untouched:

```powershell
# backend/, only after creating the isolated cluster and this new database
$env:DATABASE_URL='postgresql+psycopg://validation_owner@127.0.0.1:55439/cs_ircfs_20261109_validation'
$env:ENVIRONMENT='staging'
$env:WEATHER_FORECAST_ENABLED='false'
$env:SMS_PROVIDER='dry_run'
$env:AIRTIME_PROVIDER='dry_run'
$env:ALLOW_LIVE_MESSAGES='false'
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe scripts/check_schema.py
../.venv/Scripts/python.exe -m alembic downgrade -1
../.venv/Scripts/python.exe -m alembic upgrade head
$env:POSTGIS_VALIDATION_URL=$env:DATABASE_URL
../.venv/Scripts/python.exe scripts/check_postgis_workflows.py
```

Workflow checks returned a valid SRID round trip, row-lock query, synthetic yield achievement 75%, rainfall anomaly 50% and downtime 6h. Those numbers are test expectations, not district findings. Workflow fixtures rolled back. The disposable cluster uses local trust authentication solely for this rehearsal and must not be used for hosting.

## Security, privacy and evidence status

**Fixed locally:** malformed-number callback crashes and receipt full-body buffering. Existing full-suite coverage also passes for auth/roles/scopes, simulator/field separation, phone throttling, duplicate callbacks, delivery reconciliation, pending/private routing, masking, retention policy gates and scientific provenance. This is regression evidence, not an exhaustive penetration or concurrency/load assessment.

**External action still required:** revoke/replace the previously exposed Africa's Talking credential in the owner console, verify callback secrets/IP configuration and redact query tokens at the proxy. No credential was printed, rotated, revoked or certified safe. Keep providers in dry-run until separately approved. Review original account history and provider logs through authorized ownership.

Scientific evidence still requires sourced approved targets, references, measured observations and protocols. Existing missing-value, units, verification/origin and supersession exclusions pass local tests; no PADAB/APEFA or rainfall baseline was invented. District administrative boundaries, assets and scheme coverage require authoritative field acceptance.

## Workstream classifications and deployment readiness

| Workstream | Classification | Remaining requirement |
| --- | --- | --- |
| Simulator and malformed input | COMPLETED locally | Carrier/device acceptance remains separate |
| Backend/frontend/browser regression suites | COMPLETED locally | Hosted CI on exact published revision |
| Receipt hardening, privacy/auth/scientific regressions | COMPLETED locally | Broader security/load review and approved operational policies |
| PostGIS migration/schema/spatial and schema backup/restore rehearsal | COMPLETED locally | Production-version hosted rehearsal and real encrypted backup recovery |
| Docker/deployment configuration | IMPLEMENTED / NOT VERIFIED | New container build; Docker unavailable locally |
| Hosted CI and staging deployment verification | BLOCKED | Published revision, hosting access and actual staging URL |
| Telecom delivery/receipt format and feature-phone acceptance | BLOCKED | Owner-approved credentials, shortcode, devices and provider sandbox rehearsal |
| Kinyarwanda native review | BLOCKED | Native/domain reviewers; use existing structured review checklist |
| Selectable and persisted field USSD language | PENDING | Field menu is Kinyarwanda-first; simulator English is an aid, not a saved language preference |
| Official scientific baselines and district inventory | BLOCKED | Institutional reference data and protocol approval |
| Retention, pilot and production sign-off | BLOCKED | District policy ownership and explicit activation approval |

Use [staging smoke/rollback instructions](staging-smoke-checklist.md), [activation gates](production-activation-checklist.md) and [native review checklist](pilot/kinyarwanda-review-checklist.md). Existing `/health` liveness, `/ready` database readiness, pre-start migrations and dry-run configuration remain intact. No hosted readiness probe was run in this session. No production readiness or institutional approval is claimed.

## Top three next actions

1. Publish the reviewed revision through the normal PR process and require all hosted CI jobs, especially Chromium and Docker, to pass. Then rehearse the exact artifact against isolated staging and its real URL.
2. Have the credential owner revoke the exposed key, configure separate sandbox credentials and callbacks, and perform approved feature-phone/delivery reconciliation tests before enabling paid providers.
3. Obtain sourced district baselines/inventory, native Kinyarwanda and consent review, approved privacy/retention protocols and institutional pilot sign-off. Keep field/production activation blocked until evidence is recorded.
