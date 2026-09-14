FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/app /app/backend/app
COPY backend/migrations /app/backend/migrations
COPY backend/alembic.ini /app/backend/alembic.ini
COPY backend/seed_reference_schemes.py /app/backend/seed_reference_schemes.py
COPY dashboard /app/dashboard

WORKDIR /app/backend
CMD ["sh", "-c", "alembic upgrade head && python seed_reference_schemes.py && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
