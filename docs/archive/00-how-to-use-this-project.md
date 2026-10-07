# CS-IRCFS — Simple Project Guide

There is one platform for day-to-day use and one technical service behind it.

## 1. Main platform: District Planner Dashboard

Open `http://127.0.0.1:8080`.

This is the main platform that District Planners will use. It shows:

- overview numbers: farmers, reports, schemes, and complaints
- **Act Now**: the urgent work queue
- PADAB and APEFA outcome scorecards
- community-response health
- map and observations

For now, it displays labelled **demonstration data**. When the backend is running, select **Connect local API** to load data stored by the local platform.

## 2. Backend: the engine behind the platform

The backend is not a second planner platform. It works in the background to manage these connected modules:

- irrigation schemes: PADAB, APEFA, assets, targets, and status
- users: farmers, monitors, cooperative leaders, planners, and administrators
- citizen reports: crops, planting, harvest, pests, and diseases
- rainfall and irrigation reports: rain gauges, pumps, canals, faults, and bottlenecks
- community feedback: complaints, assignment, follow-up action, and resolution history
- locations: sectors and cells
- analytics: dashboard metrics and the Act Now priority queue

It then performs this flow:

1. receive reports from USSD, SMS, or web forms
2. validate the submitted information
3. store it in the database
4. identify urgent reports
5. send information to the planner dashboard

The backend code is in `backend/app/`. Its developer test page is `http://127.0.0.1:8000/docs`.

## 3. Technical Operations Console

Open `http://127.0.0.1:8080/management.html` to manage users, irrigation schemes, citizen reports, rainfall/irrigation reports, feedback, locations, and analytics in one consistent system screen.

## Current development status

| Part | Status | What it means |
| --- | --- | --- |
| Planner dashboard | Ready as a visual demonstration | Uses examples until real reports are entered. |
| Backend API | Running locally | Can receive and return users, crop reports, irrigation/rainfall reports, feedback, and urgent alerts. |
| Database | Local development database | It will become PostgreSQL/PostGIS for pilot/production. |
| USSD/SMS | Planned, not connected | Requires the approved provider, shortcode, Kinyarwanda menu, and testing. |
| Real PADAB/APEFA data | Not added yet | Must come from confirmed official records and pilot reporting. |

## The simple story of the platform

```text
Farmer / monitor reports a problem
        ↓
Backend checks and stores it
        ↓
Planner sees it in Act Now
        ↓
Planner assigns action and closes the case
        ↓
Community receives a response
```

This is the single project flow we will continue building.
