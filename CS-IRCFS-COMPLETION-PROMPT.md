# CS-IRCFS: completion prompt

Use this prompt with an AI coding agent working inside this repository. It describes everything still missing between the CS-IRCFS concept and the current code, in the order it should be built.

---

## 1. Your role and goal

You are a senior full-stack engineer finishing **CS-IRCFS** (Citizen Science for Irrigation Resilience and Climate-smart Food Security), a platform for Bugesera District, Rwanda.

- Farmers and Citizen Science Monitors report from feature phones by **USSD `*801#`** and **SMS `8448`**, in Kinyarwanda first.
- District Planners use a web dashboard to check whether two irrigation investments delivered their promised outcomes, and to act where they fall short:
  - **PADAB**, Mwesa Valley: AfDB-funded, 650 ha, 2 pumping stations, 65.5 km of canals.
  - **APEFA Solar**, Ngeruka and Mareba sectors: solar-powered irrigation.

Most of the platform already works. Your job is to build the remaining features, add the tooling for real-world calibration data, harden the platform for a pilot, and prepare the documentation deliverables. Work in the existing code; do not rewrite or restructure what already works.

## 2. What already exists (do not rebuild)

**Backend** (`backend/`): Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, PostgreSQL + PostGIS in production, SQLite for local development.

- `app/services/ussd.py`: the `*801#` menu, Kinyarwanda and English, six options (harvest, pests, rainfall, infrastructure, grievance, household nutrition), numbered choices, at most three levels.
- `app/services/sms_keywords.py`: SMS 8448 keywords `NZANA`, `INDWARA`, `IMVURA`, `UMUSARURO`, `IKIBAZO`, with an optional sector name for location.
- `app/services/advisory.py`: irrigation advice from 7-day rain-gauge totals (`DRY_SPELL_THRESHOLD_MM`, `WET_SPELL_THRESHOLD_MM`), local tips, and `maybe_reward()`, which pays airtime every 3 rainfall or infrastructure reports.
- `app/services/forecast.py`: 7-day rain forecast from Open-Meteo.
- `app/services/sms.py`: Africa's Talking SMS and airtime, plus a `dry_run` provider.
- `app/services/analytics.py`: dashboard summary, Act Now queue, scheme performance against yield targets, recurring-bottleneck auto-flagging, response health, nutrition summary, trends and the monthly report.
- Cases and grievances: assign, resolve, history, and a closing-the-loop SMS to the affected cell.
- Two separate people systems: `FieldUser` (USSD/SMS callers) and `PlatformAccount` (web staff). Never mix them up.
- Rate limiting, cookie and Bearer sessions, area-level access by sector, and 42 passing tests in `backend/tests/`.

**Dashboard** (`dashboard/`): plain HTML, CSS and JavaScript, served by FastAPI. No build step. Bootstrap 5.3 and Bootstrap Icons are stored locally in `assets/vendor/`.

- **Public pages:** `index.html` (live map, live counts), `login.html`, `register.html`.
- **Dashboard pages:** each is a separate page and all use `assets/js/app.js`, which reads `<body data-page>`:
  - `planner.html` (overview), `act-now.html`, `channels.html`, `schemes.html` (with an add/edit scheme form), `trends.html`
  - `advice.html`, `nutrition.html`, `map.html`, `feedback.html`
- **Other pages:** `management.html` (data tables per module), `report.html`, `simulator.html` (phone simulator), `backend-console.html`.
- **Shared shell:** `assets/js/app-shell.js` builds the sidebar, top bar and footer from one `GROUPS` list. `dashboard/README.md` explains how to add a page.
- **Styles:** `assets/css/app-shell.css` (shell), `assets/css/dashboard-theme.css` (components), `assets/css/bootstrap-theme.css` (Bootstrap in brand colours).

**Ops:** `Dockerfile`, `start-local.ps1` (`-Demo` loads demonstration records into `backend/demo.db`), and `docs/` (architecture, data model, deployment, user guide).

