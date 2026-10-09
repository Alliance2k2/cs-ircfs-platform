# CS-IRCFS Platform — Complete Full-Stack Rebuild Prompt

> **How to use:** Copy everything below the horizontal rule (`---`) and paste it into any capable AI (Claude, ChatGPT, Gemini, etc.). The prompt is fully self-contained — the receiving AI needs no other files or context from you. Provide your `.env` credentials when asked.
>
> **Warning:** This is a full rebuild prompt, not a patch request. The AI will produce a new, clean codebase. Commit or back up your current code before applying the output.

---

# CS-IRCFS Platform — Complete Full-Stack Rebuild

You are an expert full-stack engineer. Your task is to rebuild the CS-IRCFS
(Citizen Science for Irrigation Resilience and Climate-smart Food Security)
platform from the ground up, producing a clean, production-grade codebase.
Follow every instruction in this prompt precisely and completely.

---

## 1. PROJECT CONTEXT

CS-IRCFS is a field-reporting and decision-support platform for Bugesera
District, Rwanda. Farmers, cooperatives, and Citizen Science Monitors report
crop, water, and community data from any feature phone using USSD (`*801#`) and
SMS (`8448`) in Kinyarwanda — no internet access required.

District staff use a web dashboard to:

- Verify irrigation scheme outcomes against yield targets
- Manage an Act Now case queue (pest alerts, infrastructure faults)
- Track community grievances and close the loop by SMS
- View a monthly district report and 12-month trend charts
- Send irrigation scheduling advice to cooperatives by SMS
- Monitor household nutrition risk by cell area

The two irrigation schemes covered are:

- **PADAB** (Mwesa Valley, implemented by AfDB)
- **APEFA Solar** (Ngeruka/Mareba, implemented by APEFA)

**Geographic scope:** Bugesera District — 15 sectors, 72 cells.  
**Primary phone channel:** Africa's Talking gateway (USSD + SMS + airtime).  
**Weather data:** Open-Meteo 7-day rainfall forecast (free, no API key).

---

## 2. TECHNOLOGY STACK

### Backend

- Python 3.11+
- FastAPI (latest stable, ≥0.115)
- SQLAlchemy 2.0+ with the modern `Mapped`/`mapped_column` declarative style
  (**NO** legacy `db.query()` patterns anywhere in the codebase)
- Pydantic v2 with `pydantic-settings` for configuration
- Alembic for database migrations
- psycopg (v3) for PostgreSQL connections
- GeoAlchemy2 for PostGIS geometry columns
- pytest + httpx for testing
- slowapi for rate limiting

### Database

- Development/evaluation: SQLite (in-memory for tests, file for local dev)
- Production: PostgreSQL 16 + PostGIS 3
- All schema changes go through Alembic migrations — never `create_all()` in production

### Frontend

- ES Modules (`type="module"` scripts — no global variables, no `window.*` hacks)
- Vanilla JavaScript with proper module imports/exports
- **Vite** for local development and bundling (`vite.config.js` in `dashboard/`)
- A single consolidated design-token CSS system (no override files)
- Leaflet.js for the map (loaded via CDN)
- Chart.js for trend charts (loaded via CDN)

### External Services

- Africa's Talking: USSD callbacks, SMS send, airtime disbursement
- Open-Meteo: 7-day rainfall forecast (optional, togglable)
- Google OAuth: optional web sign-in

### Deployment

- Docker + Docker Compose (PostgreSQL/PostGIS + platform)
- `render.yaml` for hosted deployment
- `start-local.ps1` (PowerShell) for local development

---

## 3. FULL FEATURE SPECIFICATION

### 3.1 Field Channels (USSD `*801#` and SMS `8448`)

USSD menu — six top-level options, numeric choices, at most three levels:

1. Harvest report (crop type, expected tons, reported tons)
2. Pest or disease alert (crop, pest name, severity 1–5)
3. Rainfall reading (mm, gauge type)
4. Infrastructure health (asset, status, bottleneck category)
5. Grievance (category, anonymous — reporter never stored, only the cell)
6. Household nutrition survey (3 questions → stunting-risk score 1–5)

All USSD text in Kinyarwanda first. Numeric choices only.

First-time callers choose their sector and cell once; every later report
uses their stored location automatically.

**Gateway retries:** detect duplicate `session_id`+`text` pairs and never
record the same report twice.

**SMS keywords** (inbound to 8448):

| Keyword | Action |
|---|---|
| `IMVURA` | Rainfall reading (e.g. `IMVURA 12.5`) |
| `NZANA` | Pest/disease alert (e.g. `NGERUKA NZANA 4`) |
| `UMUSARURO` | Harvest report |
| `IKIBAZO` | Grievance |

