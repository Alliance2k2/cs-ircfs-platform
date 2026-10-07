"""Create one local administrator API key in the ignored project .env file."""
from pathlib import Path
import secrets
import sys


def main() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    existing = next((line.split("=", 1)[1].strip() for line in lines if line.startswith("API_KEY_ROLES=")), "")
    if existing and "--rotate" not in sys.argv:
        print("API key configuration already exists; no changes made.")
        return
    lines = [line for line in lines if not line.startswith(("API_KEY_ROLES=", "REQUIRE_API_KEY="))]
    lines.extend(["REQUIRE_API_KEY=true", f"API_KEY_ROLES={secrets.token_urlsafe(32)}:administrator"])
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Generated one administrator API key in .env. The key was not printed.")


if __name__ == "__main__":
    main()