## 3. Ground rules

1. **Read before you change.** Open the files you touch, follow their style, and reuse existing helpers (`apiJson`, `escapeHtml`, `toast`, `emptyState`, `setText`, the shell skeleton, the design tokens).
2. **No mock or sample data in any page.** Every figure comes from the API. When there is no data, show an honest empty state.
3. **Never invent real-world figures.** Yield targets, rainfall thresholds, asset lists and AfDB findings must come from documents the user supplies. Build the import tools and forms; leave the values for the user to enter. Mark anything unconfirmed as "to verify".
4. **Database changes:** every model change needs an Alembic migration that works on both SQLite and PostgreSQL/PostGIS, plus an update to `docs/data-model.md`.
5. **Tests:** add or extend tests in `backend/tests/` for every backend change. Keep the whole suite passing (`python -m pytest -q` in `backend/`).
6. **Kinyarwanda first.** Every new USSD or SMS text needs Kinyarwanda and English versions. Keep USSD menus at most 3 levels deep, use numeric choices, and keep each screen to 9 options or fewer and under 160 characters where possible. Add a comment `# RW: needs field review` next to new Kinyarwanda strings.
7. **Respect roles.**
   - District Planners, officers and administrators act on data.
   - Citizen Science Monitors read only.
   - Scheme edits are for administrators.
   - Keep the area-level (sector) filtering on every new query.
8. **Configuration over hard-coding.** New behaviour switches go in `app/core/config.py` and `.env.example`, with safe defaults. Anything that sends SMS or airtime must respect `SMS_PROVIDER=dry_run` and `AIRTIME_PROVIDER=dry_run`.
9. **Do not delete user files**, git stashes or branches, and do not commit or push, unless the user asks. List what you would remove and ask.
10. **Keep changes small and reviewable.** Finish one work package, run the tests, summarise, then move on.

## 4. Work packages

Each package lists what to build, where, and how to know it is done.

### WP1. Yield forecaster inputs (Module 1, Objective 1)

**Gap:** the USSD harvest flow records only crop and expected tons. The concept also needs planting date, crop variety and harvest timing, logged monthly.

- Add to the crop report model: `crop_variety` (nullable short text) and `expected_harvest_month` (nullable date or month). Fill the existing `planting_date`. Write the migration.
- Extend the USSD harvest flow (`ussd.py`) within the 3-level rule. Suggested flow:
  1. crop
  2. variety (short numbered list per crop, plus "Other / ntazi")
  3. planting month (numbered relative choices such as "this month", "last month", "2 months ago", "3+ months ago")
  4. weeks until harvest (numeric)
  5. expected tons (numeric)
- Add a matching SMS form, for example `UMUSARURO IBIGORI 2.5 UKWEZI 3`. Keep the old keyword form working.
- Keep variety lists in one data structure that is easy to edit, preferably the database table from WP7.
- **Dashboard:**
  - `schemes.html`: show planting and expected-harvest timing per scheme (for example a small "expected harvest by month" chart).
  - `trends.html`: add a "planting updates per month" series.
- Simulator: make sure the new screens work there and show English translations.
- **Done when:** a monitor can log crop, variety, planting month, harvest timing and tons by USSD and SMS; the records appear in Management → Citizen reports and on the scheme page; tests cover every step and every invalid input.

### WP2. Automatic irrigation advice (Module 2)

**Gap:** advice is sent only when a planner presses "Send advice". The concept says the system sends it automatically.

