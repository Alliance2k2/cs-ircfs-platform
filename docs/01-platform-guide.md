# Platform guide

CS-IRCFS lets citizens of Bugesera report crop, water and community information from any phone, and gives District Planners the evidence to verify whether the PADAB and APEFA Solar irrigation investments deliver their expected outcomes.

## Who uses what

| Person | Channel | What they do |
| --- | --- | --- |
| Farmer | USSD `*801#`, SMS `8448` | Report harvest, pests and disease; raise a grievance; answer the nutrition survey |
| Citizen Science Monitor / Data Champion | USSD, SMS | Same as farmers, plus daily rain-gauge readings |
| Scheme operator | USSD option 4 | Report pump and canal faults by bottleneck category |
| Cooperative leader | USSD, SMS; receives advice | Rainfall readings, and gets irrigation advice by SMS |
| District Planner / officer | Web dashboard | Act on cases, verify scheme outcomes, send advice, close the loop |
| Administrator | Web, Platform Management | Manage people, schemes, accounts and roles |

## The pages

| Page | Address | Purpose |
| --- | --- | --- |
| Home | `/` | Public introduction and how it works |
| Planner dashboard | `/planner.html` | Overview, Act Now queue, field channels, scheme performance, response health, irrigation advice, nutrition, map |
| Phone simulator | `/simulator.html` | A feature phone on screen. Dial `*801#` or text keywords; uses the real USSD/SMS endpoints |
| Platform Management | `/management.html` | Users, schemes (incl. verified yield targets), reports, feedback, nutrition surveys, SMS log, accounts |
| Sign in / Register | `/login.html`, `/register.html` | Web accounts for planners and staff |
| Technical console | `/backend-console.html` | Backend flow and endpoint links for the technical team |
| API documentation | `/docs` | Interactive API reference |

Every page has an **EN / RW** language switch. The dashboard has a **▶ Presentation tour** that walks through the eight parts of the platform.

## Running it

**Presentation or training (recommended):** fills a separate demonstration database. Your real database is not touched.

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
- Administrators set roles in **Platform Management → Accounts**.
- **Citizen Science Monitors** see the planner dashboard with live data, read-only: figures, field channels, scheme performance, irrigation advice, nutrition and the map.
- **District Planners**, district officers and administrators also get the Act Now queue, case and feedback updates, SMS sending and Platform Management.
- The home page (`/`) shows live totals and recent activity from `GET /api/v1/public/overview`. It needs no sign-in and never returns names, phone numbers, message text or grievances.
- Sign-in sessions are stored in the database (only a hash of the token) and expire after 12 hours (`SESSION_HOURS`).
- Integrations can still use service API keys (`API_KEY_ROLES`).
- In demo mode (`ENVIRONMENT=development`) everything is open, so a presenter does not need to sign in.

## Useful scripts (`backend/scripts/`)

| Script | Use |
| --- | --- |
| `load_locations.py` | Load the 15 sectors and 72 cells from `data/*.gpkg`. No QGIS needed |
| `seed_reference_schemes.py` | Add PADAB and APEFA Solar with their published figures |
| `seed_demo_data.py` | Invented month of pilot activity, for demonstrations only |
| `create_admin.py` | Create or promote an administrator |
| `check_db.py`, `schema_audit.py` | Check the database connection, migration revision, and columns |
| `configure_api_key.py` | Generate a service API key in `.env` |
