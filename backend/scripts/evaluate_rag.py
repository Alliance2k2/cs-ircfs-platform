"""Offline baseline: python scripts/evaluate_rag.py --output PATH. Never calls AI."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.assistant import documents, local_response, retrieve  # noqa: E402
from app.services.rag.evaluation import evaluate, fingerprint, validate_cases  # noqa: E402
from app.services.assistant import safe_local_response  # noqa: E402
from app.services.rag.retrieval import bm25  # noqa: E402
from app.services.rag.retrieval import fuse  # noqa: E402
from app.services.rag.embeddings import local_provider, semantic  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--method", choices=["legacy", "bm25", "semantic", "hybrid"], default="legacy")
    parser.add_argument("--embedding-path", default="")
    parser.add_argument("--embedding-revision", default="")
    parser.add_argument("--split", choices=["all", "development", "holdout"], default="all")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    dataset = root / "app/knowledge/evaluation.json"
    cases = json.loads(dataset.read_text(encoding="utf-8"))
    validate_cases(cases, {doc["id"] for doc in documents()})
    if args.split != "all":
        cases = [case for case in cases if case["split"] == args.split]
    retrieval = retrieve if args.method == "legacy" else lambda question: bm25(question, documents())
    response = local_response if args.method == "legacy" else safe_local_response
    if args.method in {"semantic", "hybrid"}:
        if not args.embedding_path or not args.embedding_revision:
            parser.error("Semantic/hybrid evaluation requires an explicit local model path and revision")
        # Fail loudly: a benchmark must never label lexical fallback as semantic.
        provider = local_provider(args.embedding_path, args.embedding_revision)
        def retrieval(question):
            dense = semantic(question, documents(), provider)
            return dense if args.method == "semantic" else fuse([bm25(question, documents(), 6), dense])
        def response(question):
            return safe_local_response(question, method=args.method, embedder=provider)
    report = evaluate(cases, retrieval, response)
    report.update(dataset_sha256=fingerprint(dataset.read_bytes()),
                  corpus_sha256=fingerprint((root / "app/knowledge/platform.json").read_bytes()),
                  retriever={"legacy": "legacy-title-weighted-keyword-v1", "bm25": "bm25-guarded-v2-question-stopwords"}.get(args.method, args.method),
                  embedding_revision=args.embedding_revision or None, split=args.split, review_status="engineering_fixture_not_native_reviewed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