**Auto-replies:** every inbound message receives a Kinyarwanda confirmation SMS
with a record number. Every 3rd weather/infrastructure report triggers a
100 RWF airtime reward (configurable via env).

### 3.2 Dashboard Features

All dashboard pages must support English and Kinyarwanda (toggle in header).
i18n strings must live in a separate `/dashboard/src/i18n/strings.js` file —
**NOT** inline in any component file.

| URL | Page | Auth |
|---|---|---|
| `/` | Public home page: live totals, sector activity feed | Public |
| `/planner.html` | District planner dashboard | Authenticated |
| `/report.html` | Printable monthly district report | Authenticated |
| `/management.html` | Platform management | Admin / Planner |
| `/simulator.html` | Feature phone simulator for USSD/SMS | Public |
| `/login.html` | Sign-in page | Public |
| `/register.html` | Self-registration | Public |
| `/backend-console.html` | Technical console | Admin only |

**Planner dashboard sections:**

- Overview metrics (farmers, reports, schemes, complaints, assets, households, rewards)
- Act Now queue (cases + community feedback, sorted by priority, auto-refresh every 15 s)
- Field channels live feed (last 20 inbound messages)
- Scheme performance (yield vs target; flagged bottlenecks ≥3 times in 90 days)
- Response health (resolution rate, median days to resolve, close-loop SMS count)
- Irrigation advice by sector (7-day rainfall + Open-Meteo forecast)
- Household nutrition by cell (stunting-risk map + table)
- Leaflet map with switchable layers:
  - Irrigation scheme boundaries
  - Infrastructure reports
  - Crop reports (markers)
  - Pest heatmap (severity-weighted points)
  - Rainfall & drought (7-day rainfall per cell)
  - Nutrition risk (colour-coded cells)
  - Registered farmers (points)
- Community feedback list with status workflow

### 3.3 Case Workflow

`IncidentCase` records wrap crop and infrastructure reports:

- **Priority:** critical / high / medium
- **Status:** `open` → `triaged` → `assigned` → `in_progress` → `resolved` → `closed`
- Immutable audit trail (`IncidentEvent` table)
- Assigned officer + due date
- "Notify community by SMS" sends a closing-the-loop message to every
  registered person in the affected cell

**Auto-case rules:**

- Severity 4–5 pest reports → critical/high case created automatically
- Offline infrastructure reports → critical case created automatically
- Staff alert SMS sent when a case opens at or above `ALERT_MIN_PRIORITY`

### 3.4 Advisory Messages

Every outbound SMS is an `AdvisoryMessage` record with:

```
phone_number, language (rw/en), message, channel (sms/ussd),
status (queued/sent/failed/dry_run), provider_id,
purpose (auto_reply/local_tip/irrigation_advice/close_loop/staff_alert),
cell_id
```

**Irrigation scheduling advice:**

- 7-day gauge total per sector
- Three levels: `irrigate_less` (≥ WET threshold) / `normal` / `irrigate_more` (≤ DRY threshold)
- Optionally augmented with Open-Meteo 7-day forecast
- District planner can broadcast advice to all cooperatives in a sector

### 3.5 Monthly Report and Trends

**Monthly report** (YYYY-MM, Kigali time = UTC+2):

- Total reports, new users, active reporters
- Scheme-by-scheme harvest vs target
- Infrastructure faults by category
- Grievances opened/resolved
- Nutrition surveys and average risk
- SMS sent / airtime disbursed
- Compared with previous month (delta %)

**12-month trends:** month-by-month reports, rainfall, cases, harvests,
nutrition — returned as structured data for the Chart.js frontend.

---

## 4. DATA MODEL

Create the following tables via Alembic migrations. Use SQLAlchemy 2.0
`Mapped`/`mapped_column` syntax throughout — no legacy `Column()` usage.

### Core Geography

```
sectors (id, name, latitude, longitude, boundary MULTIPOLYGON)
cells   (id, name, sector_id FK→sectors, latitude, longitude, boundary MULTIPOLYGON)
```

### Users (Two Separate, Clearly Named Systems)

