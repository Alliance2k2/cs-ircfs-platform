# Remaining-work register

Status of the modernization brief, kept honest: **Implemented** means code exists, **Tested** means automated tests cover it, **Blocked** means it needs something outside the repository, and **Field validation** means it works technically but must be proven with people in Bugesera. Updated at the end of Round 1 (October 2026).

## Round 1 — done

| Item | Implemented | Tested | Notes |
| --- | --- | --- | --- |
| Audit of the existing system | Yes | n/a | [audit-2026-10.md](audit-2026-10.md) |
| Missing `slowapi` dependency | Yes | CI clean install | Docker/Render builds crashed without it |
| Account approval (pending self-registration) | Yes | Yes | Approve in Platform Management → Accounts |
| Gateway callback secret and optional IP allow-list | Yes | Yes | Callback URLs must carry `?token=` |
| Per-phone throttle for callbacks; proxy headers | Yes | Yes | |
| Simulator on signed-in endpoints, never reaching a provider | Yes | Yes | |
| Grievance anonymity in message logs | Yes | Yes | Timing caveat in [security.md](security.md) |
| Phone masking and staff-only household records | Yes | Yes | |
| Stricter production guard; security headers | Yes | Yes | |
| `data_origin` (field / simulator / demo / import) | Yes | Yes | Migration `20261010_16`, tested on SQLite; PostGIS run is in CI |
| Assets down from the latest report per asset | Yes | Yes | |
| Executive overview API with metric envelopes | Yes | Yes | `/api/v1/analytics/executive-overview` |
| React foundation: tokens, shell, i18n, data states | Yes | Yes (Vitest) | `frontend/` |
| Executive Dashboard screen at `/app/` | Yes | Yes (Vitest) + screenshots | Desktop and phone width checked |
| CI: backend tests, PostGIS migrations, frontend checks, Docker build | Yes | Not yet run | First run happens when the branch is pushed |
| Multi-stage Docker image with the React build | Yes | Not built locally | Docker is not installed on the development machine; CI builds it |

## Workspaces still to build (brief §7)

Each will reuse the shell, tokens, metric envelopes and data states from Round 1. Until then the sidebar links to the classic page.

| Workspace | Classic page today | Next step |
| --- | --- | --- |
| A. Citizen science | `channels.html`, Management → Citizen reports | Report history, contributor participation, suspicious-submission flags (needs rules agreed with the district) |
| B. Crop intelligence | `map.html` (pest heatmap), `schemes.html` | Crop distribution and seasonal comparison; needs crop and season on every harvest report |
| C. Irrigation command centre | `act-now.html`, `schemes.html` | Asset register with downtime from latest-status history, maintenance log (new table) |
| D. Climate intelligence | `advice.html` | Rainfall anomaly against a reference period (needs historical rainfall) |
| E. Food and nutrition | `nutrition.html` | Aggregate-only views; screening wording reviewed with a nutritionist |
| F. PADAB / APEFA evaluation lab | `schemes.html` | See "Scientific evaluation" below |
| G. Community voice | `feedback.html` | Rebuild on the existing workflow API |
| H. Geographic intelligence | `map.html` | PostGIS layers from `data/*.gpkg` |
| I. USSD and SMS operations | `simulator.html`, `channels.html` | Delivery states and callback errors need provider delivery reports (blocked on live credentials) |
| J. Cooperatives and field teams | `cooperatives.html` | Rebuild on the existing cooperative API |
| K. Analytics and reports | `trends.html`, `report.html` | CSV export with source labels |
| L. Administration | `management.html` | Account approval queue, audit-log viewer |

## Scientific evaluation (brief §8–9)

| Item | Status | What is needed |
| --- | --- | --- |
| Yield achievement (`100 × observed ÷ target`) | **Deliberately not calculated** | Each harvest report needs harvested area, crop and season; each scheme target needs crop, unit (t/ha) and season. Then the formula is valid. The classic Scheme performance page still shows the sample-over-target percentage, now labelled "sample, not verified", until it is retired |
| Rainfall anomaly | Not started | A historical rainfall series for Mwesa Valley and Ngeruka/Mareba |
| Advisory model (crop, growth stage, soil, forecast) | Not started | Agronomist-approved rules; until then advice is labelled as using starting thresholds |
| Data-quality scoring, missing-data diagnostics | Not started | Agreement on what counts as a valid report |
| Response-time statistics | Partly (median days to resolve) | |
| Uncertainty indicators | Not started | Sample sizes are shown as notes for now |

## Blocked outside the repository

| Item | Blocked on |
| --- | --- |
| Live SMS and airtime | Africa's Talking production credentials and an approved short code |
| Official PADAB/APEFA baselines | Feasibility-study documents entered with their sources |
| Calibrated irrigation thresholds | Historical rainfall records and an agronomist's approval |
| Data protection impact assessment and registration | The district (Law N° 058/2021) |

## Needs field validation

- Kinyarwanda USSD screens and interface text (native-speaker review).
- The USSD flow on real feature phones with one cooperative.
- Whether the executive overview answers the questions District Planners actually ask (a session with planners).
- Approval workflow for new accounts in daily district use.

## Known gaps in this round

- Area-limited accounts see their own sectors' figures on the executive overview (records are scoped); the classic pages keep district-wide totals. Decide which behaviour the district wants.
- The Content Security Policy is deferred until the classic pages are retired.
- End-to-end browser tests (Playwright) are not set up yet; the React screens are covered by component tests and manual screenshots.
- Dark mode is not started (the brief puts it after a mature light theme).
