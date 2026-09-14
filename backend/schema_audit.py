"""Compare application model tables and columns with the configured database."""
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.db.base import Base
import app.db.models  # noqa: F401


def main() -> None:
    engine = create_engine(get_settings().database_url)
    inspector = inspect(engine)
    database_tables = set(inspector.get_table_names())
    for table in Base.metadata.sorted_tables:
        actual = {column["name"] for column in inspector.get_columns(table.name)} if table.name in database_tables else set()
        expected = set(table.columns.keys())
        print(f"{table.name}: model={len(expected)} database={len(actual)} missing={sorted(expected - actual)} extra={sorted(actual - expected)}")
        if table.name in database_tables:
            foreign_keys = sorted(f"{key['constrained_columns']} -> {key['referred_table']}" for key in inspector.get_foreign_keys(table.name))
            print("  foreign keys:", "; ".join(foreign_keys) or "none")
            spatial = [f"{column['name']}={column['type']}" for column in inspector.get_columns(table.name) if column["name"] in {"boundary", "location"}]
            if spatial:
                print("  spatial columns:", "; ".join(spatial))


if __name__ == "__main__":
    main()
