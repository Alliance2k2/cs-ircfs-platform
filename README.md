# CS-IRCFS Platform

[Deploy to Render](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2FAlliance2k2%2Fcs-ircfs-platform)

> A low-bandwidth platform for agricultural, irrigation, climate, and community-issue monitoring in Bugesera, Rwanda.

## What works today

| Capability | Status | Evidence |
| --- | --- | --- |
| FastAPI reporting, users, feedback, and case workflow | Working locally | `/api/v1/*` endpoints and API test |
| Planner dashboard and Act Now case actions | Working with local API | `dashboard/index.html` |
| Irrigation phone-flow demonstration | Simulator only | Saves a report through the API; no telecom gateway |
| SMS response | Simulator only | Records a notification timestamp; sends no message |
| PADAB/APEFA outcomes and example counts | Demonstration data | Not verified field evidence |
| Real USSD/SMS gateway, verified boundaries, backups and deployment | Planned | Requires field and operations decisions |

The main platform flow is **report → verify → case → assign and act → resolve → record response → measure**. The local API intentionally permits administrator access in development. Production needs individual authentication, area-level authorization, approved provider integration, verified geography, and operational controls before real personal data is used.

## Purpose

Community users submit structured reports through USSD or SMS. The platform validates and stores them, then gives District Planners a web dashboard, maps, analytics, and follow-up tools for better decisions.

**Start here:** [Simple Project Guide](docs/00-how-to-use-this-project.md). It explains the difference between the main planner platform and the technical backend.
For exact live metric definitions and remaining production gates, see [Current System and Metrics](docs/07-current-system-and-metrics.md).
For a GitHub-backed hosted preview, see [Deployment](docs/10-deployment.md). The hosted preview requires a separate PostgreSQL database and API key; it does not copy local records.

## Project structure

```text
cs-ircfs-platform/
├── docs/             # requirements, architecture, data model, roadmap, current limits
├── backend/          # FastAPI service, database migrations, and API tests
└── dashboard/        # planner and management pages
```

## Source brief

The requirements were organized from `../Steps_of_creating_platform.pdf` and `../cs-ircfs-platform-architecture.docx`. Start with [docs/05-platform-blueprint.md](docs/05-platform-blueprint.md) for the platform vision, then use the supporting requirement and engineering documents.

## Delivery sequence

1. Confirm field requirements and terminology.
2. Build the database and FastAPI foundation.
3. Deliver USSD/SMS reporting flows.
4. Deliver the district dashboard and map.
5. Add analytics, test end-to-end, run the Bugesera pilot, improve, then deploy.

The detailed scope and acceptance criteria are in [docs/04-delivery-roadmap.md](docs/04-delivery-roadmap.md).

For the competition story, feature priorities, and live-demonstration flow, see [docs/06-competitive-strategy.md](docs/06-competitive-strategy.md).

## Start the local API

1. Copy `.env.example` to `.env`.
2. From `backend`, install dependencies: `python -m pip install -r requirements.txt`.
3. Start it: `python -m uvicorn app.main:app --reload`.
4. Open `http://127.0.0.1:8000/docs` to use the interactive API documentation.

The API has health, user registration, crop and irrigation/rainfall reports, feedback history, actionable report cases, a dashboard summary, and the prioritised **Act Now** planner queue at `/api/v1/analytics/act-now`. It runs with local SQLite until PostgreSQL/PostGIS is configured. Spatial boundary and farm endpoints return 501 on SQLite.
