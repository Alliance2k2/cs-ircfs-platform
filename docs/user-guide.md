# User guide

CS-IRCFS lets citizens of Bugesera report crop, water and community information from any phone, and gives District Planners the evidence to verify whether the PADAB and APEFA Solar irrigation investments deliver their expected outcomes.

## Who uses what

| Person | Channel | What they do |
| --- | --- | --- |
| Farmer | USSD `*801#`, SMS `8448` | Report harvest, pests and disease; raise a grievance; answer the nutrition survey |
| Citizen Science Monitor / Data Champion | USSD, SMS | Same as farmers, plus daily rain-gauge readings |
| Scheme operator | USSD option 4 | Report pump and canal faults by bottleneck category |
| Cooperative leader | USSD, SMS; receives advice | Rainfall readings, and gets irrigation advice by SMS |
| District Planner / officer | Web dashboard (`/app/`) | Act on cases, verify reports and scheme outcomes, send advice, close the loop |
| Administrator | Web dashboard, Administration | Approve accounts, set roles and areas, record scheme baselines, read the audit log |

## The pages

The district dashboard is at **`/app/`**: executive overview, priority actions, field reports, crops and pests, food and nutrition, irrigation command centre, climate and advice, district map, PADAB and APEFA evaluation, grievances, cooperatives, USSD and SMS operations, phone simulator, trends, monthly report and administration. [workspaces.md](workspaces.md) describes each page, who can open it and what it does. Signing in leads there.

The classic pages below still work on the same data while the district moves to `/app/`:

| Page | Address | Purpose |
| --- | --- | --- |
| Home | `/` | Public introduction and how it works |
| Planner dashboard | `/planner.html` | Overview, Act Now queue, field channels, scheme performance, response health, 12-month trends (with a table view), irrigation advice, nutrition, map |
| Monthly report | `/report.html` | One month of field evidence: reports, scheme results, cases, grievances, pests, rainfall, nutrition, messages, with a comparison to the previous month. **Print / Save as PDF** gives an A4 report |
| Phone simulator | `/simulator.html` | A feature phone on screen. Dial `*801#` or text keywords; uses the real USSD/SMS endpoints |
| Platform Management | `/management.html` | Users, schemes (incl. verified yield targets), reports, feedback, nutrition surveys, SMS log, accounts |
| Sign in / Register | `/login.html`, `/register.html` | Web accounts for planners and staff |
| Technical console | `/backend-console.html` | Backend flow and endpoint links for developers |
| API documentation | `/docs` | Interactive API reference |

Every page has an **EN / RW** language switch.

## Running it

**Evaluation and training:** runs on a separate SQLite database filled with invented sample data. The database in `.env` is not touched.

```powershell
.\start-local.ps1 -Demo          # or VS Code: Terminal → Run Task → "CS-IRCFS: Start demo"
.\start-local.ps1 -ResetDemo     # start again from a fresh demonstration dataset
```

**Real local database** (the PostgreSQL in `.env`): applies migrations and starts the platform.

```powershell
.\start-local.ps1
```

Then open `http://127.0.0.1:8000`.

## Accounts and roles

- New registrations always start as **Citizen Science Monitor**. Nobody can register as a planner or administrator.
- The first administrator is created on the server: `python backend/scripts/create_admin.py you@example.org`.
- Administrators approve new accounts and set roles in **Administration → Accounts** (`/app/admin`); each change asks for confirmation and is recorded in the audit log.
- **Citizen Science Monitors** read live figures, field reports (with masked phone numbers), crops, nutrition, irrigation, advice, the map, evaluation, trends and the monthly report.
- **Cooperative leaders** see field reports, irrigation assets, USSD and SMS operations, the simulator and the map.
- **District officers** also work priority actions and grievances, verify reports and export data.
- **District Planners** also send irrigation advice and edit cooperatives; **administrators** also get Administration.
- The home page (`/`) shows live totals and recent activity from `GET /api/v1/public/overview`. It needs no sign-in and never returns names, phone numbers, message text or grievances.
- Sign-in sessions are stored in the database (only a hash of the token) and expire after 12 hours (`SESSION_HOURS`).
- **Area-level access.** In **Administration → Accounts**, open an account and tick the sectors an officer, planner or monitor works in. They then see cases, grievances, people, reports and messages from those sectors only, and can broadcast advice only to them. No ticks means the whole district. Administrators always see the whole district.
- Integrations can still use service API keys (`API_KEY_ROLES`).
- In evaluation mode (`-Demo`, `ENVIRONMENT=development`) sign-in is turned off.

## Alerts and forecasts

- **Staff alerts.** Put district phone numbers in `ALERT_PHONE_NUMBERS` in `.env` (comma-separated). Each gets an SMS when a case opens: offline assets and severity-5 pests by default, or also faulty assets and severity-4 pests with `ALERT_MIN_PRIORITY=high`. Alerts appear in the SMS log as `staff_alert`.
- **Rain forecast.** Irrigation advice adds the Open-Meteo 7-day forecast for each sector (free, no key, cached for 3 hours). If a dry week is followed by heavy forecast rain, the advice is to keep the usual schedule instead of irrigating more. Set `WEATHER_FORECAST_ENABLED=false` to turn it off.

## Useful scripts (`backend/scripts/`)

| Script | Use |
| --- | --- |
| `load_locations.py` | Load the 15 sectors and 72 cells from `data/*.gpkg`. No QGIS needed |
| `seed_reference_schemes.py` | Add PADAB and APEFA Solar with their published figures |
| `seed_demo_data.py` | Invented sample data for evaluation and training only |
| `create_admin.py` | Create or promote an administrator |
| `check_db.py`, `schema_audit.py` | Check the database connection, migration revision, and columns |
| `configure_api_key.py` | Generate a service API key in `.env` |