- Add `scripts/send_weekly_advice.py`. It reuses the existing advisory send logic, can run from cron, Windows Task Scheduler or a container, and exits with a clear summary.
- Optionally add an in-process scheduler controlled by settings: `ADVICE_SCHEDULE_ENABLED=false`, `ADVICE_SCHEDULE_WEEKDAY=mon`, `ADVICE_SCHEDULE_TIME=06:00` (Africa/Kigali). A lightweight library such as APScheduler is fine; note it in `requirements.txt`.
- **Idempotent:** never send the same week's advice to the same sector twice. Record each run (week key, sectors, recipients, provider status) so it can be audited.
- **Dashboard** (`advice.html`): show "Last automatic send: date · N recipients" and the next scheduled run. Keep the manual button.
- **Done when:** running the script twice in one week sends once; dry-run mode records without sending; tests cover idempotency and the no-readings case.

### WP3. Seasonal forecast (optional data source)

**Gap:** only a 7-day Open-Meteo forecast is used. The concept refers to seasonal forecasts.

- Create a small provider interface in `forecast.py` (`seven_day`, `seasonal`).
- Add a seasonal provider that reads a CSV or JSON bulletin the district uploads (for example from Meteo Rwanda: season, sector or zone, expected rainfall category). Add an upload or import script; do not scrape websites.
- Use the seasonal outlook in the advice text when available ("Season outlook: below normal rain"), and show it on `advice.html`.
- **Done when:** with no bulletin loaded nothing changes; with one loaded, advice and the advice page include it; tests cover both.

### WP4. Nutrition survey incentive

**Gap:** airtime is paid only for rainfall and infrastructure reports. The concept calls nutrition surveys "incentivized".

- Generalise `maybe_reward()` so the counted report types come from settings, for example `INCENTIVE_REPORT_TYPES=rainfall,infrastructure,nutrition`, keeping the current default behaviour.
- Pay the reward in the USSD nutrition flow and show it in the reply, as the rainfall flow does.
- Prevent abuse: at most one rewarded nutrition survey per household per month (`INCENTIVE_NUTRITION_PER_MONTH=1`).
- **Done when:** a household completing its survey earns airtime under the rules; repeats in the same month do not; Management → SMS log and the airtime totals show it; tests cover the rules.

### WP5. Cooperatives, Data Champions and the pilot (Section 8, Objective 5)

**Gap:**
- the cooperative is only a free-text name on a field user
- there is no Data Champion designation
- there is no participation ranking for the monthly Inteko z'Abaturage meetings
- there is no tracking of the target of 200 trained monitors, and no view of the 3 pilot cooperatives

**Data model and migration:**
- Add a `cooperatives` table: name (unique), sector, irrigation scheme, `is_pilot`, contact field user.
- Add `cooperative_id` on field users. The migration should create cooperatives from existing `cooperative_name` values and link them; keep the old column readable until the migration is confirmed.
- Add to field users: `is_data_champion`, `trained_at` (date), `training_notes`.
- Add settings `MONITOR_TRAINING_TARGET=200` and `PILOT_COOPERATIVE_TARGET=3`.

**API:**
- CRUD for cooperatives (planners and administrators).
- A participation endpoint: per cooperative, over the last 30 days and month to date, return reports by type, active reporters, Data Champions and the last report date.
- A training-progress endpoint: monitors trained against the target.

**Dashboard:**
- Add a new page `cooperatives.html` with `data-page="cooperatives"`:
  - add it to `GROUPS` in `app-shell.js` and to `NEEDS` in `app.js`
  - a photo header, and a ranking table and bar chart of cooperative participation
  - a pilot-cooperatives panel, and a progress bar towards 200 trained monitors
  - a "print for Inteko z'Abaturage" layout that hides the shell when printed
- Add a Cooperatives module to `management.html`, and Data Champion and training fields to the Users form.
- Add a "Cooperative participation" section to the monthly report.

**Done when:** an administrator can create cooperatives, mark pilots and Data Champions and record training; the ranking and progress update live from real records; tests cover the ranking maths and permissions.

### WP6. Twilio SMS provider (optional)

- Add `SMS_PROVIDER=twilio` next to `africas_talking` and `dry_run` in `services/sms.py`, with settings `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`.
- Add a Twilio inbound SMS webhook that maps to the same keyword handler, with signature validation.
- Note in the docs that Twilio has no USSD in Rwanda; USSD stays with Africa's Talking.
- **Done when:** switching providers changes only configuration; tests mock both providers.

