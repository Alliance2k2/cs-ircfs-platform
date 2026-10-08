# CS-IRCFS Platform

[Deploy to Render](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2FAlliance2k2%2Fcs-ircfs-platform)

> Citizen Science for Irrigation Resilience and Climate-smart Food Security in Bugesera, Rwanda. Citizens report from any phone through **USSD `*801#`** and **SMS `8448`**. District Planners use the evidence to verify whether the **PADAB** and **APEFA Solar** irrigation schemes deliver their expected outcomes, and to find where they fall short.

```text
Farmers · Citizen Science Monitors · Cooperatives   (feature phone, no internet)
        │  USSD *801#  ·  SMS 8448   (Kinyarwanda first)
        ▼
Africa's Talking gateway  ──►  FastAPI  ──►  PostgreSQL / PostGIS
                                               │
        ┌──────────────────────────────────────┘
        ▼
Planner dashboard: outcome verification · bottleneck detection · Act Now
        │
        └──►  SMS back to citizens: tips · irrigation advice · airtime · closing the loop
```

## Quick start

```powershell
python -m pip install -r backend/requirements.txt
.\start-local.ps1 -Demo        # presentation data in a separate demo.db
```

Open **http://127.0.0.1:8000**. In VS Code you can use **Terminal → Run Task → CS-IRCFS: Start demo** instead. Use `.\start-local.ps1` (without `-Demo`) for your real PostgreSQL. It applies migrations first.

| Page | What you can do |
| --- | --- |
| `/planner.html` | Act Now queue, live field messages, scheme performance against targets, response health, 12-month trends, irrigation advice, nutrition risk, layered map, **▶ presentation tour**, EN/RW |
| `/simulator.html` | Dial `*801#` or text `NYAMATA NZANA 5` on an on-screen phone and watch the record appear |
| `/management.html` | People, schemes (verified yield targets), reports, feedback, nutrition, SMS log, accounts and roles |
| `/docs` | Interactive API reference |

## What it does (architecture Modules 1–3)

| Module | Features |
| --- | --- |
| **1. Citizen science and food security** | Crowdsourced yield forecaster compared with scheme targets · SMS pest alerts with heatmap · household nutrition tracker (stunting risk) |
| **2. Irrigation resilience and climate** | Infrastructure health reporter with bottleneck categories and auto-flagging · citizen rain-gauge network and drought map · irrigation scheduling assistant (SMS advice) |
| **3. Community feedback loops** | Anonymous grievance log, including resettlement and downstream impacts · closing-the-loop SMS to the affected cell |
| **Participation (§8)** | Airtime reward every 3rd weather report · local tips after every report · cooperative Data Champion roles · Kinyarwanda, numeric, ≤3 menu levels |

## Project structure

```text
cs-ircfs-platform/
├── backend/            FastAPI service
│   ├── app/api/routes/   channels (USSD/SMS), reports, cases, feedback, analytics, advisory, auth, …
│   ├── app/services/     ussd.py, sms_keywords.py, reporting.py, advisory.py, notifications.py, sms.py
│   ├── migrations/       Alembic versions 01–08
│   ├── scripts/          load_locations, seed_demo_data, create_admin, check_db, …
│   └── tests/            API, USSD, SMS, closing-the-loop, analytics, and sign-in tests
├── dashboard/          Web pages served at /  (planner, simulator, management, sign-in)
├── ussd-sms/           Menu map, SMS keywords, Africa's Talking setup
├── infrastructure/     Docker Compose (PostGIS + platform) and operations guide for handover
├── data/               Bugesera sector and cell boundaries (GeoPackage)
├── docs/               Guides (older documents are in docs/archive/)
├── scripts/            Repository utilities (architecture reader, QGIS location import)
├── frontend/           Experimental React draft, not used
├── Dockerfile, render.yaml, start-local.ps1, start-platform.bat
└── cs-ircfs-platform-architecture.docx
```

## Documentation

1. [Platform guide](docs/01-platform-guide.md): pages, roles, running, scripts
2. [Architecture alignment](docs/02-architecture-alignment.md): every architecture item and where it is implemented
3. [Data model](docs/03-data-model.md)
4. [Deployment](docs/04-deployment.md): demo, Docker, Render, production checklist
5. [Presentation demo script](docs/05-presentation-demo-script.md)
6. [Roadmap and current limits](docs/06-roadmap-and-limits.md)
7. [USSD and SMS channels](ussd-sms/README.md) · [Handover stack](infrastructure/README.md)

## Tests

```powershell
cd backend
python -m pytest -q -p no:cacheprovider
```

Tests always use an in-memory database (`tests/conftest.py`). They never touch the database in `.env`.

## Status

All features above work end to end through the simulator and the API. Two things are needed before real field use:

- Africa's Talking credentials. Until then, outgoing SMS and airtime are logged as `dry_run`.
- The official PADAB and APEFA yield targets.

See [roadmap and limits](docs/06-roadmap-and-limits.md). Never commit `.env` or `infrastructure/stack.env`.
