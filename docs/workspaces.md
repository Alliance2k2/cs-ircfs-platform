# Workspaces

The district dashboard at `/app/` is a React application (`frontend/`). Every page here has the same frame: a page header that states the page's purpose and when its data was last loaded, loading skeletons, an empty state that says how data arrives, and an error state with a retry. Figures come only from the API; nothing is estimated in the browser.

Who can open a page follows the backend's role checks (`frontend/src/components/navigation/nav.ts`). The menu hides pages a role cannot use, and opening one by address shows who the page is for. The backend refuses the same requests, so hiding a link is a convenience, not the protection.

| Access level | Roles |
| --- | --- |
| field | Citizen Science Monitor, cooperative leader, district officer, district planner, administrator |
| analyst | Citizen Science Monitor, district officer, district planner, administrator |
| staff | district officer, district planner, administrator |
| planner | district planner, administrator |
| admin | administrator |

A role that cannot see the executive overview (cooperative leader, farmer) starts on the first page it may use.

## Dashboard

### Executive overview — `/app/` (analyst)

Headline figures with their period, source and definition; the priority queue; asset health; scheme comparison; rainfall advice map; recent reports. API: `GET /api/v1/analytics/executive-overview`. See [design-system.md](design-system.md) for how a figure is labelled.

### Priority actions — `/app/actions` (staff)

Open incident cases and grievances, most urgent first. Opening one shows a side panel to change the status, assign an owner (district staff for cases, a registered field user for grievances), set a deadline and record the action taken. Resolving or closing needs the action taken. Every save adds a status event, shown as the item's history.

**Tell the community by SMS** is available once the item is resolved. It first shows how many people registered in the affected cell would receive the message and the message itself; nothing is sent until **Send** is pressed. Links of the form `/app/actions?open=infrastructure-5` open an item directly (used by the notification bell and the overview).

APIs: `GET /analytics/act-now`, `GET|PATCH /cases/{id}`, `GET /cases/{id}/history`, `POST /cases/{id}/notify-cell`, `GET|PATCH /feedback/{id}`, `POST /feedback/{id}/notify-cell`, `GET /admin/assignees`, `GET /field-users`.

## Field intelligence

### Field reports — `/app/field-reports` (field)

Every crop, pest, rainfall and infrastructure report, filterable by type, period, sector, scheme, verification and data origin. Each report carries automatic checks: no location, no scheme, missing value, unusual value (rain above 150 mm, harvest above 50 t) and possible duplicate (same reporter and subject within 24 hours). Checks are hints for verification, not errors.

Staff can mark a report verified, reject it (a reason is required) or return it to unverified; each decision is in the audit log and in the report's verification history. **Export CSV** (staff) downloads the filtered list without names or phone numbers. Monitors and cooperative leaders see masked phone numbers and no notes. At most 500 reports are listed; a notice says when the list is cut.

APIs: `GET /field-reports`, `GET /field-reports/{source}/{id}`, `PATCH /field-reports/{source}/{id}/verification`, `GET /field-reports/export.csv`.

### Crops & pests — `/app/crops` (analyst)

Reports by crop, pest alerts by severity and sector, the most reported pests, expected and reported harvest by crop, and plantings and severe pest alerts by month. Harvest figures come from a sample of farmers and are not total production.

### Food & nutrition — `/app/nutrition` (analyst)

Household screening answers by cell. Cells with fewer than five households show the household count only; their scores are hidden so that no family can be singled out. The same rule applies to the monthly report and to monthly averages in trends. Scores are risk screening, not a diagnosis.

## Water & climate

### Irrigation command centre — `/app/irrigation` (field)

Each named pump, canal and solar array with its latest reported condition, bottleneck, fault reports and open cases, plus inventory assets that have never been reported. Opening an asset shows its full condition history. APIs: `GET /irrigation/assets`, `GET /irrigation/assets/history`.

### Climate & advice — `/app/climate` (analyst)

