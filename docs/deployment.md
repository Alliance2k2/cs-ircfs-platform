# Deployment

There are three ways to run the platform. All three use the same code.

| Option | For | How |
| --- | --- | --- |
| Local evaluation | Trying the platform, training | `.\start-local.ps1 -Demo` (separate `backend/demo.db` with sample data, no sign-in; builds the React dashboard on first run when Node.js is installed) |
| Local real database | Development against your PostgreSQL | `.\start-local.ps1` (runs migrations first) |
| Docker Compose | District IT / MINAGRI handover | [infrastructure/README.md](../infrastructure/README.md) |
| Render (hosted preview) | A shareable online demo | `render.yaml` Blueprint, described below |

## The React dashboard

The Docker image builds `frontend/` in a Node stage and serves the result at `/app/`; nothing extra is needed on the server. Locally, `start-local.ps1` builds it once. While changing the frontend, run the API and then `npm run dev` in `frontend/`: Vite serves the app on http://localhost:5173/app/ and forwards `/api` and the sign-in page to http://127.0.0.1:8000 (set `CS_IRCFS_API` to use another address).

## Hosted PostgreSQL (Neon)

The platform runs on any PostgreSQL with PostGIS, including Neon. Set `DATABASE_URL` to the connection string Neon gives (keep `?sslmode=require`); the platform adds the psycopg driver itself and re-checks pooled connections, which Neon closes when idle.

To move existing data to a new database:

```powershell
cd backend
$env:DATABASE_URL = "<new database URL>"; python -m alembic upgrade head; Remove-Item Env:DATABASE_URL
python scripts/copy_database.py --target "<new database URL>"   # source = DATABASE_URL in .env
```

The copy takes every platform table in one transaction and checks each row count; it refuses to overwrite a target that already has rows unless `--replace` is given. Then point `DATABASE_URL` in `.env` at the new database.

## Maps (Mapbox)

Every map (the executive overview and the classic Map page) is drawn with Mapbox GL. Create a **public** token (it starts with `pk.`) at account.mapbox.com, restrict it there to the site's URLs, and set `MAPBOX_ACCESS_TOKEN` (optionally `MAPBOX_STYLE`). The browser receives it from `/api/v1/public/map-config`; a secret `sk.` token is refused. Without a token each map says what to configure, and the lists next to it still work.

## Render hosted preview

1. Push this folder to GitHub, keeping `.env` out of Git.
2. Use the **Deploy to Render** link in the main README. When asked for `API_KEY_ROLES`, give a **new** `random-secret:administrator` value.
3. The container runs `alembic upgrade head` and adds the reference schemes on every start. Check `/health`.
4. Open the Render shell and run `python scripts/load_locations.py`, then `python scripts/create_admin.py you@example.org`.
5. Render's free PostgreSQL expires after 30 days and has no backups. Use it only for demonstrations, never for real citizen records.

## Before real citizen data (production checklist)

- [ ] `ENVIRONMENT=production`, `REQUIRE_API_KEY=true`, `COOKIE_SECURE=true`, an empty `CORS_ORIGINS` (same-origin dashboard) and a `GATEWAY_CALLBACK_TOKEN`; the platform refuses to start otherwise. Strong secrets, not reused from development.
- [ ] `FORWARDED_ALLOW_IPS` set to the reverse proxy's address so rate limits see real clients.
- [ ] HTTPS in front of the platform. The Africa's Talking callbacks need a public HTTPS URL.
- [ ] Africa's Talking credentials set, callback URLs ending in `?token=<GATEWAY_CALLBACK_TOKEN>`, and `SMS_PROVIDER` / `AIRTIME_PROVIDER` switched from `dry_run`.
- [ ] New staff accounts approved in Platform Management → Accounts (self-registered accounts start pending).
- [ ] The data protection impact assessment and registration required by Law N° 058/2021 completed by the district.
- [ ] The Kinyarwanda USSD screens reviewed with the field team and cooperative leaders.
- [ ] PADAB and APEFA yield targets, hectares and assets entered from official documents, with their sources.
- [ ] `DRY_SPELL_THRESHOLD_MM` / `WET_SPELL_THRESHOLD_MM` calibrated from Mwesa Valley and Ngeruka/Mareba rainfall records.
- [ ] Daily database backups (`pg_dump`) stored off the server, and a restore that has been tested.
- [ ] A consent message for first-time callers, and a data-retention policy agreed with the district.
- [ ] For officers who should see only their own sectors, set each account's **Area** in Platform Management → Accounts.

## Security notes

- Passwords are hashed with PBKDF2-SHA256 (210,000 rounds). Session tokens are stored only as SHA-256 hashes and expire.
- Self-registered accounts start pending and cannot choose a role. Only an administrator activates and promotes accounts.
- Suspending an account signs the person out immediately.
- The USSD and SMS callbacks are public URLs protected by `GATEWAY_CALLBACK_TOKEN`; `GATEWAY_ALLOWED_IPS` (or the reverse proxy) can also limit them to Africa's Talking's addresses. See [security.md](security.md).
- Outgoing messages and rewards are logged with their delivery status (`sent`, `dry_run`, `failed`).
