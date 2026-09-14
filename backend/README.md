# CS-IRCFS Backend

## Clean structure

```text
app/
├── api/routes/       # system, users, reference data, reports, feedback, analytics
├── core/             # settings, logging, API-key role protection
├── db/               # SQLAlchemy models and database session
├── services/         # shared business rules and foreign-key validation
├── schemas.py        # request/response validation contracts
└── main.py           # application setup only
migrations/           # Alembic database versions
tests/                # automated API tests
```

## Local development

```powershell
python -m uvicorn app.main:app --reload
python -m pytest -q tests
```

If pytest cannot access the system temporary directory on Windows, run `python -m pytest -q -p no:cacheprovider -p no:tmpdir tests`.

For a new database, run `alembic upgrade head`. Actionable crop reports (severity 4 or 5) and offline/faulty irrigation reports create incident cases automatically. Planners can list and update `/api/v1/cases`, inspect `/{id}/history`, and record a demonstration response via `/{id}/simulate-notification`. Resolved cases leave the Act Now queue. This notification endpoint sends no SMS.

SQLite supports basic reports and point coordinates for local demonstration. Farm and boundary geometry endpoints require PostgreSQL/PostGIS and return 501 on SQLite.

`DELETE /api/v1/users/{id}` permanently removes a user only if no reports, farms, feedback, or case history reference the account. Otherwise it returns 409; an administrator can set `is_active=false` with `PATCH` to preserve historical records. The management page offers this deactivation path when deletion is blocked.

Administrators can create irrigation schemes through `POST /api/v1/irrigation-schemes`. The management forms use this endpoint and the existing user, crop-report, irrigation-report, and feedback creation endpoints.

## Pilot/production checklist

1. Set `ENVIRONMENT=production` and a PostgreSQL connection in `.env`.
2. Set `REQUIRE_API_KEY=true` and configure `API_KEY_ROLES` with secret keys stored outside source control.
3. Run `alembic upgrade head` before starting the application.
4. Set up backups, monitoring, and HTTPS at the deployment environment.

Never commit a real `.env` file or API keys.

The local PostgreSQL setup uses the ignored project `.env` file. Run `python check_db.py` to confirm connectivity and the Alembic revision, then `python -m alembic upgrade head` when a migration is pending. `python configure_api_key.py` creates an administrator key only if no key is configured; use `python configure_api_key.py --rotate` if a key is exposed. Restart the API after changing `.env`. For a loopback preview, run `python -m uvicorn app.main:app --host 127.0.0.1 --port 8002`; the dashboard can use `http://127.0.0.1:8080/?api=http://127.0.0.1:8002/api/v1`. On connecting, enter the key portion before `:administrator` in `API_KEY_ROLES` from `.env`. The dashboard keeps it in browser session storage for that tab's session.

API keys currently identify a role, not an individual user or permitted district area. Individual authentication, ownership checks, privacy rules for anonymous feedback, and a verified delivery provider are required before production use.
