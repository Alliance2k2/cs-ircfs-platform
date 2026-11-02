"""Inspect the durable outbox by default; --send explicitly contacts configured providers."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select
from app.db.session import SessionLocal
from app.services.delivery_outbox import MODELS, dispatch_one, mark_stale_claims_unknown


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send", action="store_true", help="Dispatch committed queued SMS and airtime; may charge the provider account")
    parser.add_argument("--recover-stale", action="store_true", help="Mark stale claims unknown for manual provider reconciliation")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("limit must be 1..1000")
    if args.recover_stale:
        print("Stale claims marked unknown:", mark_stale_claims_unknown(SessionLocal))
    if args.send:
        for kind in MODELS:
            for _ in range(args.limit):
                status = dispatch_one(SessionLocal, kind)
                if status in ("disabled", "empty"):
                    break
                print(kind, status)
    with SessionLocal() as db:
        for kind, model in MODELS.items():
            print(kind, dict(db.execute(select(model.status, func.count()).group_by(model.status)).all()))


if __name__ == "__main__":
    main()
