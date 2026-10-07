"""Keep tests away from the developer's real database.

Environment variables take precedence over the project .env, so the app imports
against a throwaway in-memory SQLite database in development mode.
"""
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ENVIRONMENT"] = "development"
os.environ["REQUIRE_API_KEY"] = "false"
os.environ["WEATHER_FORECAST_ENABLED"] = "false"  # no network calls from tests
