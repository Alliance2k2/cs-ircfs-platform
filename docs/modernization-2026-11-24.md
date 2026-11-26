# Platform modernization — 24 November 2026

## Audit and preservation

Work branch: `feature/platform-modernization-20261124`, based on local
`6c1b4c8`. Remote main was inspected at `cfe1450`; the local branch already has
newer assistant, knowledge-ingestion and session-validation changes. Resetting
to main would lose those improvements. Fifty-one modified/new project files
were copied to the ignored `backend/.pytest-tmp/modernization-before-20261124`
snapshot before editing. Unrelated application documents were left untouched.

The existing architecture remains FastAPI, SQLAlchemy/Alembic, React, TypeScript,
Tailwind, TanStack Query, Recharts and lazy-loaded Mapbox. Public HTML and
authentication remain served by FastAPI. No replacement framework is needed.

## Baseline verification

- Backend: `.venv/Scripts/python -m pytest -q` from `backend`: **451 passed,
  2 skipped**, 17 warnings, 247.24 seconds. Warnings include Alembic's legacy
  path splitting; skipped PostgreSQL coverage requires an isolated database.
- Frontend: `npm test -- --reporter=dot`: **71 passed**, 20 files, 33.14 seconds.
- Production build: `npm run build`: passed in 57.60 seconds, with existing
  local-font resolution and large lazy Mapbox chunk warnings.
- Screenshots: `node scripts/capture-modernization.mjs before` against isolated
  synthetic demo at port 8794. See
  [before capture manifest](images/modernization-20261124/before/audit.json).
  External requests were blocked, including map tiles. This is a local layout
  check, not evidence that hosted Google OAuth or paid map services work.

## Findings and implementation gates

1. Shared components already exist; extend them instead of introducing a second
   component library. Evidence badges overflow the two-column mobile KPI layout.
   Dark-mode base headings retain a dark forest color; buttons have small touch
   targets. Preserve the white canvas, forest identity, Manrope and DM Sans.
2. The public hero downloads external autoplay video even though licensed local
   photographs are available. Replace only its media; retain the approved headline,
   structure, reporting simulator and navigation. Existing photography credits
   remain authoritative; context photographs are not pilot-site evidence.
3. Overview has scheme, sector and rolling-period filters, source badges,
   priorities, recent activity, infrastructure condition and scientific yield
   eligibility. Extend actual scoped receipt statistics; never treat changes in
   reporting volume as agricultural impact or a validated scientific baseline.
4. GIS already supports standard/satellite/terrain views, recorded-coordinate
   markers, protected nutrition aggregation and an explicit token-free fallback.
   Missing rainfall is incorrectly converted to zero in the UI; fix that before
   extending layers. No invented points or household locations.
5. The newer local assistant already has chat controls, citations, expandable
   evidence, source selection and bounded memory. Preserve it. Native-language
   review and semantic-model prerequisites remain separate from UI polish.
6. Incident histories, climate forecasts, calibrated-threshold source fields,
   exports and role restrictions already exist; refine their presentation and
   regression coverage without duplicating business logic.

## Offline retrieval baseline

The 64-case engineering fixture is a development dataset, not an independent
agronomic validation. It contains 50 answerable cases and eight draft Kinyarwanda
cases. Results are in `docs/ai/modernization-{legacy,bm25}-20261124.json`.

| Method | Recall@3 | MRR | Abstention accuracy | Extractive citation accuracy |
| --- | ---: | ---: | ---: | ---: |
| Legacy lexical | 0.83 | 0.82 | 0.429 | 1.00 |
| BM25 lexical | 0.83 | 0.83 | 1.00 | 1.00 |

BM25 English Recall@3 is 0.940; draft Kinyarwanda Recall@3 is 0.250. Citation
accuracy measures retrieved quotations, not the truth of agricultural advice.
No generated-answer unsupported-claim rate can be inferred from this extractive
benchmark. Semantic/hybrid results require an approved, pinned local embedding
model; do not label lexical fallback results as semantic retrieval. External
generation, live messaging, ingestion and uploads are disabled in this audit's
isolated preview. No production data or credentials are changed.

## Implemented changes

