# How the backend works

The backend is a FastAPI application (`backend/app/`). Every group you see in the interactive reference at `/docs` is one file in `backend/app/api/routes/`, and most of the work is done by helper modules in `backend/app/services/`. This page explains each group in the order `/docs` shows it: what it is for, who may use it, each endpoint, and the rules behind it.

## Before the groups: three ideas used everywhere

**1. Who is asking (the "principal").** Every protected request is identified by `get_current_principal` (`core/security.py`), in this order:

1. A browser sends the session cookie set at sign-in, or an API client sends `Authorization: Bearer <token>`. The token is looked up by its SHA-256 hash in `auth_sessions`; expired sessions, unknown tokens, and accounts that are not `active` are refused.
2. Otherwise a service may send `X-API-Key`; the key's role comes from `API_KEY_ROLES` in `.env`.
3. Local development only (`ENVIRONMENT=development` and `REQUIRE_API_KEY=false`): everyone is treated as an administrator. Production refuses to start in this mode.

**2. Roles.** Each endpoint names the roles it accepts with `require_roles(...)`; anyone else gets `403`. The roles are: farmer, Citizen Science Monitor, cooperative leader, district officer, district planner and administrator. In the tables below, "staff" means district officer, district planner and administrator.

**3. Area of work.** An account can be limited to some sectors (Administration → Accounts). `allowed_cells()` (`core/scope.py`) turns that into a list of cells, and record lists are filtered to those cells. Administrators and accounts with no sectors see the whole district.

Two more rules apply across groups:

- **Data origin.** Every report, grievance, survey and inbound message is marked `field`, `simulator`, `demo` or `import`. Simulator tests are never counted in figures, reports or the evaluation (`services/evidence.py`, `counted()`).
- **Audit log.** Changes made by staff (accounts, cases, grievances, verification, schemes, exports, advice sends) are written to `audit_events` (`services/audit.py`).

Errors come back as JSON with a `detail` message. A database failure returns `500` with "Database operation failed" and the full error goes to the server log only.

---

## 1. system

Health checks used by hosting platforms and monitors. No sign-in.

| Endpoint | What it does |
| --- | --- |
| `GET /health` | Answers `{"status": "ok"}` when the server runs. Render, Docker and the dashboard's "Platform online" badge use it |
| `GET /api/v1/auth-status` | Says whether service API keys are configured, without revealing them |

## 2. authentication

Web accounts for district staff and monitors (`routes/auth.py`). Farmers do not need an account: they use USSD and SMS.

| Endpoint | Who | What it does |
| --- | --- | --- |
| `GET /auth/config` | anyone | Tells the sign-in page whether Google sign-in is set up and whether the development bypass is on |
| `POST /auth/register` | anyone | Creates an account as **Citizen Science Monitor** with status **pending**. Nobody can register as planner or administrator |
| `POST /auth/login` | anyone | Checks email and password; starts a session |
| `POST /auth/google` | anyone | Same, with a Google credential (verified with Google; the email must be verified). A first Google sign-in creates a pending account |
| `GET /auth/me` | signed in | Who you are: name, role, status and area. The dashboard calls it on every page load |
| `POST /auth/logout` | signed in | Deletes the session and clears the cookie |
| `GET /auth/accounts` | administrator | All accounts |
| `PATCH /auth/accounts/{id}` | administrator | Change role, status (`active`, `pending`, `suspended`) and area (sector list). Audited |

**How sign-in works, step by step:**

1. Passwords are never stored. `hash_password` stores `pbkdf2$210000$<salt>$<hash>`: PBKDF2-SHA256 with a random salt and 210 000 rounds, so a stolen database does not reveal passwords. `verify_password` compares in constant time.
2. A pending or suspended account is refused with a clear message, but only after the password is correct, so the status is not revealed to strangers.
3. `start_session` creates a random 256-bit token, stores only its hash with an expiry (`SESSION_HOURS`, 12 by default) and returns the token.
4. The token is also set as a cookie: `httpOnly` (scripts cannot read it), `SameSite=Lax`, and `Secure` in production (HTTPS only).
5. Sign-in is limited to 10 attempts a minute per address, against password guessing.
6. Suspending an account deletes all its sessions at once.

## 3. field channels

How farmers' phones reach the platform (`routes/channels.py`, `services/ussd.py`, `services/sms_keywords.py`).

