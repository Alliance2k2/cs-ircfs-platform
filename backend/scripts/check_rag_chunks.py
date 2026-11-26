"""Measure chunk size sensitivity on the approved packaged summaries, offline."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.assistant import documents  # noqa: E402
from app.services.rag.chunking import chunk_pages  # noqa: E402
from app.services.rag.retrieval import bm25  # noqa: E402
from app.services.rag.evaluation import ranking_metrics  # noqa: E402


def main():
    cases = json.loads((Path(__file__).resolve().parents[1] / "app/knowledge/evaluation.json").read_text(encoding="utf-8"))
    result = []
    for size in (128, 256, 512, 768):
        collection = []
        for doc in documents():
            collection.extend(dict(doc, id=f"{doc['id']}:{chunk.ordinal}", document_id=doc["id"], text=chunk.text)
                              for chunk in chunk_pages([doc["text"]], size=size, overlap=min(64, size // 4)))
        recalls = []
        for case in cases:
            if not case["relevant_ids"]:
                continue
            found = bm25(case["question"], collection)
            ids = list(dict.fromkeys(row["document_id"] for row in found))
            recalls.append(ranking_metrics(case["relevant_ids"], ids)["recall_at_k"])
        result.append({"size_whitespace_tokens": size, "chunks": len(collection), "document_recall_at_3": sum(recalls) / len(recalls)})
    print(json.dumps({"results": result, "limitation": "Six short summaries cannot establish optimal chunk size for long agricultural PDFs. No semantic model evaluated."}, indent=2))


if __name__ == "__main__":
    main()
