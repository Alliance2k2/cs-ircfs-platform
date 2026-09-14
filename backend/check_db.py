"""Check configured database connectivity without printing credentials."""
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, connect_args={"connect_timeout": 3} if settings.database_url.startswith("postgresql") else {})
    with engine.connect() as connection:
        print("Environment:", settings.environment)
        print("Dialect:", engine.dialect.name)
        print("Connection:", connection.scalar(text("SELECT 1")))
        tables = inspect(connection).get_table_names()
        print("Tables:", ", ".join(sorted(tables)) or "none")
        if engine.dialect.name == "postgresql":
            print("PostGIS installed:", connection.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis')")))
        if "alembic_version" in tables:
            print("Migration revision:", connection.scalar(text("SELECT version_num FROM alembic_version")))


if __name__ == "__main__":
    main()