| Endpoint | Who | What it does |
| --- | --- | --- |
| `POST /ussd` | Africa's Talking | The `*801#` menu. Called once per key press with the whole session so far |
| `POST /sms/inbound` | Africa's Talking | SMS to `8448`, read as keywords |
| `POST /simulator/ussd` | field and staff roles | The same menu for the on-screen phone, with an English translation |
| `POST /simulator/sms` | field and staff roles | The same keywords for the on-screen phone |
| `GET /channels/activity` | field and staff roles | Latest messages received, SMS sent and airtime rewards |

**USSD.** A first-time caller is registered by phone number and asked for their sector and cell. After that the main menu is: 1 harvest, 2 pest or disease, 3 rainfall, 4 irrigation infrastructure, 5 grievance, 6 household nutrition. Each option is a short chain of numbered screens in Kinyarwanda; the last screen saves the record and thanks the caller.

**SMS keywords.** `IMVURA 12` / `RAIN 12` (rainfall), `NZANA` / `ARMYWORM` and `INDWARA` (pests and disease), `UMUSARURO` / `HARVEST` (harvest), `IKIBAZO` / `IGITEKEREZO` / `COMPLAINT` (grievance). A sector name can come first, e.g. `NYAMATA IMVURA 12`.

**Safeguards:**

- The gateway URLs must carry the secret `?token=` (`GATEWAY_CALLBACK_TOKEN`), optionally only from listed IP addresses, so nobody can post fake reports.
- At most 30 messages a minute per phone number.
- A gateway retry with the same session or message id gets the stored reply instead of creating a duplicate.
- **Grievances are anonymous**: the phone number of that whole USSD session, and of the SMS, is replaced by `withheld`, and the grievance never stores who sent it.
- Simulator records are marked `simulator`, and SMS or airtime from the simulator is always dry-run.
- Monitors and cooperative leaders see masked phone numbers and no message text in the activity list.

## 4. farmer advisory

Irrigation advice and outgoing SMS (`routes/advisory.py`, `services/advisory.py`).

| Endpoint | Who | What it does |
| --- | --- | --- |
| `POST /advisory/sms` | planner, administrator | Send one SMS to one phone |
| `GET /advisory/messages` | staff | SMS sent, newest first |
| `GET /advisory/incentives` | staff | Airtime rewards |
| `GET /advisory/irrigation-schedule` | monitor and staff | For each sector: 7-day rain-gauge total, forecast, level and advice in English and Kinyarwanda |
| `GET /advisory/weekly-advice` | monitor and staff | Whether automatic weekly sending is on, and the last run |
| `POST /advisory/irrigation-schedule/send` | planner, administrator | Send each sector's advice to its cooperative leaders and monitors. With `"preview": true` it only counts recipients |

**How advice is decided.** Each sector's rain-gauge readings over the last 7 days give a rainfall figure. Below the dry threshold (10 mm by default) the advice is *irrigate more* (about 10% more this week); above the wet threshold (40 mm) *irrigate less*; otherwise *normal*; with no readings, *no data*, asking gauge holders to report. If the Open-Meteo forecast for the next 7 days is at least twice the dry threshold, a dry week becomes *normal* ("check again in 2–3 days") instead of *irrigate more*. Per-sector thresholds come from the `advisory_thresholds` table (set with `scripts/calibrate_rainfall_thresholds.py`) and are shown with their source; without them the defaults apply.

**Airtime rewards.** Every 3rd counted report from a person (rainfall, infrastructure and nutrition by default) earns 100 RWF of airtime; nutrition surveys count at most once a month per household. Until live credentials exist, rewards and SMS are recorded as `dry_run`.

## 5. calibration

Lists the field menus use, kept editable (`routes/calibration.py`). Reading is for staff; changing is for administrators.

| Endpoint | What it does |
| --- | --- |
| `GET`/`POST`/`PATCH`/`DELETE /grievance-categories` | The grievance categories offered in USSD option 5 |
| `GET`/`POST`/`PATCH`/`DELETE /scheme-assets` | The named pumps, canals and solar arrays offered in USSD option 4 |

An item that records already use cannot be deleted (`409`); deactivate it instead, so old records keep their meaning.

## 6. cooperatives

| Endpoint | Who | What it does |
| --- | --- | --- |
| `GET /cooperatives` | staff | The cooperatives |
| `POST`, `PATCH /cooperatives` | planner, administrator | Add or edit (name, sector, scheme, pilot flag, contact) |
| `DELETE /cooperatives/{id}` | planner, administrator | Refused while members still belong to it |
| `GET /cooperatives/participation` | staff | Per cooperative: members, Data Champions, reports and active reporters in 30 days and this month |
| `GET /cooperatives/training-progress` | staff | Trained monitors against the target (200) and pilot cooperatives against 3 |

