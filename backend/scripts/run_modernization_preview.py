"""Run an isolated synthetic UI preview, without ingestion or external services.

Reuses the existing end-to-end seed and sandbox. It never opens the normal local
database. Only the port is configurable here; model execution cannot be enabled.
"""
import argparse
import os
import sys

import run_e2e_server as runner


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8794)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a local port between 1024 and 65535")
    sandbox = runner.sandbox_environment

    def preview_environment(database, port):
        sandbox(database, port)
        os.environ.update(ASSISTANT_GENERATION_ENABLED="false",
                          ASSISTANT_INGESTION_ENABLED="false",
                          ALLOW_LIVE_MESSAGES="false")

    runner.sandbox_environment = preview_environment
    sys.argv = [sys.argv[0], "--port", str(args.port)]
    runner.main()


if __name__ == "__main__":
    main()
