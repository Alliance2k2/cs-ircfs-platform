# Learning AI engineering with this repository

RAG means **retrieve evidence, then optionally generate an answer**. Retrieval is
useful without an LLM: this platform defaults to quoted evidence. An LLM is a
language model, not an authenticated database or a source of institutional approval.

Read these in order: [architecture/audit](RAG_ARCHITECTURE.md),
[retrieval](RETRIEVAL_PIPELINE.md), [embeddings](EMBEDDINGS.md),
[prompts](PROMPT_ENGINEERING.md), [evaluation](RAG_EVALUATION.md),
[security](SECURITY.md), [deployment](DEPLOYMENT.md).

## Follow one question through the code

1. `AssistantPage.tsx` sends a question, explicit/automatic language and at most three
   previous **user questions**. No previous model answers are submitted as evidence.
2. `api/routes/assistant.py` checks officer/planner/admin access and request bounds.
3. `rag/store.py` checks document approval, role and required sector sets before
   fetching chunk text. The packaged six summaries remain general engineering sources.
4. `assistant.py` rejects recognized personal data, secrets, bypass instructions
   and live-data demands, then calls local retrieval. Regex checks are incomplete.
5. Retrieval returns bounded evidence with source/revision/page/classification.
6. Default answers quote evidence. Optional providers cannot receive managed documents
   or unreviewed-language requests. Every generated paragraph must quote complete
   sentences from its cited source; unsupported paraphrases trigger excerpt fallback.
7. React displays text safely; clear/navigation discards browser-memory conversation.

## Hands-on exercises

```python
# Run in backend (or import from a test).
from app.services.rag.embeddings import cosine
assert cosine([1, 0], [0, 1]) == 0  # orthogonal directions

from app.services.rag.chunking import chunk_pages
chunks = chunk_pages(["word " * 700], size=512, overlap=64)
assert len(chunks) == 2  # one page; overlapping chunks retain page=1
```

Try `check_rag_chunks.py` and explain why six short sources yield the same Recall@3
for 128/256/512/768 whitespace-token chunks. Add a synthetic long source **in a test**
and observe the difference. Do not silently alter the frozen benchmark corpus.

Run the legacy and BM25 evaluation commands. Inspect a development failure and
propose a change; reserve holdout cases for release evaluation. Ask a native reviewer
to correct RW wording/labels separately. A model card's multilingual label cannot
replace these measurements. Finally inspect the source-approval API integration test:
explain why a newly uploaded source is invisible until approval.

## Terms to keep separate

An embedding is a vector, retrieval is a ranked search, a prompt is instructions,
generation is new text, an evaluation label is a judgment, and authorization is a
server-side permission decision. None of these alone establishes factual correctness.
No trained agriculture model or institutionally reviewed agronomic corpus is supplied.
