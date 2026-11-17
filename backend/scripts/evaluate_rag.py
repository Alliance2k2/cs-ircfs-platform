"""Offline baseline: python scripts/evaluate_rag.py --output PATH. Never calls AI."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.assistant import documents, local_response, retrieve  # noqa: E402
from app.services.rag.evaluation import evaluate, fingerprint, validate_cases  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    dataset = root / "app/knowledge/evaluation.json"
    cases = json.loads(dataset.read_text(encoding="utf-8"))
    validate_cases(cases, {doc["id"] for doc in documents()})
    report = evaluate(cases, retrieve, local_response)
    report.update(dataset_sha256=fingerprint(dataset.read_bytes()),
                  corpus_sha256=fingerprint((root / "app/knowledge/platform.json").read_bytes()),
                  retriever="legacy-title-weighted-keyword-v1", review_status="engineering_fixture_not_native_reviewed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
