# USSD language selection — engineering validation, 13 November 2026

## Scope and initial audit

Branch: `feature/ussd-language-selection-20261113`, based on `bf9e4f2`. Existing uncommitted login/landing/sign-in-test changes and application-material files were preserved and are outside this feature's change set. No deployment, merge, credential change or live message was performed.

The audit confirmed that `ussd.py` already contains `(Kinyarwanda, English)` screen pairs, but `con()` and `end()` always selected Kinyarwanda for the field response. English was a separate simulator aid. `FieldUser` had no preference column; the `language` column elsewhere belongs to another model. USSD callbacks replay the complete answer path and journal responses for retries. Simulator callers and session IDs already use staff-specific non-dialable namespaces. Dashboard EN/RW selection is independent of field USSD.

Reviewed the FastAPI callback parser, gateway validation, transaction/deduplication handling, participant registration/consent behavior, participant and inbound-message models, migration history, paired phone translations, simulator UI and tests, browser fixtures and CI commands. Retained the existing architecture and dependencies.

## Implemented behavior

- New callers see a bilingual numbered prompt: `1. Ikinyarwanda`, `2. English`. Choosing a language continues directly to the existing sector/cell onboarding in that same session.
- Reporting choices **1–6 keep their previous meanings**. The main menu adds navigation choice **0** for language settings. A returning caller chooses `0`, then `1` or `2`, and continues to the appropriate location/main menu without resetting profile or reports.
- `FieldUser.ussd_language` is nullable and database-constrained to `rw`/`en`. New profiles remain unselected until a valid choice. Migration `20261113_29` gives existing profiles `rw` to preserve their previous field behavior; it does not invent a claim that those callers explicitly chose RW.
- Existing paired strings supply the selected `CON`/`END` field response. English simulator assistance remains separate. The new RW navigation wording is marked in source and the review checklist as a draft requiring native approval.
- The original bilingual dial response in the callback journal identifies whether the full answer path starts with a language choice. This avoids treating an English choice `2` as the pest-report branch after the preference has already been saved. `0` paths carry an explicit settings prefix. No new session table, process-local state or provider call is introduced.
- Only the selection callback updates the preference; replaying a longer path does not overwrite a newer choice from another session. Exact duplicate callbacks replay the stored reply through the existing unique-key/transaction mechanism.
- Preference callbacks do not backfill an existing participant's consent timestamp, opt-out status, location, activation or origin. Normal initial-contact consent behavior is retained. Scientific values and reporting calculations are unchanged.
- Simulator preference changes affect only the existing staff-namespaced training profile; real callers with the same displayed phone/session remain separate.
- A nonblank `sessionId` is now required for USSD, before registration. Gateway/simulator sessions already provide it. SMS behavior and its IDs are unchanged.

The journal must be retained during active carrier sessions. As before, a carrier restart uses a new session ID. This release does not add a carrier timeout engine or validate real-device session duration. Roll out schema and application together outside active sessions; the onboarding marker is the saved bilingual prompt from this version.

## Changed files

| Files | Purpose |
| --- | --- |
| `backend/app/db/models.py`, `backend/migrations/versions/20261113_29_ussd_language.py` | Nullable constrained preference, preservation of legacy RW behavior, reversible schema change |
| `backend/app/services/ussd.py` | Bilingual selection, option 0, selected-language rendering and answer-prefix handling |
| `backend/app/api/routes/channels.py` | Journal-aware replay, required session ID, preference-only consent handling |
| `backend/app/services/reporting.py` | Optional consent backfill suppression for language callbacks |
| `backend/tests/test_ussd_language.py` | 28 service/callback cases covering both languages, invalid input, retries, profile preservation, all reporting prompts, constraints and isolation |
| `backend/tests/test_migrations.py` | Upgrade/downgrade, legacy profile snapshot and retained scientific report checks |
| `backend/tests/conftest.py`, `test_ussd.py`, `test_advisory.py`, `test_calibration.py`, `test_hardening.py`, `test_reports.py`, `test_simulator_profiles.py` | Declare legacy RW fixtures or perform language selection before existing reporting assertions; retain duplicate, anonymity and scientific-write assertions |
| `frontend/e2e/07-simulator.spec.ts` | Select English before the existing location/reporting workflow |
| `frontend/e2e/14-ussd-language.spec.ts` | Two browser workflows with English aid off: RW/EN selection, location, reporting, changing, reload persistence and invalid settings |
| `README.md`, `docs/roadmap.md`, `docs/platform-completion-2026-11.md`, `docs/testing.md`, `docs/staging-smoke-checklist.md`, `docs/pilot/kinyarwanda-review-checklist.md`, this report | Current behavior, migration instructions, test evidence and review gates |

## Validation evidence

Local environment: Windows, Python 3.13.9 repository virtual environment, Node v24.20.0, installed Chrome, SQLite test databases, PostgreSQL 18.6 / PostGIS 3.6.2. Hosted CI uses Linux/Python 3.12/Node 22/Chromium and is a separate validation requirement. Test providers remain dry-run; forecast/external services are disabled by test fixtures.