The approved public information architecture, hero headline, navigation, pilot
descriptions, footer and feature-phone demonstration remain. The hero and dashboard
banner now use an existing local landscape photograph. The unverified LIVE ticker
is removed; the public feed describes received report summaries, labels demonstration
figures, and does not announce pilot activation merely because an API responds.
Supporting text has stronger contrast, and the demo's pause control is no longer
inside an `aria-hidden` container. This is a refinement of the existing site.

The dashboard retains white surfaces and forest branding. Shared cards contain
narrow content; evidence badges wrap; controls have larger mobile targets; focus
rings and base headings adapt to each theme. Dark chart labels, tooltips and map
popups use theme colors. Charts with equivalent accessible data tables no longer
create keyboard stops inside their decorative `aria-hidden` wrappers.

**Reporting activity and evidence** adds Rwanda-calendar date windows, cell and
staff-only cooperative filtering on top of selected sector/scheme filters. It
compares equal-length receipt periods and shows verified and located report counts.
Simulator, demo and superseded rows are excluded. Selection intersects the viewer's
area; cooperative filters follow the existing directory's role/404 area rules.
Current membership is explicit. These controls affect this panel, not current-state
asset conditions. The implementation does not invent a scientific baseline.

GIS retains standard/satellite/terrain controls. Recorded sector/cell boundaries
can be drawn from the existing endpoints; nearby crop reports cluster and expand;
point details support touch. A paginated observation table and name/status search
work without tiles. Missing rainfall and risk scores stay missing rather than
becoming zero. Protected nutrition aggregation and recorded-coordinate requirements
are preserved. No point, infrastructure inventory or boundary has been invented.

The newer local assistant remains intact. Main prompts, suggestions, evidence-mode
labels, input/feedback controls and messages use shared EN/RW dictionaries. Source
selection, chat memory bounds, document review and authorization are preserved.
Incident events are chronological, with recorded actors and Kigali timestamps;
history errors have a retry instead of implying there is no history. Climate
coverage separates gauge readings, forecast estimates and missing gauge evidence.

All API responses now use `Cache-Control: private, no-store`. No service worker or
private-record offline cache is introduced. Hashed static assets retain long-lived
caching. A PWA with private offline records is deliberately not enabled on shared
devices; an installable/public-shell-only PWA needs a separate acceptance review.

## Actual verification

| Check | Executed command / scope | Result |
| --- | --- | --- |
| Backend | `.venv/Scripts/python -m pytest -q` from `backend` | **458 passed, 2 skipped**, 17 warnings, 270.79 s |
| Frontend | `npm test -- --reporter=dot` | **76 passed**, 23 files, 68.54 s |
| Browser workflows | `PYTHON=../.venv/Scripts/python npm run e2e` | **34 passed**, 1 optional local-model test skipped, 3.4 min |
| Types, lint, production build | `npm run typecheck`, `npm run lint`, `npm run build` | Passed; final build 26.30 s |
| SQLite migrations | Included in full backend suite | Passed |
| Isolated PostgreSQL/PostGIS | Alembic to `20261117_30`, `scripts/schema_audit.py` | **36 model tables** matched; no missing/extra model columns |
| PostgreSQL knowledge lifecycle | `pytest tests/test_rag_postgres.py -q` on disposable database | **1 passed, 1 skipped**; pgvector unavailable |
| npm advisory audit | `npm audit --json` against final lockfile, all dependency scopes | **0 known vulnerabilities** |
| Python advisory audit | Isolated pip-audit against `.venv/Lib/site-packages` | **56 packages**, **0 advisory entries** |
| Responsive screenshots | `node scripts/capture-modernization.mjs after` | **64 captures**, no capture errors, uncaught page errors, visible error alerts or horizontal overflow |
| Automated accessibility | `node scripts/check-modernization.mjs`, WCAG 2/2.1/2.2 A/AA tags | **15 public/authenticated page/theme checks, 0 violations** |
| Public links | Same browser check, local links and anchors | **13 checked, 0 broken** |

The backend skips in the ordinary run require a dedicated PostgreSQL URL. The
additional isolated run exercised knowledge migration/ACL/deletion on PostgreSQL;
its exact-distance pgvector test remains skipped. The optional model browser test
was not activated. No paid or external generation was used. Existing Alembic path
splitting and Starlette/httpx deprecation warnings remain; they are not test failures.