```
field_users                 ← USSD/SMS callers (farmers, monitors, cooperatives)
  id, phone_number UNIQUE, full_name,
  role ENUM(farmer/citizen_science_monitor/cooperative_leader),
  cooperative_name, cell_id FK→cells, is_active, location POINT, created_at

platform_accounts           ← Web dashboard staff
  id, email UNIQUE, full_name, password_hash,
  role ENUM(citizen_science_monitor/district_officer/district_planner/administrator),
  status (pending/active/suspended), created_at
  + account_sectors  (many-to-many join table)

auth_sessions               ← Only SHA-256 hashed token stored
  id, token_hash UNIQUE, account_id FK→platform_accounts CASCADE,
  created_at, expires_at
```

> **IMPORTANT:** The two user systems must be clearly separated in naming,
> routes, and documentation. Never call a `platform_account` a "user" and
> never call a `field_user` an "account".

### Irrigation

```
irrigation_schemes
  id, name UNIQUE, implementing_partner, hectares_developed,
  baseline_yield_target_tons, baseline_source,
  sector_id FK→sectors, latitude, longitude, boundary MULTIPOLYGON, is_active
```

### Field Reports

```
citizen_science_logs        ← Harvest + pest reports
  id, reporter_id FK→field_users, scheme_id FK→irrigation_schemes,
  cell_id FK→cells, crop_type, planting_date,
  expected_harvest_tons, reported_harvest_tons,
  pest_or_disease, severity (1–5), notes, latitude, longitude, created_at

irrigation_climate_logs     ← Infrastructure + rainfall reports
  id, reporter_id FK→field_users, scheme_id FK→irrigation_schemes,
  cell_id FK→cells, infrastructure_name, operational_status,
  bottleneck_category, fault_description, rainfall_mm,
  latitude, longitude, created_at

nutrition_surveys           ← Household nutrition (USSD option 6)
  id, reporter_id FK→field_users, cell_id FK→cells,
  meals_per_day, ate_protein_or_vegetables BOOL, food_sufficient BOOL,
  stunting_risk_score (1–5), created_at
```

### Cases and Feedback

```
community_feedback          ← Grievances and community reports
  id, reporter_id NULL (always anonymous), scheme_id, cell_id,
  category, message,
  status ENUM(open/triaged/assigned/in_progress/resolved/closed),
  assigned_to_field_user_id, due_at, action_taken, created_at, updated_at

community_feedback_events   ← Immutable audit trail
  id, feedback_id FK, previous_status, new_status,
  action_taken, changed_by_account_id FK→platform_accounts, created_at

incident_cases              ← Planner workflow
  id, source_type VARCHAR (only "crop" or "infrastructure"),
  source_id INT, priority (critical/high/medium),
  status ENUM, assigned_to_account_id FK→platform_accounts,
  due_at, action_taken, reporter_notified_at, created_at, updated_at
  UNIQUE(source_type, source_id)

incident_events             ← Immutable audit trail
  id, case_id FK, previous_status, new_status,
  action_taken, changed_by_account_id FK, created_at
```

### Messaging

```
inbound_messages            ← USSD steps and SMS received
  id, phone_number, channel (ussd/sms), session_id, text, reply,
  record_type, record_id (informational only — no FK constraint),
  created_at
  INDEX(phone_number, created_at DESC)
  INDEX(session_id)

advisory_messages           ← Every outbound SMS
  id, phone_number, language, message, channel, status,
  provider_id, purpose, cell_id FK→cells, created_at

incentive_rewards           ← Airtime micro-bonuses
  id, field_user_id FK→field_users, phone_number, amount_rwf,
  reason, status (pending/sent/failed/dry_run), provider_id, created_at
```

---

## 5. BACKEND ARCHITECTURE

### 5.1 Project Layout