### WP7. Calibration tooling (Section 9). Build tools; do not invent values.

**Yield targets (PADAB, APEFA):**
- Add `scripts/import_scheme_targets.py`. It reads a CSV (scheme, yield target in tons, hectares, source document and page) and refuses rows without a source.
- The existing "Manage schemes" form on `schemes.html` is the manual route.
- Make the scheme page warn clearly while any target source still says "DEMONSTRATION VALUE".

**Rainfall thresholds per sector:**
- Add an `advisory_thresholds` table (sector, dry mm, wet mm, source, valid from). It overrides the `.env` defaults per sector.
- Add `scripts/calibrate_rainfall_thresholds.py`. It reads historical daily rainfall CSVs (Mwesa Valley, Ngeruka, Mareba), computes rolling 7-day totals, and proposes dry and wet thresholds from configurable percentiles (default 20th and 80th). It writes a report (`docs/calibration/rainfall-thresholds.md`) and only saves to the database with `--apply`.

**Bottleneck flagging:**
- Make the recurring-bottleneck rule configurable (window in days, minimum count, minimum share, per category).
- Add `scripts/import_bottleneck_baseline.py` for historical AfDB evaluation findings (scheme, asset, category, date, description). Use the baseline to set initial per-category thresholds, and show "above historical baseline" on the scheme page.

**Grievance categories and asset inventory:**
- Move both from constants in `ussd.py` into tables: `grievance_categories` (Kinyarwanda and English labels, sort order, active) and `scheme_assets` (scheme, asset name in both languages, type, active).
- Seed them with today's values. The USSD menus read from the database (paginate if more than 9).
- Add Management modules to edit both.

**Done when:** every calibration value can be loaded from a document without code changes, each has a recorded source, and the dashboard shows which values are still unverified.

### WP8. Production locations and geodata

- Check that `scripts/load_locations.py` loads all 15 Bugesera sectors and their cells, with boundaries, into PostGIS. Document the source dataset and the exact command in `docs/deployment.md`.
- Give each sector a centroid so the public map and advice work without PostGIS.
- **Done when:** a fresh PostgreSQL/PostGIS database reaches a fully populated map with documented commands only.

### WP9. Go-live readiness for telecom (code and checklists only)

The real short codes, reverse billing and sender ID are arranged by the user with Africa's Talking. Do not attempt them. Produce:

- `docs/go-live-checklist.md` covering:
  - short-code and USSD-code request, reverse-billed (zero-rated) setup and sender-ID approval
  - callback URLs for USSD and SMS, and the production API key
  - switching `SMS_PROVIDER` and `AIRTIME_PROVIDER` from `dry_run`
  - staff alert numbers (`ALERT_PHONE_NUMBERS`), and a test plan using the simulator and a real handset
- A startup warning in the logs and on the technical console when production runs with dry-run providers.
- A `scripts/check_telecom.py` that verifies credentials and sends one test SMS to a given number, only with `--send`.

### WP10. Security, privacy and offline readiness

- **One sign-in method.** The backend sets an httpOnly session cookie, but `assets/js/shared.js` also keeps a Bearer token in `sessionStorage`. Move the browser to cookie-only sessions with `credentials: "include"`, keep Bearer for API clients, and keep CSRF in mind for cookie writes (SameSite=Lax plus an Origin check).
- **Offline and local-network use:**
  - store Leaflet and leaflet.heat in `assets/vendor/` (they currently load from unpkg)
  - replace the Unsplash photos with images in `assets/img/` (ask the user for real Bugesera photos, otherwise keep the gradient fallbacks)
- **Data protection** (Rwanda Law No. 058/2021 on personal data):
  - document what personal data is stored and why
  - mask phone numbers everywhere except where staff must call back
  - add a retention setting and a script that anonymises inbound message text older than N months
  - keep grievances anonymous
