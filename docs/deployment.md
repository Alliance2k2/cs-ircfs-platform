# Deployment

There are three ways to run the platform. All three use the same code.

| Option | For | How |
| --- | --- | --- |
| Local evaluation | Trying the platform, training | `.\start-local.ps1 -Demo` (separate `backend/demo.db` with sample data, no sign-in) |
| Local real database | Development against your PostgreSQL | `.\start-local.ps1` (runs migrations first) |
| Docker Compose | District IT / MINAGRI handover | [infrastructure/README.md](../infrastructure/README.md) |
| Render (hosted preview) | A shareable online demo | `render.yaml` Blueprint, described below |

## Render hosted preview

1. Push this folder to GitHub, keeping `.env` out of Git.
2. Use the **Deploy to Render** link in the main README. When asked for `API_KEY_ROLES`, give a **new** `random-secret:administrator` value.
3. The container runs `alembic upgrade head` and adds the reference schemes on every start. Check `/health`.
4. Open the Render shell and run `python scripts/load_locations.py`, then `python scripts/create_admin.py you@example.org`.
5. Render's free PostgreSQL expires after 30 days and has no backups. Use it only for demonstrations, never for real citizen records.

## Before real citizen data (production checklist)

- [ ] `ENVIRONMENT=production`, `REQUIRE_API_KEY=true`, and strong secrets that are not reused from development.
- [ ] HTTPS in front of the platform. The Africa's Talking callbacks need a public HTTPS URL.
- [ ] Africa's Talking credentials set, and `SMS_PROVIDER` / `AIRTIME_PROVIDER` switched from `dry_run`.
- [ ] The Kinyarwanda USSD screens reviewed with the field team and cooperative leaders.
- [ ] PADAB and APEFA yield targets, hectares and assets entered from official documents, with their sources.
- [ ] `DRY_SPELL_THRESHOLD_MM` / `WET_SPELL_THRESHOLD_MM` calibrated from Mwesa Valley and Ngeruka/Mareba rainfall records.
- [ ] Daily database backups (`pg_dump`) stored off the server, and a restore that has been tested.
- [ ] A consent message for first-time callers, and a data-retention policy agreed with the district.
- [ ] For officers who should see only their own sectors, set each account's **Area** in Platform Management → Accounts.

## Security notes

- Passwords are hashed with PBKDF2-SHA256 (210,000 rounds). Session tokens are stored only as SHA-256 hashes and expire.
- Self-registration cannot choose a role. Only an administrator can promote an account.
- Suspending an account signs the person out immediately.
- The USSD and SMS callbacks are public by design. In production, restrict them at the reverse proxy to Africa's Talking's IP ranges.
- Outgoing messages and rewards are logged with their delivery status (`sent`, `dry_run`, `failed`).
