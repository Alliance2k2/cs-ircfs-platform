# CS Assistant audit and implementation plan — 19 November 2026

## Scope and evidence

Inspected the local `feature/document-assistant-20261117` branch at `6c1b4c8`, its
uncommitted chat/authentication fixes, FastAPI routes, SQLAlchemy knowledge tables,
retrieval/provider adapters, React components, tests, migration and engineering docs.
The local tracking ref reports six unpushed commits; it was not refreshed from GitHub.
This is a local-source audit, not confirmation of deployed behavior.
Unrelated application materials and personal PDFs are outside scope.

## Findings before this implementation pass

| Area | Observed implementation | Gap or limitation |
| --- | --- | --- |
| Chat | Ten in-memory exchanges, New Chat/clear, three previous user questions, copy and categorical feedback | Previous UI verbose; chat redesign in progress. No persistent session history; no streaming/cancellation |
| Sources | Six packaged engineering excerpts; managed documents have immutable revisions, SHA-256, page/logical-section metadata | Demo DB has zero managed sources; packaged summaries are not district-approved agronomic guidance |
| Retrieval | BM25 default, bounded corpus/context; optional semantic encoder and RRF | No installed sentence-transformers or cached model snapshot; actual embedding/hybrid quality unmeasured |
| Vectors | Portable JSON embeddings, exact pgvector adapter, model/dimension filters | Adapter not connected to HTTP retrieval; no native vector index/HNSW; no cross-encoder implementation |
| Answer support | Generated passages must be verbatim source quotations with valid IDs; plain React text rendering | Citation provenance is not source truth or relevance. Previous local answers repeated entire excerpts; unrelated lexical overlap possible |
| Permissions | Staff API role checks; required role and all required sectors checked before loading managed chunks | Must retain this ordering in any future vector/reranking path; broad source approval remains a human responsibility |
| Knowledge workflow | Pending → approved → superseded; signed-in admin approval; duplicate/idempotency checks, previews, removal | No source search, processing/embedding dashboard or repair endpoint; job rows exist but are not surfaced |
| Upload boundary | Server switch defaults off; byte/page/text/chunk bounds; PDF, DOCX, text parsers | Parser runs in process, not an isolated worker; activation requires explicit extraction-environment approval |
| Security | Fixed provider endpoints, generation off, request bounds, mutation origin checks, heuristic secret/PII/injection guards | Guards are incomplete; lifecycle events need durable audit entries; source text also needs screening before provider access |
| Operations | Aggregate process-local telemetry and offline evaluations | No shared telemetry store; no production acceptance test; no real-model benchmark |
| Google login | Session verification; server originally launched with sandbox network restrictions | Server restarted with network; network-vs-invalid-token error distinction added and tested |

## Prioritized implementation plan

1. **P0: preserve access and evidence boundaries.** Add lifecycle audit events,
   source-content screening and HTTP regression tests for roles, sectors, citations,
   missing evidence and disabled ingestion. Never send source secrets to a provider.
2. **P1: finish usable chat.** Compact welcome, scrollable messages, fixed composer,
   keyboard/mobile tests, announced loading/errors, compact cited extracts, hidden
   source details and collapsed administrator settings. Keep chat memory local to
   this page; persistent history requires a separate retention/access design.
3. **P1: make knowledge operations inspectable.** Search/filter source revisions,
   show actual chunk/job/embedding counts, surface upload gate, allow bounded,
   repeatable reindex/check of stored chunks and safe retry after failure. Preserve
   existing approved versions; do not fabricate success for missing models/chunks.
4. **P2: measure before expanding.** Re-run lexical baseline and citation evaluation;
   document missing model/pgvector prerequisites. Do not add a vector service or
   reranker without a reproducible relevance/latency benefit on reviewed data.
5. **P2: validate and document.** Backend/frontend regression checks, desktop/mobile
   browser evidence, results artifact and updated operator/learning documentation.

## Retrieval baseline reproduced during audit

64 engineering-labeled fixtures, including eight unreviewed Kinyarwanda cases;
both development and holdout splits were previously inspected. No model calls.

| Method | Recall@3 | MRR | nDCG@3 | Mode accuracy | Negative-mode accuracy |
| --- | ---: | ---: | ---: | ---: | ---: |
| Legacy overlap | 0.83 | 0.82 | 0.81875 | 0.75 | 0.42857 |
| Guarded BM25 | 0.83 | 0.83 | 0.82613 | 0.84375 | 0.85714 |

Artifacts: `legacy-results-2026-11-19.json`, `bm25-results-2026-11-19.json`.
These are retrieval/response-mode measurements, not end-to-end answer correctness.
BM25 remains the default. RRF combines ranked lists; it does not establish that
either list is relevant. pgvector accelerates vector operations; it does not make
an embedding model understand local agriculture. Cross-encoders add a second
question/passage scoring step and should earn their additional cost in a benchmark.

## Validation and remaining work

The final run results and remaining release gates are recorded separately in
`VALIDATION_2026-11-19.md`. No model download, paid API activation, extraction
activation, deployment, main-branch push or field-data mutation is authorized here.
