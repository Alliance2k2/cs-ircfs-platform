"""Audit structural citations against engineering-labeled claims; no LLM judge."""
import json
import sys
import argparse
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.assistant import documents  # noqa: E402
from app.services.rag.citations import validate, validate_extractive  # noqa: E402


def audit():
    knowledge = Path(__file__).resolve().parents[1] / "app/knowledge"
    dataset = knowledge / "citation_evaluation.json"
    cases = json.loads(dataset.read_text(encoding="utf-8"))
    collection = {source["id"]: source for source in documents()}
    rows = []
    for case in cases:
        source = collection[case["source_id"]]
        if case["evidence"] not in source["text"]:
            raise ValueError("Claim annotation evidence no longer matches its source")
        try:
            accepted = validate(case["claim"], [source])
        except ValueError:
            accepted = False
        try:
            extractive = validate_extractive(case["claim"], [source])
        except ValueError:
            extractive = False
        rows.append(dict(case, structurally_accepted=accepted, extractively_accepted=extractive))
    unsupported = [row for row in rows if not row["supported"]]
    return {"dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
            "corpus_sha256": hashlib.sha256((knowledge / "platform.json").read_bytes()).hexdigest(),
            "annotation_status": "engineering_labels_from_packaged_summaries", "cases": len(rows),
            "unsupported_cases": len(unsupported),
            "unsupported_claim_structural_acceptance_rate": sum(row["structurally_accepted"] for row in unsupported) / len(unsupported),
            "unsupported_claim_extractive_acceptance_rate": sum(row["extractively_accepted"] for row in unsupported) / len(unsupported),
            "supported_claim_extractive_acceptance_rate": sum(row["extractively_accepted"] for row in rows if row["supported"]) / sum(row["supported"] for row in rows),
            "limitation": "Citation-ID checks alone accept unsupported claims; extractive checks enforce sentence provenance. This is a synthetic validator challenge set, not model hallucination rate, source truth or semantic paraphrase verification.",
            "provider_calls": 0, "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