```
backend/
  app/
    __init__.py
    main.py                 FastAPI app, middleware, router registration
    core/
      config.py             Pydantic-settings Settings class
      security.py           Principal, hash_token, require_roles
      scope.py              allowed_cells() helper
      logging.py            Structured logging setup
    api/
      routes/
        auth.py             /api/v1/auth/*
        field_users.py      /api/v1/field-users/*
        schemes.py          /api/v1/irrigation-schemes/*
        channels.py         /api/v1/ussd, /api/v1/sms/inbound
        reports.py          /api/v1/citizen-reports/*, /api/v1/irrigation-reports/*
        cases.py            /api/v1/cases/*
        feedback.py         /api/v1/feedback/*
        analytics.py        /api/v1/analytics/*  ← THIN LAYER ONLY
        advisory.py         /api/v1/advisory/*
        map_data.py         /api/v1/map-data
        geography.py        /api/v1/geography/*
        reference_data.py   /api/v1/sectors, /api/v1/cells
        public.py           /api/v1/public/*
        system.py           /api/v1/health
    db/
      base.py               DeclarativeBase
      models.py             All SQLAlchemy models
      session.py            engine, get_db dependency
    schemas/
      auth.py
      field_users.py
      schemes.py
      reports.py
      cases.py
      feedback.py
      analytics.py
      advisory.py
      geography.py
    services/
      analytics.py          dashboard_summary(), scheme_performance(),
                            response_health(), nutrition_summary()
      reporting.py          build_monthly_report(), build_trends()
      advisory.py           advice_for_rainfall(), irrigation_schedule(),
                            send_irrigation_advice(), maybe_reward()
      forecast.py           fetch_open_meteo_forecast()
      notifications.py      send_staff_alert(), send_close_loop_sms()
      sms.py                SMS provider abstraction
      ussd.py               USSD menu state machine
      sms_keywords.py       Inbound SMS keyword parser
      cases.py              auto_create_case(), resolve_case()
  migrations/
    versions/
  scripts/
    create_admin.py
    load_locations.py
    seed_demo_data.py
    check_db.py
  tests/
    conftest.py
    test_auth.py
    test_field_users.py
    test_reports.py
    test_cases.py
    test_ussd.py
    test_sms_keywords.py
    test_analytics.py
    test_advisory.py
```

### 5.2 Analytics Architecture (CRITICAL)

The analytics route handlers **must be thin**. All business logic —
database queries, calculations, aggregations — must live in
`services/analytics.py`, `services/reporting.py`, and `services/advisory.py`.

A correct route handler looks like this:

```python
@router.get("/dashboard-summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    principal: Principal = viewer,
) -> DashboardSummary:
    return analytics_service.dashboard_summary(db, principal)
```

**Never put SQL queries directly inside route handlers.**

### 5.3 SQLAlchemy Style

Use **only** the SQLAlchemy 2.0 style throughout:

```python
# CORRECT
results = db.scalars(select(IncidentCase).where(IncidentCase.status == "open")).all()

# FORBIDDEN — remove every instance
results = db.query(IncidentCase).filter(IncidentCase.status == "open").all()
```

### 5.4 Rate Limiting

Install `slowapi`. Apply to:

| Endpoint | Limit |
|---|---|
| `POST /api/v1/ussd` | 30 / minute per IP |
| `POST /api/v1/sms/inbound` | 30 / minute per IP |
| `POST /api/v1/auth/login` | 10 / minute per IP |

### 5.5 Session Cookies

The FastAPI backend must:

1. Accept Bearer tokens in the `Authorization` header (for API clients).
2. Accept and **set** an `httpOnly`, `SameSite=Lax`, `Secure` cookie named
   `cs_ircfs_session` for browser clients.
3. On login, set the cookie **and** return the token in the response body.
4. On logout, clear the cookie.

`COOKIE_SECURE=false` in `.env` for local HTTP development.

---

## 6. FRONTEND ARCHITECTURE

### 6.1 Module System

All JavaScript **must** use ES Modules:

```html
<script type="module" src="/src/main.js"></script>
```

No global variables via `window.*`. Pass state through module imports and
exported functions.

Use **Vite** for the build.

### 6.2 Folder Layout

```
dashboard/
  src/
    main.js                 Entry for planner.html
    management.js           Entry for management.html
    pages/
      planner/
        index.js
        sections/
          overview.js
          act-now.js
          channels.js
          schemes.js
          map.js
          advice.js
          nutrition.js
          feedback.js
          response-health.js
      management/
        index.js
        modules/
          field-users.js
          accounts.js
          schemes.js
          reports.js
          messages.js
          analytics.js
      simulator/
        index.js
      report/
        index.js
    shared/
      api.js                apiFetch, apiJson
      session.js            session management (cookie-aware)
      i18n.js               t(), setLang(), applyI18n()
      toast.js              toast()
      map-utils.js          Leaflet helpers
      chart-utils.js        Chart.js helpers
    i18n/
      strings.js            ALL i18n strings — nothing else in this file
    demo/
      demo-data.js          ALL demo data — never imported by production paths
  styles/
    tokens.css              CSS custom property tokens ONLY
    global.css              Reset + base typography + body
    shared.css              Sidebar, topbar, cards, buttons, forms
    planner.css             Planner-specific styles
    management.css          Management-specific styles
    simulator.css           Simulator styles
  public/
    *.html                  All 8 HTML pages
    bugesera-boundary.geojson
  vite.config.js
  package.json
```

### 6.3 CSS System

**One** design token file (`styles/tokens.css`). Every color, spacing,
radius, and font is a CSS custom property.

No color may appear as a literal hex or RGB value in any file other than
`tokens.css`.

