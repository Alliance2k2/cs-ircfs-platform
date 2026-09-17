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

1. Install dependencies once: `python -m pip install -r backend/requirements.txt`.
2. In VS Code, open **Terminal → Run Task → CS-IRCFS: Start local platform**. Alternatively, run `powershell -ExecutionPolicy Bypass -File .\start-local.ps1` from the project root.
3. Open `http://127.0.0.1:8000` for the platform and `http://127.0.0.1:8000/docs` for interactive API documentation.
4. Keep the terminal running. Refresh the browser after changing HTML, CSS, or JavaScript. After a Python change, press `Ctrl+C` and start the task again.

The launcher creates `.env` from `.env.example` only when `.env` does not already exist. It never overwrites your current database or API-key settings. In VS Code, **Run and Debug → CS-IRCFS: Debug local platform** starts the same application with Python debugging enabled.
If you want Python auto-reload and your Windows setup supports it, run `powershell -ExecutionPolicy Bypass -File .\start-local.ps1 -Reload`.

The API has health, user registration, crop and irrigation/rainfall reports, feedback history, actionable report cases, a dashboard summary, and the prioritised **Act Now** planner queue at `/api/v1/analytics/act-now`. It runs with local SQLite until PostgreSQL/PostGIS is configured. Spatial boundary and farm endpoints return 501 on SQLite.