| Command/check | Executed outcome |
| --- | --- |
| `cd backend; ../.venv/Scripts/python.exe -m pytest -q --basetemp=.pytest-tmp/language-initial-20261113 -o cache_dir=.pytest-tmp/cache-language --tb=short` | 324 passed, 15 failed: previous test setups skipped newly required language selection. Updated setup/paths without removing meaningful assertions |
| Targeted `test_ussd_language.py` run | Initial 24 passed, 2 failed because the new test expected “Choose”/“Hitamo” where the existing pest prompt says “Which crop is affected”/“Igihingwa cyafashwe”; corrected expectations to existing resources |
| `cd backend; ../.venv/Scripts/python.exe -m pytest -q --basetemp=.pytest-tmp/language-second-20261113 -o cache_dir=.pytest-tmp/cache-language --tb=short` | **368 passed**, 17 existing deprecation warnings, 145.13 seconds |
| `cd frontend; npm run typecheck` | Passed |
| `cd frontend; npm run lint` | Passed |
| `cd frontend; npm test -- --maxWorkers=1 --no-file-parallelism` | **61 passed**, 17 files, 227.03 seconds |
| `cd frontend; npm run build` | Passed TypeScript and production Vite build; 2310 modules transformed, Vite 1m 2s; existing font-path and large Mapbox-chunk notices remain |
| `cd frontend; $env:PYTHON='../.venv/Scripts/python.exe'; npm run e2e` | **28 passed**, zero retries, 3.5 minutes; includes five role setups, the preserved uncommitted sign-in regression and both new language workflows. Verified the working tree, not a clean hosted checkout |
| Disposable PostGIS `alembic upgrade head`, `scripts/check_schema.py`, `alembic downgrade -1`, upgrade again, `scripts/check_postgis_workflows.py` | Passed, including migration 29; zero schema differences; synthetic workflow fixtures rolled back |
| Disposable PostGIS `scripts/seed_reference_schemes.py`, `scripts/seed_demo_data.py --yes` | Passed; demonstrations created only in the new validation database |
| Repository Python `-m pip check` | Passed: no broken requirements |
| `cd frontend; npm audit --omit=dev --json` | Exit 1: three existing production-package findings (two moderate: `react-router`, `react-router-dom`; one high: `zod`). Suggested fixes require major-version upgrades; no dependency changes included in this USSD feature |
| Backend `pip-audit -r backend/requirements.txt --format json` using an ignored isolated tool installation | Exit 1: scanner reports two advisory entries for `pytest` 8.4.2, both with ID `PYSEC-2026-1845`, suggesting 9.0.3. Requirements currently restrict pytest below 9. These are not counted as two distinct IDs; the advisory gate is not green. 43 resolved dependencies examined; this is the CI requirements-resolution audit, not an audit of every installed environment package |
| Docker build | BLOCKED: Docker CLI unavailable locally |
| Hosted CI / deployment | NOT VERIFIED: this feature branch has not been published or deployed |

Ignored backend logs: `.pytest-tmp/language-initial-20261113.log`, `language-target-20261113.log`, `language-second-20261113.log`, `e2e-language-20261113.log`, `npm-audit-language-20261113.json`, `pip-audit-language-20261113.json`. Existing Starlette/httpx and Alembic path-separator deprecations remain. Browser teardown also logged an incidental Windows connection reset; all workflows passed. No application dependency version or lockfile was changed; the advisory scanner was installed only in an ignored tools directory.

PostGIS was initialized under `backend/.pytest-tmp/postgis-language-20261113`. Port 55439 was already occupied, so that first start failed without changing the other service; the new cluster ran only on `127.0.0.1:55441`, database `cs_ircfs_language_20261113_validation`, owner `validation_owner`. It uses local trust authentication solely for disposable validation, never hosting. `DATABASE_URL` and `POSTGIS_VALIDATION_URL` explicitly targeted that database. Existing application databases were untouched.

Before starting an application with this model:

```powershell
cd backend
python -m alembic upgrade head
```

Back up the intended database first under the existing deployment procedure. A downgrade from revision 29 **removes saved preferences**; re-upgrade sets then-existing profiles to RW again. Do not use downgrade as a routine application rollback or run against production without authorization.

## Acceptance status and remaining limitations

The disposable PostGIS cluster was stopped after successful checks. Existing database services and application databases were not modified. No feature publication or hosted verification was performed.

- **COMPLETED locally:** backend selection, persistence, replay, simulator isolation and SQLite/PostGIS migrations; frontend type/lint/unit checks, production build and all 28 browser checks.
- **BLOCKED externally:** native-speaker/agronomy wording approval, carrier screen limits/encoding/timeout acceptance, real feature-phone usability and hosted release validation. Docker also needs an environment with a working CLI/daemon.
- The preference applies to USSD screens; it does not change SMS keyword/reply localization, dashboard language, outbound advice, consent policy, agricultural data or official evidence. Existing English harvest wording continues to identify any local tip as Kinyarwanda rather than inventing a translated agronomic recommendation.
- Dependency advisory findings above remain open for a separate compatibility-reviewed update. Passing language tests does not close them or establish production security readiness.

## Pull request summary

**Title:** Add persisted Kinyarwanda/English field USSD selection

New callers choose a language before existing sector/cell onboarding; returning callers change it using option 0 while reporting choices 1–6 retain their meanings. Persist a constrained nullable preference, preserve legacy callers as RW, reuse paired screen resources and the existing retry journal, and keep training profiles separate from real participants. Add service/callback/migration and both-language browser coverage. Native/carrier acceptance and hosted deployment remain separate gates.