Token structure:

```css
/* styles/tokens.css */
:root {
  --bg: #0f1117;
  --surface: #181c27;
  --fg: #e2e8f4;
  --accent: #4f7fff;
  /* ... */
}

@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    --bg: #f5f7ff;
    --surface: #ffffff;
    --fg: #0f1117;
    --accent: #2d5fe8;
    /* ... */
  }
}

:root[data-theme="light"] {
  --bg: #f5f7ff;
  /* same light values */
}
```

**No override files. No `styles.css` that is 1 line. No `-overrides.css` files.**
Each CSS file has one clear responsibility.

### 6.4 Cache Busting

Vite handles cache busting automatically via content hashes in filenames.
**Do NOT add manual `?v=...` version numbers** to any HTML `<link>` or `<script>` tags.

### 6.5 i18n

`src/i18n/strings.js` contains exactly one export:

```js
// src/i18n/strings.js
export const STRINGS = {
  "nav.home":    ["Home",         "Ahabanza"],
  "nav.actnow":  ["Act now",      "Ibyihutirwa"],
  // ... all strings
};
```

Nothing else goes in this file.

### 6.6 Demo Data

`src/demo/demo-data.js` contains exactly one export with all sample figures.
Production code paths **never** import this file.

---

## 7. SECURITY REQUIREMENTS

1. **httpOnly cookies** for browser sessions (see section 5.5).
2. **Rate limiting** on USSD, SMS inbound, and login endpoints (section 5.4).
3. **No dev bypass in production.** Startup must raise `RuntimeError` if
   `ENVIRONMENT=production` and `REQUIRE_API_KEY=false`.
4. **No SQLite in production.** Startup must refuse if
   `ENVIRONMENT=production` and `DATABASE_URL` starts with `sqlite`.
5. All request bodies validated server-side with Pydantic before any DB write.
6. **Grievances are always anonymous.** `reporter_id` is always `NULL` in
   `community_feedback` — never accept or store it, even if sent in the request.
7. Public endpoints (`/api/v1/public/*`) return aggregates only — no names,
   phone numbers, message text, or individual grievance content.
8. CORS: only origins in `settings.allowed_origins` are accepted.
9. Session token is SHA-256 hashed before storage; never store plaintext.
10. Password hash: PBKDF2-SHA256, 210,000 iterations.
11. Admin accounts can only be created by existing admins or via
    `create_admin.py` — never by self-registration.
12. Self-registration always creates `citizen_science_monitor` role. Admins
    promote accounts from Platform Management.

---

## 8. TESTING REQUIREMENTS

### 8.1 Test Structure

Write **separate, focused test files** — NOT one giant sequential integration
test. Each domain has its own file. Every test function tests one behaviour.

### 8.2 Required Tests

**`tests/conftest.py`**
- In-memory SQLite engine and session factory
- `TestClient` factory with auth override helpers
- Admin and planner principal fixtures
- No network calls, no file system side effects

**`tests/test_auth.py`**
- Register creates `citizen_science_monitor` role
- Login returns token and sets cookie
- Expired session returns 401
- Suspended account returns 403
- `citizen_science_monitor` cannot access planner-only endpoints
- Admin can update account role and area sectors

**`tests/test_field_users.py`**
- Create field user with phone number normalisation
- Duplicate phone number returns 409
- Cannot delete a field user who has reports → 409
- Can delete a field user with no reports → 204
- Update field user cell and role

**`tests/test_reports.py`**
- Crop report with severity ≥ 4 creates an `incident_case`
- Crop report with severity ≤ 3 does **not** create a case
- Infrastructure `offline` report creates a critical case
- Infrastructure `operational` report does not create a case
- Duplicate USSD `session_id` is idempotent — no duplicate record
- Nutrition survey computes correct `stunting_risk_score`

**`tests/test_cases.py`**
- Act Now queue returns open cases sorted by priority
- Resolving a case removes it from the Act Now queue
- Case history grows by 1 on each status change
- Close-loop SMS endpoint queues advisory messages for each cell resident
- Area-scoped principal only sees cases in their cells

**`tests/test_ussd.py`**
- Full session: first-time caller registers sector/cell, submits harvest report —
  verify both `field_user` location and `citizen_science_log` record
- Option 2, severity 5: verify critical case auto-created
- Option 5 (grievance): verify `reporter_id` is `NULL`
- Retry with same `session_id`: verify no duplicate record
- Unknown caller gets registration flow

