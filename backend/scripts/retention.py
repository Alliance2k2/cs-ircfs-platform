"""Preview retention counts; --apply requires an approved policy and explicit DB confirmation."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.session import SessionLocal
from app.services.retention import retention_plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply",action="store_true")
    parser.add_argument("--policy-reference")
    parser.add_argument("--confirm-database")
    args=parser.parse_args()
    with SessionLocal() as db:
        name=Path(db.bind.url.database or "").name
        if args.apply and (args.confirm_database != name or not args.policy_reference):
            parser.error("--apply requires --policy-reference and --confirm-database matching the selected database name")
        result=retention_plan(db,apply=args.apply,policy_reference=args.policy_reference)
        if args.apply: db.commit()
        print(json.dumps(result,indent=2))

if __name__=="__main__":main()
