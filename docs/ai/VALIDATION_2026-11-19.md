# CS Assistant validation — 19 November 2026

Branch: `feature/document-assistant-20261117`, based on local commit `6c1b4c8`.
This report covers the working-tree improvements, not a deployed release.

## Delivered changes

- Compact responsive chat with message bubbles, internally scrolling messages,
  fixed composer, Enter/Shift+Enter handling, focus recovery, loading/error/empty
  states, examples, New Chat and five page-only archived conversations.
- Authenticated mode status and an explicit generation disclosure. Sending is
  blocked when mode settings cannot be loaded, with a retry control.
- Short contiguous source extracts, complementary-source selection, collapsed full
  evidence, source titles/revisions/page or logical-section references, copy/votes.
- Live pump-status abstention and fewer generic-word false matches. Source text is
  screened for detectable credentials, personal data and injection before ranking
  in the default BM25 path. This is a heuristic defense, not a completeness claim.
- Administrator title search/review filters, actual chunk/job/embedding counts,
  upload capability gate, bounded reindex/check and safe failed-job recovery.
- Durable source lifecycle audit events without question/document content or keys.
  Roles, required sectors, review gates and mutation origin checks remain enforced.
- No new dependencies, schema migration, vector service or model download.

## Test evidence

All databases used by mutation tests are throwaway fixtures. The browser runner
creates its own SQLite database and disables outbound messaging and AI generation.
It enables ingestion only for synthetic lifecycle tests; this does not approve
ingestion on the running local platform.

| Check | Actual result |
| --- | --- |
| Broad backend `pytest tests -q -p no:cacheprovider --tb=line` | 427 passed, 2 skipped, 15 temporary-directory setup errors in the restricted Windows sandbox |
| Workspace-temp attempt | Same 15 Windows permission setup errors; no assertion failures |
| Affected calibration/hosting/migration files plus assistant/management outside sandbox | 61 passed; resolves the 15 fixture setup errors and covers final excerpt changes |
| Focused assistant/API/management/evaluation run after final reply selection | 42 passed |
| API regression including new persisted failure/retry test | 12 passed |
| Full frontend suite `npm run test -- --maxWorkers=2` | 70 passed across 19 files |
| Changed assistant/knowledge UI rerun after accessible-name fix | 9 passed |
| TypeScript and production build | Passed |
| ESLint | Passed |
| Chrome sign-in + assistant end-to-end workflows | 14 passed: 5 role-session setup checks and 9 browser scenarios |
| Assistant accessibility scan | No serious/critical axe violations in the tested chat region/state |
| Desktop/mobile visual inspection | Final synthetic screenshots reviewed; welcome scroll starts at zero and composer stays visible on mobile |

The broad backend invocation was **not** a clean single-run success: its Windows
fixture errors are recorded above, and the affected files passed outside the
sandbox. Two dedicated PostgreSQL tests skipped because `RAG_TEST_POSTGRES_URL`
was not supplied. This report does not claim a current PostgreSQL/pgvector run.

Initial browser failures were resolved rather than hidden: exact/scoped selectors
removed ambiguous matches; an actual visible-label/accessible-name mismatch on
**New chat** was corrected. Screenshot review also found the initial welcome icon
being scrolled under the header; empty-chat scrolling and welcome sizing were fixed.
The final post-fix browser rerun passed all 14 checks in 29.1 seconds. The local
server was restarted with the final code; health and assistant page returned 200,
and unauthenticated assistant configuration access returned 401 as expected.

Known non-failing warnings: Starlette TestClient/httpx deprecation, Alembic legacy
path-separator configuration, Vite runtime-resolved font references and the existing
large map bundle. The tested runtime served the fonts successfully. These checks
are Chrome desktop/mobile-viewport checks, not physical-device/Safari acceptance.

## Retrieval and citation results

The same 64 engineering-labeled cases were used for comparison. Fifty are labeled
answerable and fourteen negative; eight draft Kinyarwanda fixtures are not native
reviewed. Both development/holdout splits have been inspected previously. These are
regression measurements, not independent research-test or institutional acceptance.

