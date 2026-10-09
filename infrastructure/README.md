# Deployment and handover

This folder is the deployment package for the Bugesera District IT unit or MINAGRI (architecture Section 5, Months 5–6). It runs two Docker containers:

| Container | What it is |
| --- | --- |
| `db` | PostgreSQL 16 with PostGIS. Data is kept in the `pgdata` volume. |
| `platform` | One FastAPI service. It serves the planner dashboard, the REST API, and the USSD and SMS callbacks. |

## First start

```powershell
cd infrastructure
copy stack.env.example stack.env      # then edit the secrets in stack.env
docker compose --env-file stack.env up -d --build
```

On every start, the platform container runs `alembic upgrade head` and then adds the PADAB and APEFA Solar reference schemes if they are missing. After that:

1. **Load Bugesera's sectors and cells** (15 sectors, 72 cells, with boundaries):
   `docker compose --env-file stack.env exec platform python scripts/load_locations.py`
2. **Create the first administrator:**
   `docker compose --env-file stack.env exec platform python scripts/create_admin.py it.officer@bugesera.gov.rw`
3. Open `http://<server>:8000/login.html` and sign in. Promote District Planners in **Platform Management → Accounts**.
4. In **Platform Management → Irrigation schemes → Edit figures**, enter the verified feasibility-study yield target for each scheme, with its source.

## Connecting the telecom gateway (Africa's Talking)

See [../ussd-sms/README.md](../ussd-sms/README.md). In short:

- point the USSD service code at `https://<server>/api/v1/ussd?token=<GATEWAY_CALLBACK_TOKEN>`
- point the SMS short code at `https://<server>/api/v1/sms/inbound?token=<GATEWAY_CALLBACK_TOKEN>`
- set `SMS_PROVIDER=africas_talking` (and `AIRTIME_PROVIDER` for rewards) with the account credentials

Both callbacks need a public HTTPS address. Put the platform behind the district's reverse proxy, for example nginx or Caddy with a TLS certificate.

## Operations

| Task | Command |
| --- | --- |
| View logs | `docker compose --env-file stack.env logs -f platform` |
| Back up the database | `docker compose --env-file stack.env exec db pg_dump -U cs_ircfs cs_ircfs > backup-%DATE%.sql` |
| Restore a backup | `type backup.sql \| docker compose --env-file stack.env exec -T db psql -U cs_ircfs cs_ircfs` |
| Update to a new version | `git pull`, then `docker compose --env-file stack.env up -d --build` (migrations run automatically) |
| Check the database | `docker compose --env-file stack.env exec platform python scripts/check_db.py` |

Schedule a daily `pg_dump`, and keep copies off the server.
