# Offline RAG evaluation

Run from `backend`:

```powershell
../.venv/Scripts/python.exe scripts/evaluate_rag.py --output ../docs/ai/baseline-results.json
../.venv/Scripts/python.exe -m pytest tests/test_rag_evaluation.py tests/test_assistant.py -q
```

The versioned 64-case dataset is `app/knowledge/evaluation.json`. It has 50 questions
with source relevance labels and 14 negative/security/ambiguous questions. Eight
Kinyarwanda questions and their labels are **drafts pending native review**.
They are engineering evaluation fixtures, not approved translations. All identifiers,
email/phone/secret examples are synthetic. The corpus is six engineering summaries,
not institutional agriculture guidance. Development/holdout labels prevent tuning on
every question; do not repeatedly inspect holdout mistakes to tune a release.

Metrics use source IDs as binary relevance labels. Precision@3 divides hits by 3,
even if fewer than 3 results are returned; Recall@3 divides hits by all relevant
sources. MRR uses the first relevant rank. nDCG discounts lower ranks by
`1/log2(rank+1)` and divides by ideal DCG. These four means include answerable cases
only. Negative cases have undefined recall/nDCG, not an invented perfect score.
Mode accuracy covers all cases; abstention accuracy compares the required refusal
type for negative cases. A privacy refusal differs from a missing-evidence response.

The frozen legacy baseline (`baseline-results.json`) measured Precision@3 **0.300**,
Recall@3 **0.830**, MRR **0.820**, nDCG **0.819**, mode accuracy **0.750**, and negative
mode accuracy **0.429**. These are small synthetic-corpus measurements, not production
quality estimates. Per-language counts/results and every retrieved ID are in JSON.
Latency is local wall time, includes two retrieval calls and the initial cache load;
it is not network/provider/production latency. Dataset/corpus SHA-256 binds the run
to its inputs. Token usage/API cost/provider calls are zero because generation is
never invoked, independently of environment settings.

Faithfulness, semantic answer relevance, hallucination rate and citation entailment
are **not measured** by source ranking or response mode. Do not relabel these metrics
as answer correctness. Generation needs claim-level reviewed annotations and actual
provider acceptance. RAGAS is not added because this offline phase has no judge or
approved external processing. A future judge should be calibrated against humans.

Baseline weaknesses include keyword-triggered answers to unsupported live totals,
injection instructions sharing corpus vocabulary, typos and cross-language misses.
Do not force those failures into passing by changing labels after observing results.