The Vitest upgrade initially exhausted test deadlines with automatic concurrency
(17 failures, mostly timeouts). Bounding **isolated workers to two** made all tests
pass with the original assertions and timeouts. No meaningful test was removed or
weakened. The first visual scan found text contrast, hidden focus and scroll-region
focus issues; these were corrected and the final scan is recorded separately.
Automated checks do not constitute a complete manual WCAG certification.

Dependency remediation includes compatible transitive updates, Vite 6.4.6,
React Router 7.18.6, Zod 4.6.7 and Vitest 5.1.1. Router v7 behavior was already
opted into; obsolete future flags were retired. Zod records now specify key schemas,
and API type signatures use v4's types. Python uses pytest 9.2.0, certifi 2026.11.20,
pyasn1 0.6.5 and opentelemetry-api 1.45.2. Requirements include security floors for
declared/transitive application dependencies; OpenTelemetry was an existing local
environment package, not added as an application dependency. Advisory results are
dated observations, not guarantees about future advisories or hosted resolutions.

See [machine-readable verification](modernization-verification-20261124.json),
[responsive manifest](images/modernization-20261124/after/audit.json) and
[accessibility/link results](images/modernization-20261124/after/quality.json).

## Screenshots and photography

There are **49 baseline captures** and **64 after captures**. Desktop covers all
19 classic/public pages and all 18 React workspaces; after captures include every
React workspace at 360 px, plus key public/auth/dashboard views at 768 px.
Desktop width is 1440 px. Dark and RW examples are additional captures.

Open the [comparison gallery](images/modernization-20261124/index.html) or
[desktop review sheet](images/modernization-20261124/desktop-review.jpg).

| View | Before | After |
| --- | --- | --- |
| Public website | [Before](images/modernization-20261124/before/public.jpg) | [After](images/modernization-20261124/after/public.jpg) |
| Executive dashboard | [Before](images/modernization-20261124/before/app-.jpg) | [After](images/modernization-20261124/after/app-.jpg) |
| Dashboard, 360 px | [Before](images/modernization-20261124/before/app--360.jpg) | [After](images/modernization-20261124/after/app--360.jpg) |
| Assistant, 360 px | [Before](images/modernization-20261124/before/app-assistant-360.jpg) | [After](images/modernization-20261124/after/app-assistant-360.jpg) |
| Map workspace | [Before](images/modernization-20261124/before/app-map.jpg) | [After](images/modernization-20261124/after/app-map.jpg) |
| Climate workspace | [Before](images/modernization-20261124/before/app-climate.jpg) | [After](images/modernization-20261124/after/app-climate.jpg) |

