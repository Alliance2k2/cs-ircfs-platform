"""Send this week's irrigation advice SMS (WP2) and print a summary.

Idempotent: each sector receives the week's advice at most once, recorded in the
``advice_runs`` table, so running this twice in the same week sends once. Sectors
without rain-gauge readings this week are skipped. With SMS_PROVIDER=dry_run the
messages are recorded but not sent.

Run it from cron, Windows Task Scheduler or a container, for example (Mondays 06:00
Africa/Kigali, i.e. 04:00 UTC):

    0 4 * * 1  cd /srv/cs-ircfs/backend && python scripts/send_weekly_advice.py

Exit codes: 0 = sent (or already sent this week), 1 = something failed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make the `app` package importable

from app.db.session import SessionLocal
from app.services.advisory import send_weekly_advice


def main() -> int:
    db = SessionLocal()
    try:
        summary = send_weekly_advice(db)
    finally:
        db.close()

    print(f"Week: {summary['week_key']}")
    if summary["dry_run"]:
        print("Provider: dry_run (messages recorded, not sent)")
    if summary["no_readings"]:
        print(f"Sectors without rain-gauge readings (skipped): {summary['no_readings']}")
    if not summary["sectors"]:
        if summary["skipped_already_sent"]:
            print("Nothing to send: every sector with readings already received this week's advice.")
        elif not summary["no_readings"]:
            print("Nothing to send: no sectors found in the database.")
        else:
            print("Nothing to send: no sector has rain-gauge readings this week.")
        return 0
    if summary["skipped_already_sent"]:
        print(f"Sectors already sent this week (skipped): {summary['skipped_already_sent']}")
    for sector in summary["sectors"]:
        print(f"  {sector['sector']}: {sector['recipients']} recipients -> {sector['status']}")
    print(f"Total: {len(summary['sectors'])} sectors, {summary['total_recipients']} recipients")
    failed = [sector for sector in summary["sectors"] if sector["status"] == "failed"]
    if failed:
        print(f"FAILED: {len(failed)} sector(s) could not be sent.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
