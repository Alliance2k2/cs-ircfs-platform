# Database migrations

Use Alembic, not `create_all`, for pilot and production databases.

```powershell
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

The application calls `create_all` only when `ENVIRONMENT=development`. Set `ENVIRONMENT=production` before deployment; then run `alembic upgrade head` as part of deployment.