| Method | Recall@3 | MRR | nDCG@3 | Correct response mode | Negative modes correct |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original legacy overlap | 0.83 | 0.82 | 0.81875 | 75% | 42.86% |
| Original guarded BM25 | 0.83 | 0.83 | 0.82613 | 84.375% | 85.71% |
| Revised guarded BM25 | 0.83 | 0.83 | 0.82613 | 87.5% | 100% (14/14) |

The lexical ranking equations and architecture did not change. Common question
scaffolding was removed from query matching. Local answers select short verbatim
sentences instead of repeating entire chunks. A second reply source must cover
additional question terms; a small verify/verified/verification normalization applies
only to excerpt selection. Raw top-k retrieval metrics are distinct from this reply
selection and do not measure end-to-end semantic answer correctness.

The final artifact reports a median **17 answer words**, maximum 59 on these cases,
and **100% exact extractive citation validity** for document-mode fixture replies.
This verifies quotation provenance, not source truth, relevance or complete context.
English Recall@3: 0.94048; draft Kinyarwanda: 0.25. Remaining mode failures are two
spelling/paraphrase cases (`q055`, `q056`) and six Kinyarwanda cases (`q059`–`q064`).

The separate eight-claim challenge set shows ID-only validation accepting all six
unsupported claims. Exact extractive validation rejected six of six unsupported
claims and accepted two of two supported quotations. No LLM judge or real provider
call was used. This is not a measured model hallucination rate.

Artifacts:

- `legacy-results-2026-11-19.json`
- `bm25-results-2026-11-19.json`
- `bm25-improved-results-2026-11-19.json`
- `citation-support-results-2026-11-19.json`

## Architecture decision and missing comparisons

| Candidate | Evidence from this run | Status |
| --- | --- | --- |
| BM25 | Reproduced lexical metrics, authorization and abstention tests | Retain default |
| Embeddings | `sentence_transformers` absent; no cached Hugging Face model snapshots | Real relevance/latency unmeasured |
| Hybrid + RRF | Existing adapters and synthetic fusion/geometry tests pass | Real-model gain unmeasured |
| pgvector | Existing exact-distance adapter; dedicated test URL absent | Skipped; no extension installed |
| Cross-encoder | No implementation or approved local model/benchmark | Defer; no unjustified new component |

No model, vector index or reranker is activated merely because an interface exists.
See [operator and engineering guide](ASSISTANT_OPERATIONS.md) for reproduction and
the distinction between database search, an embedding model and a reranker.

## Retained visual evidence

All screenshots show synthetic E2E identities and data:

- [Welcome](../images/assistant-welcome-2026-11-19.png)
- [Desktop conversation](../images/assistant-desktop-2026-11-19.png)
- [Mobile conversation](../images/assistant-mobile-2026-11-19.png)

## Remaining risks and prioritized next steps

1. Obtain independent institutional/source and native Kinyarwanda review. The current
   packaged excerpts are engineering summaries; the local demo has no managed sources.
2. Provision an approved local encoder and disposable pgvector database; benchmark
   semantic/hybrid/reranking quality and latency on newly reviewed data before changing
   defaults. Do not interpret synthetic vector tests as real semantic quality.
3. Approve a constrained extraction worker before enabling real uploads. The current
   parser has limits but no isolated CPU/memory sandbox, OCR or reliable DOCX print pages.
4. Review privacy, retention and access requirements before persistent chat storage.
   Current chat history clears when leaving the page. There is no streaming/cancellation.
5. Review source screening false positives/negatives and prompt-injection cases.
   Human approval, authorization, tool absence and plain text rendering remain essential.
   Existing role-only service API keys resolve to district-wide sector scope; use
   appropriately scoped staff accounts for area-restricted access, and review a
   scoped-service-principal design before issuing keys for restricted integrations.
6. Validate long-document job timeouts, multi-process concurrency and shared telemetry
   before scaling. Reindexing is synchronous and bounded to 2,000 stored chunks;
   original uploads are not retained for reparsing. Stored vectors are not selected
   by the current HTTP retrieval path, and no ANN/HNSW performance is claimed.

No main-branch push, deployment, paid API activation, live message, field-data reset,
source removal in the running demo, or upload activation was performed. The local
server remains a demo with normal sign-in, ingestion off and generation off.