## 7. field users

The people who use USSD and SMS (farmers, monitors, cooperative leaders), keyed by phone number (`routes/field_users.py`).

| Endpoint | Who | What it does |
| --- | --- | --- |
| `POST /field-users` | administrator | Register a person (phone, name, role, cooperative, cell, optional location). One person per phone number |
| `GET /field-users` | staff | List and search, within the area of work |
| `PATCH /field-users/{id}` | administrator | Edit, deactivate, mark as Data Champion or trained |
| `DELETE /field-users/{id}` | administrator | Only when no record refers to the person; otherwise deactivate |

Most field users register themselves by dialling `*801#` for the first time.

## 8. irrigation schemes

| Endpoint | Who | What it does |
| --- | --- | --- |
| `POST /irrigation-schemes` | administrator | Add a scheme |
| `GET /irrigation-schemes` | all roles | PADAB, APEFA Solar and any others, with their baseline |
| `PATCH /irrigation-schemes/{id}` | administrator | Edit partner, hectares, location and the **yield target**. A target is refused without its source document. Audited |

## 9. reference data

`GET /sectors` and `GET /cells`: the 15 sectors and 72 cells of Bugesera, loaded from the district boundary files (`scripts/load_locations.py`). Used by every filter and form.

## 10. reports

Reports entered on the web or by an integration (USSD and SMS use the same helpers in `services/reporting.py`, so a phone report and a web report follow the same rules).

| Endpoint | Who can send / read | What it does |
| --- | --- | --- |
| `POST`, `GET /citizen-reports` | field roles send; field and staff read | Crop reports: crop, planting, expected and harvested tons, pest or disease with severity 1–5 |
| `POST`, `GET /irrigation-reports` | same | Rain-gauge readings and asset condition (operational, faulty, offline, with a bottleneck category) |
| `POST /nutrition-surveys` | field roles | Household screening: meals a day, protein or vegetables, enough food |
| `GET /nutrition-surveys` | **staff only** | Individual household answers are personal data |

**What happens automatically when a report arrives:**

- Severity 4–5 pests and faulty or offline assets **open an incident case** (high or critical), which appears in Priority actions. Critical cases also SMS the staff numbers in `ALERT_PHONE_NUMBERS`.
- A nutrition survey gets a **risk score** from 1 (low) to 5 (high): fewer meals, no protein or vegetables and not enough food each add risk.
- Every reference (reporter, scheme, cell) is checked to exist.

## 11. feedback (grievances)

| Endpoint | Who | What it does |
| --- | --- | --- |
| `POST /feedback` | field roles, administrator | Submit a grievance on the web. The sender is never stored |
| `GET /feedback` | staff | Grievances in the area of work |
| `PATCH /feedback/{id}` | staff | Change status, owner (a field user), deadline, action taken. Resolving or closing needs the action taken. Every change is a history event and audited |
| `GET /feedback/{id}/history` | staff | All status changes |
| `POST /feedback/{id}/notify-cell` | staff | **Closing the loop**: tell everyone registered in the grievance's cell what was done. With `"preview": true` it only counts recipients. Only after resolution |

Statuses: open → triaged → assigned → in progress → resolved → closed.

## 12. cases

Incident cases opened automatically from serious reports (see Reports).

| Endpoint | Who | What it does |
| --- | --- | --- |
| `GET /cases`, `GET /cases/{id}` | staff | Cases in the area of work |
| `PATCH /cases/{id}` | staff | Status, owner (a staff account), deadline, action taken; same rules as grievances. An `assigned` case needs an owner |
| `GET /cases/{id}/history` | staff | Status changes |
| `POST /cases/{id}/notify-cell` | staff | Closing-the-loop SMS to the report's cell, with preview |
| `POST /cases/{id}/simulate-notification` | staff | Older demonstration helper: marks the reporter as notified without sending anything. The new dashboard does not use it |

## 13. analytics

Figures for the dashboards (`services/analytics.py`, `services/executive.py`, `services/reporting.py`). All leave out simulator tests.