**`tests/test_sms_keywords.py`**
- `IMVURA` creates `irrigation_climate_log` with `rainfall_mm`
- `NZANA` creates `citizen_science_log` pest report
- `UMUSARURO` creates `citizen_science_log` harvest report
- `IKIBAZO` creates `community_feedback` with `NULL` reporter
- Unknown keyword returns helpful Kinyarwanda auto-reply

**`tests/test_analytics.py`**
- `dashboard_summary()` counts correct after inserting known records
- `scheme_performance()` returns correct `achievement_percent`
- Bottleneck flagged when category appears ≥ 3 times in 90 days
- Bottleneck **not** flagged when category appears < 3 times
- `response_health()` `resolution_rate` is mathematically correct

**`tests/test_advisory.py`**
- `advice_for_rainfall()` returns `irrigate_more` below dry threshold
- `advice_for_rainfall()` returns `irrigate_less` above wet threshold
- `advice_for_rainfall()` returns `normal` between thresholds
- Airtime reward triggered on every 3rd qualifying report
- Airtime reward **not** triggered on 1st or 2nd report

### 8.3 Test Run Command

```bash
cd backend && python -m pytest -q --tb=short
```

All tests run on in-memory SQLite with **no network calls**
(mock Africa's Talking and Open-Meteo with `pytest monkeypatch`).

---

## 9. DEVOPS AND DEPLOYMENT

### 9.1 `.gitignore` — Required Entries

```
*.db
*.sqlite
*.sqlite3
.env
infrastructure/stack.env
.venv/
__pycache__/
*.pyc
*.pyo
node_modules/
dist/
.DS_Store
```

### 9.2 `.env.example`

```env
ENVIRONMENT=development
DATABASE_URL=sqlite:///./cs_ircfs.db
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:8000
REQUIRE_API_KEY=false
API_KEY_ROLES=
SESSION_HOURS=12
COOKIE_SECURE=false
GOOGLE_CLIENT_ID=

SMS_PROVIDER=dry_run
AIRTIME_PROVIDER=dry_run
AFRICAS_TALKING_USERNAME=sandbox
AFRICAS_TALKING_API_KEY=
SMS_SENDER_ID=
INCENTIVE_AMOUNT_RWF=100
INCENTIVE_EVERY_N_REPORTS=3

DRY_SPELL_THRESHOLD_MM=10
WET_SPELL_THRESHOLD_MM=40
ALERT_PHONE_NUMBERS=
ALERT_MIN_PRIORITY=critical
WEATHER_FORECAST_ENABLED=true

LOG_LEVEL=INFO
USSD_SERVICE_CODE=*801#
SMS_SHORTCODE=8448
```

### 9.3 Dockerfile (Multi-Stage)

```dockerfile
# Stage 1: Build frontend
FROM node:20-slim AS frontend
WORKDIR /app/dashboard
COPY dashboard/package*.json ./
RUN npm ci
COPY dashboard/ ./
RUN npm run build

# Stage 2: Backend + bundled frontend
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend /app/dashboard/dist ./dashboard/
CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
```

### 9.4 `infrastructure/docker-compose.yml`

Two services:
- `db`: `postgres:16-postgis` with PostGIS extension enabled
- `platform`: built image, `depends_on: db`, env from `stack.env`

### 9.5 `start-local.ps1`

- Accept a `-Demo` flag: starts against `backend/demo.db` with sign-in off
- Without the flag: start normally against `DATABASE_URL`
- Run `alembic upgrade head` automatically before starting

---

## 10. THE 19 ISSUES TO FIX

Fix **every one** of the following — do not leave any unresolved.

### 🔴 Critical

| ID | Fix |
|---|---|
| **FIX-01** | **CSS:** Replace all override files and empty 1-line base CSS files with a proper token-based CSS system (`styles/tokens.css` + purpose-named files). No `styles.css` that is 1 line. No `*-overrides.css` files. |
| **FIX-02** | **JS Modules:** Replace all global-state, `document.querySelector` procedural scripts with ES Modules. No `window.*` global exports. |
| **FIX-03** | **DB Files:** Add `*.db` to `.gitignore`. Remove all committed `.db` files from the repository. The root-level `cs_ircfs.db` must be deleted. |
| **FIX-04** | **Naming:** Rename all "users" that are USSD callers to `field_users` and all "accounts" that are web staff to `platform_accounts`. Apply consistently across models, schemas, routes, and frontend. |
| **FIX-14** | **Tests:** Write all tests described in Section 8. Replace the single giant sequential integration test with focused, independent test functions. |

### 🟠 Significant

| ID | Fix |
|---|---|
| **FIX-05** | **Analytics layer:** Move all business logic and SQL from analytics route handlers into `services/analytics.py`. Route handlers must be thin delegators only. |
| **FIX-06** | **Polymorphic FK:** Add application-level safeguards so resolving a case that points at a deleted source record does not produce dangling data silently. |
| **FIX-07** | **Session storage:** Move session tokens from `sessionStorage` to httpOnly cookies. Keep Bearer token support for API clients. |
| **FIX-08** | **Dev auth bypass:** Add a startup warning log whenever dev bypass is active. Raise `RuntimeError` if `ENVIRONMENT=production` and `REQUIRE_API_KEY=false`. |
| **FIX-09** | **Rate limiting:** Add `slowapi` rate limiting to USSD, SMS inbound, and login endpoints. |

### 🟡 Moderate

| ID | Fix |
|---|---|
| **FIX-10** | **Schemas:** Split `schemas.py` into domain-specific schema modules under `backend/app/schemas/`. |
| **FIX-11** | **Cache busting:** Use Vite content-hash filenames. Remove all `?v=20xxxxxx` manual version strings from HTML. |
| **FIX-12** | **SQLAlchemy style:** Use only SQLAlchemy 2.0 style everywhere. Remove all `db.query()` / `.filter()` legacy calls. |
| **FIX-13** | **Dead code:** Remove the `Farm` model and the `501 /geography/farms` route entirely, or fully implement them. Do not ship a `501`. |
| **FIX-15** | **trends.js island:** `trends.js` must become a proper ES Module imported by the planner page module — not a detached file. |

### 🔵 Minor

| ID | Fix |
|---|---|
| **FIX-16** | **.venv:** Ensure `.venv/` is in `.gitignore`. Do not include it in the repository. |
| **FIX-17** | **i18n:** Move all i18n strings out of `shared.js` into `dashboard/src/i18n/strings.js`. Nothing else in that file. |
| **FIX-18** | **Demo data:** Move all demo data out of `app.js` into `dashboard/src/demo/demo-data.js`. Production code paths must never import it. |
| **FIX-19** | **Spatial local dev:** When SQLite is active, the UI must show a visible "Spatial features require PostgreSQL" notice on map panels that return empty data — not silently show nothing. |

---

## 11. DELIVERABLES CHECKLIST

Produce **every file** listed. Do not skip any. No placeholders, no ellipsis,
no "rest of file unchanged."

### Backend

- [ ] `backend/app/main.py`
- [ ] `backend/app/core/config.py`
- [ ] `backend/app/core/security.py`
- [ ] `backend/app/core/scope.py`
- [ ] `backend/app/core/logging.py`
- [ ] `backend/app/db/base.py`
- [ ] `backend/app/db/models.py`
- [ ] `backend/app/db/session.py`
- [ ] `backend/app/schemas/__init__.py`
- [ ] `backend/app/schemas/auth.py`
- [ ] `backend/app/schemas/field_users.py`
- [ ] `backend/app/schemas/schemes.py`
- [ ] `backend/app/schemas/reports.py`
- [ ] `backend/app/schemas/cases.py`
- [ ] `backend/app/schemas/feedback.py`
- [ ] `backend/app/schemas/analytics.py`
- [ ] `backend/app/schemas/advisory.py`
- [ ] `backend/app/schemas/geography.py`
- [ ] `backend/app/api/routes/auth.py`
- [ ] `backend/app/api/routes/field_users.py`
- [ ] `backend/app/api/routes/schemes.py`
- [ ] `backend/app/api/routes/channels.py`
- [ ] `backend/app/api/routes/reports.py`
- [ ] `backend/app/api/routes/cases.py`
- [ ] `backend/app/api/routes/feedback.py`
- [ ] `backend/app/api/routes/analytics.py`
- [ ] `backend/app/api/routes/advisory.py`
- [ ] `backend/app/api/routes/map_data.py`
- [ ] `backend/app/api/routes/geography.py`
- [ ] `backend/app/api/routes/reference_data.py`
- [ ] `backend/app/api/routes/public.py`
- [ ] `backend/app/api/routes/system.py`
- [ ] `backend/app/services/analytics.py`
- [ ] `backend/app/services/reporting.py`
- [ ] `backend/app/services/advisory.py`
- [ ] `backend/app/services/forecast.py`
- [ ] `backend/app/services/notifications.py`
- [ ] `backend/app/services/sms.py`
- [ ] `backend/app/services/ussd.py`
- [ ] `backend/app/services/sms_keywords.py`
- [ ] `backend/app/services/cases.py`
- [ ] `backend/migrations/env.py`
- [ ] `backend/migrations/versions/` (all migration files)
- [ ] `backend/requirements.txt`
- [ ] `backend/tests/conftest.py`
- [ ] `backend/tests/test_auth.py`
- [ ] `backend/tests/test_field_users.py`
- [ ] `backend/tests/test_reports.py`
- [ ] `backend/tests/test_cases.py`
- [ ] `backend/tests/test_ussd.py`
- [ ] `backend/tests/test_sms_keywords.py`
- [ ] `backend/tests/test_analytics.py`
- [ ] `backend/tests/test_advisory.py`
- [ ] `backend/scripts/create_admin.py`
- [ ] `backend/scripts/load_locations.py`
- [ ] `backend/scripts/seed_demo_data.py`

### Frontend

- [ ] `dashboard/vite.config.js`
- [ ] `dashboard/package.json`
- [ ] `dashboard/styles/tokens.css`
- [ ] `dashboard/styles/global.css`
- [ ] `dashboard/styles/shared.css`
- [ ] `dashboard/styles/planner.css`
- [ ] `dashboard/styles/management.css`
- [ ] `dashboard/styles/simulator.css`
- [ ] `dashboard/src/i18n/strings.js`
- [ ] `dashboard/src/demo/demo-data.js`
- [ ] `dashboard/src/shared/api.js`
- [ ] `dashboard/src/shared/session.js`
- [ ] `dashboard/src/shared/i18n.js`
- [ ] `dashboard/src/shared/toast.js`
- [ ] `dashboard/src/shared/map-utils.js`
- [ ] `dashboard/src/shared/chart-utils.js`
- [ ] `dashboard/src/main.js`
- [ ] `dashboard/src/management.js`
- [ ] `dashboard/src/pages/planner/index.js` + all section modules
- [ ] `dashboard/src/pages/management/index.js` + all module files
- [ ] `dashboard/src/pages/simulator/index.js`
- [ ] `dashboard/src/pages/report/index.js`
- [ ] `dashboard/public/index.html`
- [ ] `dashboard/public/planner.html`
- [ ] `dashboard/public/management.html`
- [ ] `dashboard/public/simulator.html`
- [ ] `dashboard/public/report.html`
- [ ] `dashboard/public/login.html`
- [ ] `dashboard/public/register.html`
- [ ] `dashboard/public/backend-console.html`

### Config and Infrastructure

- [ ] `.env.example`
- [ ] `.gitignore`
- [ ] `Dockerfile`
- [ ] `infrastructure/docker-compose.yml`
- [ ] `infrastructure/README.md`
- [ ] `render.yaml`
- [ ] `start-local.ps1`

### Documentation

- [ ] `README.md`
- [ ] `docs/architecture.md`
- [ ] `docs/data-model.md`
- [ ] `docs/deployment.md`
- [ ] `ussd-sms/README.md`

---

## 12. CODING STANDARDS

- **Python:** PEP 8. Line length ≤ 100 chars. Type annotations on all
  functions. No bare `except:`. No `print()` in production code (use `logging`).

- **JavaScript:** ESNext. `const` by default, `let` when reassignment is
  needed, never `var`. Arrow functions. Template literals. `async/await` not
  `.then()`. No `console.log()` in production paths.

- **SQL/ORM:** All queries through SQLAlchemy. No raw SQL strings.
  Parameterised queries only. No ORM calls that load entire tables
  to filter in Python.

- No `TODO` or `FIXME` in delivered code. If something is genuinely not
  implemented, raise `NotImplementedError` with a clear message.

- Each file begins with a one-line module docstring explaining its purpose.

---

## 13. DELIVERY ORDER

Begin with the backend. Produce each file **in full** — no placeholders,
no ellipsis (`...`), no "rest of file unchanged."

Deliver files in this order:

1. `backend/app/db/models.py`
2. `backend/app/core/config.py`
3. `backend/app/core/security.py`
4. `backend/app/db/session.py`
5. `backend/app/db/base.py`
6. All `backend/app/schemas/*.py` files
7. All `backend/app/services/*.py` files
8. All `backend/app/api/routes/*.py` files
9. `backend/app/main.py`
10. All `backend/tests/*.py` files
11. `backend/requirements.txt`, `backend/alembic.ini`, `backend/migrations/env.py`
12. All `backend/scripts/*.py` files
13. All frontend files (`dashboard/`)
14. All config and infrastructure files

If you reach a token limit mid-file, stop at the end of the current file
and wait for me to say "continue." Do not truncate a file midway.