Seven-day rain-gauge totals per sector, the Open-Meteo forecast, the dry and wet thresholds with their source ("starting values, not yet calibrated" until calibrated) and the advice each sector receives in English and Kinyarwanda. **Send advice by SMS** (planner) previews the number of recipients per sector before anything is sent. The weekly automatic send status is shown below.

### District map — `/app/map` (all)

Mapbox map of Bugesera with layers for infrastructure, crop reports, a pest heatmap and rainfall readings; analysts also get nutrition risk per cell (cells with five or more households only). Map, satellite and terrain bases and a 3D view are in the map's corner. Only coordinates stored with records are drawn. Grievances and households are never mapped. Without `MAPBOX_ACCESS_TOKEN` the page explains how to add one.

## Evaluation

### PADAB & APEFA evaluation — `/app/evaluation` (analyst)

The five evaluation questions answered scheme by scheme from recorded evidence only: documented baseline (with its source, or marked as a demonstration value or not entered), observed outcomes, bottlenecks, beneficiary feedback, affected and downstream communities, and evidence quality (located, verified and demonstration shares, months with reports). Yield achievement is shown only when it can be computed validly; otherwise the page lists each missing requirement. **Export CSV** (staff) and **Print** produce the same evidence for reports.

## Community

### Grievances — `/app/grievances` (staff)

Anonymous concerns from USSD option 5 and the `IKIBAZO` SMS keyword. No phone number or name is stored with a grievance; the cell is kept only so the answer can go to everyone registered there. Opening a grievance gives the same work panel as Priority actions.

### Cooperatives — `/app/cooperatives` (staff)

Participation per cooperative over 30 days, Data Champions, and progress against the monitor-training and pilot-cooperative targets. Planners and administrators add and edit cooperatives. Report counts show activity, not quality.

## Communications

### USSD & SMS operations — `/app/channels` (field)

Messages received, SMS sent and airtime rewards, newest first, with simulator tests marked. Monitors and cooperative leaders see masked numbers and no message text.

### Phone simulator — `/app/simulator` (field)

A phone on screen for `*801#` and SMS to `8448`, with an English translation of each USSD screen and a trace of every request. Records are stored as simulator data: they appear in operations, never in field reports, metrics or evaluation, and nothing is sent to a telecom provider.

## Reports

### Trends — `/app/trends` (analyst)

Twelve months of reports, severe pest alerts, asset faults, cases opened and resolved, grievances, harvest and rainfall, as charts or as one table.

### Monthly report — `/app/monthly-report` (analyst)

One month compared with the month before: headline figures with their change, schemes, cases, grievances, pests, rainfall, nutrition (small groups hidden), sector activity and airtime rewards. Pick a month, then **Print**. The month is kept in the address (`?month=2026-09`) so a report can be shared.

## Administration — `/app/admin` (admin)

- **Accounts**: approve new registrations, suspend and reactivate, change roles (each asks for confirmation) and set an account's area of work (sectors). Administrators cannot change their own role or status here.
- **Scheme baselines**: yield target, its source document, implementing partner and hectares developed. A target without a source is refused.
- **Audit log**: who changed what, newest first, searchable.

Administration and **Platform management** (the classic `/management.html`, which still holds field users, grievance categories, the asset inventory, nutrition surveys and the SMS log) stay pinned at the bottom of the sidebar for administrators, and are also in the account menu.

## The shell

- **Search pages** (Ctrl+K): jump to any page the role can open.
- **Notification bell** (staff): open priority actions, linking straight to each item.
- **Account menu**: name, role, area, public site and sign out.
- **EN / RW**: Kinyarwanda text falls back to English where a translation is missing (see [remaining-work.md](remaining-work.md)).
- The sidebar collapses to icons on large screens (remembered on the device) and becomes a drawer on phones.

The classic pages (`/planner.html`, `/management.html` and the others) still work and use the same API; they will be retired once the district has used the new pages.
