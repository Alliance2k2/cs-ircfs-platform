# Stage 1: build the React dashboard (frontend/ -> frontend/dist), served by FastAPI at /app/.
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Stage 2: the platform (API, USSD/SMS callbacks, classic dashboard and the React build).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/app /app/backend/app
COPY backend/migrations /app/backend/migrations
COPY backend/alembic.ini /app/backend/alembic.ini
COPY backend/scripts /app/backend/scripts
COPY dashboard /app/dashboard
COPY --from=frontend /frontend/dist /app/frontend/dist

WORKDIR /app/backend
# --proxy-headers: behind a load balancer, rate limits must see the real client address.
# FORWARDED_ALLOW_IPS names the trusted proxy ("*" on Render, where only its proxy can reach the container).
CMD ["sh", "-c", "alembic upgrade head && python scripts/seed_reference_schemes.py && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-127.0.0.1}"]
