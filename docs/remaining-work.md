# Remaining-work register

Status of the modernization brief. **Implemented** means code exists. **Tested** means automated tests cover it. **Blocked** means it needs something outside the repository. **Field validation** means it works technically but must be proven with people in Bugesera. Updated at the end of Phase 2 (October 2026).

## Done

### Foundation and security (Round 1)

| Item | Implemented | Tested | Notes |
| --- | --- | --- | --- |
| Audit of the existing system | Yes | n/a | [audit-2026-10.md](audit-2026-10.md) |
| Missing `slowapi` dependency | Yes | CI clean install | |
| Account approval for self-registration | Yes | Unit + end-to-end | Approve in Administration → Accounts |
| Gateway callback secret, per-phone throttle, proxy headers | Yes | Yes | |
| Simulator on signed-in endpoints, never reaching a provider | Yes | Unit + end-to-end | |
| Grievance anonymity | Yes | Unit + end-to-end | Timing caveat in [security.md](security.md) |
| Phone masking, staff-only household records | Yes | Unit + end-to-end | |
| Production guard, security headers | Yes | Yes | |
| `data_origin` and simulator exclusion from every figure | Yes | Yes | Monthly report and trends fixed in Phase 2 |

### Phase A — migrations and CI

| Item | Implemented | Tested | Notes |
| --- | --- | --- | --- |
| Deterministic migrations (frozen baseline, explicit tables) | Yes | SQLite: fresh, upgrade-with-data, downgrade | `backend/tests/test_migrations.py` |
| Case assignments point at platform accounts | Yes | Yes | Migration `20261011_17` |
| Report verification and audit log | Yes | Yes | Migration `20261011_18` |
| Schema-versus-model check | Yes | SQLite and PostGIS, enforced in CI | Verified locally on a clean PostGIS 3.6 server: upgrade, 0 differences, downgrade/upgrade, seeds |
| CI jobs: backend, PostGIS migrations, frontend, browser end-to-end, Docker | Yes | Backend, frontend and Docker green on GitHub | The first PostGIS and end-to-end runs failed (fixed in "Fix the PostGIS migrations and the CI end-to-end start"); awaiting the rerun |

### Phase B — UX foundation

| Item | Implemented | Tested |
| --- | --- | --- |
| Design tokens, typography, focus ring, reduced motion | Yes | Visual checks |
| Shell: collapsible sidebar, phone drawer, breadcrumbs, Ctrl+K page search, notification list, account menu, freshness | Yes | Unit + end-to-end |
| Access levels matching the backend roles; role-aware start page | Yes | Unit + end-to-end |
| Button, Drawer, Dialog, Toast, form fields, DataTable, badges, BarList, PageHeader, error boundary per page | Yes | Unit |
| No horizontal scrolling at 390 px on every page | Yes | Browser check of all 16 pages |

### Phases C–G — workspaces

All pages are described in [workspaces.md](workspaces.md).

| Workspace | Implemented | Tested |
| --- | --- | --- |
| Priority actions (assign, deadline, action, history, previewed closing-the-loop SMS) | Yes | Unit + end-to-end |
| Field reports (quality checks, verification, CSV export, masking) | Yes | Unit + end-to-end |
| Crops & pests | Yes | Browser check |
| Food & nutrition (five-household rule) | Yes | Unit + end-to-end (notice) |
| Irrigation command centre (latest status, history, never-reported assets) | Yes | Backend + browser check |
| Climate & advice (thresholds with source, previewed send) | Yes | End-to-end |
| District map (Mapbox layers, privacy rules) | Yes | Browser check; end-to-end without a token |
| PADAB & APEFA evaluation (five questions, no invented outcomes, CSV, print) | Yes | Backend + unit + end-to-end |
| Grievances | Yes | End-to-end |
| Cooperatives (participation, training, add/edit) | Yes | Browser check |
| USSD & SMS operations | Yes | End-to-end |
| Phone simulator | Yes | Unit + end-to-end |
| Trends, monthly report | Yes | End-to-end |
| Administration (approval, roles, areas, scheme baselines, audit log) | Yes | Unit + end-to-end |

### Phases H–I — quality and documentation

| Item | Status |
| --- | --- |
| Backend tests | 144 passing |
| Frontend unit tests | 49 passing; type check and lint clean |
| Browser end-to-end tests | 10 workflows (14 tests, plus 5 sign-in setups), passing twice in a row locally; see [testing.md](testing.md) |
| Documentation | [workspaces.md](workspaces.md), [testing.md](testing.md), user guide, design system, security, data model and README updated |

## Not built, and why

| Item | What it needs |
| --- | --- |
| Crop distribution by season and seasonal comparison | Crop and season recorded on every harvest report |
| Asset downtime durations and a maintenance log | A maintenance table and agreement on how repairs are recorded |
| Rainfall anomaly against a reference period | A historical rainfall series for Mwesa Valley and Ngeruka/Mareba |
| SMS delivery states and callback errors | Provider delivery reports (blocked on live credentials) |
| Advisory model by crop, growth stage and soil | Agronomist-approved rules; advice is labelled as using starting thresholds |
| Data-quality scoring beyond the automatic checks | Agreement on what makes a valid report |
| Uncertainty indicators | Sample sizes are shown as counts for now |
| Grievance category management and asset inventory editing in `/app/` | Still in the classic Management page (`/management.html`) |
| Dark mode, Content Security Policy | After the classic pages are retired |

## Scientific evaluation

| Item | Status | What is needed |
| --- | --- | --- |
| Yield achievement (`100 × observed ÷ target`) | **Deliberately not calculated** | Harvested area, crop and season on each harvest report; each scheme target per crop, unit (t/ha) and season. The evaluation page lists each missing requirement |
| Rainfall anomaly | Not started | Historical rainfall |
| Response-time statistics | Median days to resolve | |

## Blocked outside the repository

| Item | Blocked on |
| --- | --- |
| Live SMS and airtime | Africa's Talking production credentials and an approved short code |
| Official PADAB/APEFA baselines | Feasibility-study documents entered with their sources (Administration → Scheme baselines) |
| Calibrated irrigation thresholds | Historical rainfall records and an agronomist's approval |
| Data protection impact assessment and registration | The district (Law N° 058/2021) |

## Needs field validation

- **Kinyarwanda for the new pages.** About 440 new interface strings exist in English only (`frontend/src/i18n/en.workspaces.ts`); with RW selected they fall back to English. They need translation and review by native-speaking field staff before the pilot. USSD screens are already in Kinyarwanda.
- The USSD flow on real feature phones with one cooperative.
- Whether the pages answer the questions District Planners actually ask (a working session with planners).
- Showing individual crop-report locations on the map: households and grievances are never mapped, but the district should confirm crop-report points are acceptable.
- The account approval workflow in daily district use.

## Known gaps

- `/analytics/farmer-summary` returns fixed zeros for schemes, complaints and assets; only classic pages use the older summaries.
- **Fresh databases.** Grievance categories and the asset inventory are created by the demonstration seed only. A new production database needs them entered (classic Management page) or a reference seed script; until then USSD uses its built-in lists.
- **Area-limited accounts** see their own sectors' records; district totals, trends and the monthly report stay district-wide. Decide which behaviour the district wants.
- Reads of personal data on screen are not audited (changes and exports are).