| Endpoint | Who | What it does |
| --- | --- | --- |
| `GET /analytics/executive-overview` | monitor and staff | The new overview: each figure with value, unit, period, definition and source (citizen report, documented, demonstration, missing), plus schemes, assets, rainfall, priority actions and recent reports. Filters: days, scheme, sector |
| `GET /analytics/act-now` | staff | Open cases and grievances, most urgent first |
| `GET /analytics/scheme-performance` | monitor and staff | Per scheme: harvest reports against target, bottlenecks and recurring problems |
| `GET /analytics/response-health` | monitor and staff | How fast concerns are resolved and answered |
| `GET /analytics/pest-heatmap` | monitor and staff | Pest alerts as weighted points (90 days) |
| `GET /analytics/rainfall-map` | monitor and staff | 7-day rainfall per cell with its advice level |
| `GET /analytics/nutrition-summary` | monitor and staff | Screening by cell; **cells with fewer than 5 households show no scores** |
| `GET /analytics/trends` | monitor and staff | Twelve months, month by month |
| `GET /analytics/monthly-report` | monitor and staff | One month against the month before (`?month=2026-09`) |
| `GET /analytics/dashboard-summary` | monitor and staff | Older summary used by the classic dashboard |
| `GET /analytics/farmer-summary` | staff | Older summary; only its farmer and report counts are real (see "Known issues") |

## 14. map

`GET /map-data` (all roles): points for the classic map and the new District map: schemes, asset and rain readings, crop reports and registered farmers, within the area of work. On SQLite it returns points only; boundaries need PostGIS.

## 15. geography

Boundaries as GeoJSON, PostGIS only (empty on SQLite): `GET /geography/sectors`, `GET /geography/cells` and `GET /geography/farmers` (registered farmers who have a location). All roles.

## 16. public

No sign-in; used by the public home page.

| Endpoint | What it does |
| --- | --- |
| `GET /public/map-config` | The Mapbox public token and style. A secret `sk.` token is never sent |
| `GET /public/overview` | Live totals, recent activity and this week's advice per sector: counts and sector names only, never names, phone numbers, message text or grievances. Simulator tests left out |

## 17. field reports

The unified, checked list of crop and infrastructure reports for the Field reports page (`routes/field_reports.py`, `services/field_reports.py`).

| Endpoint | Who | What it does |
| --- | --- | --- |
| `GET /field-reports` | field and staff roles | Newest 500 reports with filters (type, days, sector, scheme, verification, origin) and **automatic checks**: no location, no scheme, missing value, unusual value (rain over 150 mm, harvest over 50 t), possible duplicate (same person and subject within 24 h). Monitors and leaders see masked reporters |
| `GET /field-reports/{source}/{id}` | same | One report with its case and verification history |
| `PATCH /field-reports/{source}/{id}/verification` | staff | Verified, rejected (reason required) or back to unverified. Audited |
| `GET /field-reports/export.csv` | staff | The filtered list as CSV, without names or phone numbers. Audited |

## 18. irrigation command centre

| Endpoint | Who | What it does |
| --- | --- | --- |
| `GET /irrigation/assets` | field and staff roles | Each asset's **latest** condition (not every fault ever reported), fault count, open cases, and inventory assets never reported |
| `GET /irrigation/assets/history` | same | Every condition report for one asset |

## 19. evaluation

The PADAB and APEFA evaluation lab (`services/evaluation.py`).

| Endpoint | Who | What it does |
| --- | --- | --- |
| `GET /evaluation?days=365` | monitor and staff | The five evaluation questions answered per scheme from recorded evidence: baseline and its source, outcomes, bottlenecks, beneficiary feedback, downstream communities, evidence quality |
| `GET /evaluation/export.csv` | staff | The same as CSV. Audited |

**Yield achievement** (`100 × observed ÷ target`) is returned as "not computable" with the list of missing requirements, until harvest reports record harvested area, crop and season and each target states crop, unit and season. Nothing is estimated or modelled.

## 20. administration

| Endpoint | Who | What it does |
| --- | --- | --- |
| `GET /admin/assignees` | staff | Active staff a case can be assigned to (names and roles only) |
| `GET /admin/audit` | administrator | The audit log, newest first, filterable by action and record type |

---

## Known issues found while writing this page

These are in the code today and are recorded in [remaining-work.md](remaining-work.md):

1. **Generated map positions.** `/map-data` places a report that has no GPS point at its cell's centre plus a small fixed offset, so several reports from one cell can be clicked separately. Those positions are not recorded coordinates, but the maps draw them like real ones.
2. **Farmer names and home locations for every role.** `/map-data` and `/geography/farmers` return registered farmers' names and locations to every signed-in role, including farmers and cooperative leaders.
3. **Report notes on the map.** `/map-data` includes crop-report notes for every role, while `/field-reports` hides notes from monitors and leaders.
4. **Simulator rows on the map.** `/map-data` does not leave out simulator tests.
5. **`/analytics/farmer-summary`** returns fixed zeros for schemes, complaints and assets. Only the classic pages call these older summaries.