- **Backups:** a `scripts/backup_db.sh` / `.ps1` for `pg_dump` with rotation, and a restore procedure in `docs/deployment.md`.
- **Done when:** the dashboard works with internet only for map tiles, and the privacy notes are in `docs/`.

### WP11. Continuous integration

- Add `.github/workflows/ci.yml` that:
  - lints with `ruff`
  - runs `pytest` on SQLite
  - runs `alembic upgrade head` and the tests against a `postgis/postgis` service container
  - builds the Docker image
- **Done when:** the workflow passes on the current branch.

### WP12. Documentation deliverables (Sections 5–6)

The reports are written by the user. Generate templates and the data that goes into them.

- `scripts/export_ussd_wireframes.py`: export the real USSD menu tree (Kinyarwanda and English) to `docs/ussd-wireframes.md` from the code and database, so the Inception Report wireframes always match the platform.
- `scripts/pilot_metrics.py`: export pilot metrics for a date range to Markdown and CSV:
  - reports by channel, type, sector and cooperative
  - active reporters, Data Champions and training progress
  - response times, closing-the-loop messages and airtime paid
  - outcome verification per scheme
- Templates in `docs/reports/`: `inception-report.md`, `mid-term-progress-note.md`, `pilot-report.md`, `final-fellowship-report.md`. Give each its section headings from the concept and placeholders that say which script or page provides the numbers.
- Training materials in `docs/training/`:
  - a Data Champion guide (Kinyarwanda and English: USSD steps, SMS keywords, rain-gauge reading, what happens after a report)
  - a District Planner guide (each dashboard page)
  - an administrator guide (accounts, schemes, calibration imports)
  - one-page printable cards for farmers
- `docs/handover.md`: the handover protocol for the Bugesera District IT unit or MINAGRI. Cover architecture, hosting requirements, Docker deployment, environment variables, telecom accounts, backups, monitoring, user and role management, calibration ownership, and a support contact.

### WP13. Housekeeping. Ask the user before each step.

- The branch has about 110 uncommitted changes. Propose a set of logical commits (backend restructure, dashboard redesign, standalone pages, docs) and wait for approval before committing.
- `git stash@{0}` holds an old Vite dashboard. Ask before dropping it.
- The project root holds template sources: `CS_IRCFS_Landing/`, the root `index.html`, `Eco Agriculture Community Emblem.png`, two WhatsApp mockup images and `CS-IRCFS-REBUILD-PROMPT.md`. Propose moving them to `design/` (and adding them to `.dockerignore`) or deleting them, and wait for the user's choice.
- Review the Kinyarwanda strings added to the dashboard (`assets/js/shared.js` `STRINGS`) and list any still missing for the new pages.

## 5. Order of work

1. WP1, WP4, WP2 (field-facing, small)
2. WP5 (cooperatives and Data Champions)
3. WP7 (calibration tooling)
4. WP10, WP11 (security, offline, CI)
5. WP8, WP9 (production geodata, go-live checklist)
6. WP3, WP6 (optional providers)
7. WP12 (documentation)
8. WP13 (housekeeping, with the user's approval)

## 6. How to report back after each work package

- What changed, as a short list of files.
- New settings, with their defaults.
- New migrations and how to run them.
- Test results (`python -m pytest -q`).
- Anything that needs the user: documents to supply, Kinyarwanda strings to review, decisions to make.

## 7. Out of scope for the agent

These need people, contracts or documents, not code. Track them in the go-live checklist and report templates instead:

- Short-code and USSD allocation, reverse billing and sender ID with Africa's Talking.
- Real PADAB and APEFA feasibility-study figures, AfDB evaluation findings and historical rainfall records.
- Field surveys (Nyamata, Ruhuha), the 3-cooperative pilot, training sessions and rain-gauge distribution.
- Writing the narrative of the Fellowship reports.