The hero reuses `landscape-1200.webp` / `landscape-640.webp`: Baloona's **Farm outside
of Kigali, Rwanda**, credited in the existing [photography page](../dashboard/photography.html)
as CC BY-SA 4.0, with its [original source record](https://commons.wikimedia.org/wiki/File:Farm_outside_of_Kigali,_Rwanda.jpg).
It is contextual Rwanda imagery, not a verified Bugesera pilot site. Existing
photography credits and context notices remain; no new stock image, institution,
participant identity or endorsement is invented.

## Performance and localization limits

Two external autoplay video sources were replaced with responsive local media:
the hero image is **232,110 bytes** at 1200 px or **62,938 bytes** at 640 px.
This avoids video requests and playback; the baseline browser blocked external
requests, so no measured video-bandwidth saving is claimed. Mapbox remains lazy:
the token-free capture run requested **no Mapbox SDK chunk**. Its configured-map
chunk still costs about **1,912.89 kB / 540.14 kB gzip**. This warning remains.

Initial application JS grew from **389.04 kB / 116.03 kB gzip** to approximately
**456.20 kB / 139.60 kB gzip**, reflecting new functionality and dependency security
upgrades. Do not describe this as a bundle reduction. Local-font URL build warnings
remain; the font files are copied to the build and served locally at runtime.
No production Lighthouse/Core Web Vitals or configured-map performance score is
claimed from this isolated, externally blocked browser run.

The [keyed React native-review pack](modernization-native-review-20261124.json)
contains **761 entries**, including **659 without RW drafts**. The
[source-located UI review](modernization-ui-review-20261124.json) lists **240 additional
React copy candidates**. These are review work queues, not approved translations.
The public page also has a separate existing draft RW dictionary; its changed
activity wording needs native review. Brand names/data values may remain unchanged.
The language switcher and new main assistant controls work locally, but the whole
platform is not certified fully translated. Preserve placeholders and require a
named reviewer/evidence reference before applying an approved review pack.

## Retrieval assessment and remaining validation

The final BM25 rerun is [recorded here](ai/modernization-bm25-after-20261124.json)
and preserves Recall@3 **0.83**, MRR **0.83**, and extractive citation accuracy
**1.00**. On the **14 negative fixtures**, legacy retrieval returned document mode
in **7 cases (50%)**; BM25 did so in **0 (0%)**. This measures unsupported lookup
responses on those fixtures, not generated-answer hallucination. Actual model
faithfulness/unsupported-claim rates remain unmeasured because generation is off.
The engineering corpus is not an approved agricultural advisory library, and the
previously seen development/holdout fixtures are not independent scientific validation.

Semantic/hybrid benchmarking is not justified as a reported result until an approved,
pinned embedding model/runtime is available. `sentence_transformers` is absent;
no model was downloaded and no external embedding request was made. Existing optional
vector adapters and approved-source controls remain; a synthetic vector unit test
must never be presented as a real semantic-retrieval benchmark.

Institutional/field gates remain: official crop/season/area baselines and source
approval; verified sector/cell geometry and recorded infrastructure coordinates;
native-language acceptance; gauge calibration and agronomist approval; pilot and
carrier/device acceptance; configured satellite/tile and hosted Google OAuth checks;
hosted CI/staging and release verification. Local map fallback checks do not validate
live satellite imagery or prove that missing field inventories exist. Live telecom,
airtime, production data changes, external model transmission and production deployment
were not activated. No field outcomes or causal impact are claimed.

## Modified files and reproduction

The [file manifest](modernization-modified-files-20261124.json) distinguishes changes
from the preserved baseline. Of the 51 pre-existing project files, **46 remain byte
identical**; five were extended: README, assistant documentation, AssistantPage,
its tests and the English dictionary. Unrelated application documents remain untouched.

| Area | Main files | Rationale |
| --- | --- | --- |
| Shared design | React/legacy tokens, `styles/index.css`, `Card`, `Badge`, `Button`, `RainfallPanel` | Containment, touch targets, contrast, theme/focus behavior |
| Public | `dashboard/index.html`, `landing.css`, `landing.js` | Local imagery, truthful activity labels, readable copy, accessible demo |
| Reporting | `services/reporting_activity.py`, analytics route, `ReportingActivity` and tests | Scoped date/membership comparisons and evidence counts |
| GIS | `DistrictMap`, `MapPage`, observation parser and tests | Recorded boundaries, crop clustering, missing-value handling, searchable text alternative |
| Assistant/localization | Existing AssistantPage/tests, `i18n/assistant.ts`, EN/RW dictionaries, translation exporter/tests | Reuse chat work; add draft bilingual controls and review provenance |
| Incident/climate/charts | `WorkItemDrawer`, `ClimatePage`, `RainfallChart`, `SchemeChart`, `TrendChartView` | Actual timelines, data coverage, accessible decorative charts |
| Security/compatibility | API cache middleware, requirements, package/lock files, API/schema helpers, router entry/test wrapper | Advisory remediation, private caching, library compatibility |
| Reproducible QA | Preview runner, capture/quality/gallery/review scripts | Isolated data, screenshots, accessibility, source-located review |
| Documentation | README, design system, roadmap, workspaces, assistant docs and this report | User guidance, results, limitations, PR summary |

From the repository root, run `.venv/Scripts/python backend/scripts/run_modernization_preview.py`
to open a **new isolated synthetic** platform on `http://localhost:8794`.
Fixture sign-in: `admin@e2e.test` / `e2e-password-2026`. These are local test accounts,
not production credentials. Normal local data is not opened. Ingestion, generation,
live messaging, weather and map credentials remain disabled. Stop it with Ctrl+C.
From `frontend`, run the capture/quality/gallery commands shown above. Use the
ordinary platform start scripts for normal development data, not this disposable preview.

See [pull request summary](modernization-pr-summary-20261124.md). Changes remain
local on the feature branch; no push, merge, hosted CI run or deployment is claimed.
