# GitHub and hosted preview

This repository can run as one web service: FastAPI serves both `/api/v1/*` and the dashboard at `/`. The `render.yaml` Blueprint provisions a PostgreSQL database and connects it to the Docker service. Render supports the PostGIS extension used by the Alembic migrations.

## Publish

1. Push this folder as the root of a GitHub repository. Keep `.env` out of Git.
2. In Render, create a Blueprint from that repository and review the service and database plan before creating resources. The service asks for `API_KEY_ROLES`; supply a new key in `random-secret:administrator` format. Do **not** reuse the local development key.
3. The Docker start command runs `alembic upgrade head` before serving requests. Check the deploy logs for migration success and `/health` for a 200 response.
4. Open the Render service URL. The dashboard uses the API at the same HTTPS origin. Enter the new hosted API key when connecting. The hosted database starts with only the inactive PADAB and APEFA Solar reference names. It has zero observations and no scheme markers.
5. Add only verified Bugesera locations and scheme records to the hosted database. Keep the source data and approval record with the project.

This is a **hosted demonstration**, not a production service for real citizen records. API keys identify a role rather than a person, and district ownership, privacy controls, a telecom provider, backups, and monitoring still need implementation. Do not migrate personal data from the local database into the hosted preview.

The Blueprint has no fixed paid plan. Render may ask you to choose a plan and billing method when creating the database or service. Review the current pricing in Render before confirming resource creation.
