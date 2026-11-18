# RAG extension engineering report — 18 November 2026

Branch: `feature/document-assistant-20261117`, starting at `8105ca6`.
This report records local engineering validation, including work begun on 17 November.
It does not authorize deployment, external generation, institutional use or native
language acceptance. Earlier pilot counts remain historical.

## Outcome and architecture decisions

The existing FastAPI/SQLAlchemy/PostgreSQL/React stack is preserved. The six packaged
engineering summaries remain available; reviewed knowledge documents are a separate
collection with immutable versions and role/required-sector permissions. Retrieval
defaults to BM25. Local embedding, hybrid fusion, persistent portable vectors and
pgvector distance adapters are optional. Their real-model/index quality is not yet
validated. New knowledge tables use migration `20261117_30` without changing field
consent, locations, reports, simulator profiles or scientific evidence.

Document ingestion uses bounded extraction, page-preserving chunks, content hashes,
idempotent retries, explicit signed-in administrator approval and transactional
replacement/deletion. Identical uploads with identical metadata return the existing
version even when a client lost its document ID. Different metadata/access policy
cannot silently repurpose a duplicate. PostgreSQL serializes same-content uploads
with transaction advisory locks and serializes document/version mutations with row
locks. SQLite is a development fallback, not a validated multi-process upload service.

External generation remains off. OpenAI Responses is retained; loopback Ollama is an
optional adapter. Generated output must contain complete verbatim sentences from its
cited sources. This conservative restriction follows an explicit claim-support audit:
valid IDs alone accepted contradictory claims. Managed knowledge and RW requests are
blocked from generation. No real provider call, secret modification, paid service,
live operational action, deployment, merge or push was performed for this extension.

## Phase reports

### Phase 1 — audit and baseline: completed

- **Implementation/decision:** preserved the legacy overlap baseline and separated
  offline local response construction from provider calls. Added 64 synthetic cases
  with source labels, languages, categories and development/holdout splits.
- **Files:** `backend/app/knowledge/evaluation.json`, `services/rag/evaluation.py`,
  `scripts/evaluate_rag.py`, `tests/test_rag_evaluation.py`, `RAG_ARCHITECTURE.md`,
  `RAG_EVALUATION.md`, `baseline-results.json`.
- **Evidence/security:** metric denominator tests and a no-network test pass. Baseline
  Recall@3 0.83, MRR 0.82, mode accuracy 0.75; provider calls/tokens/API cost are zero.
- **Limitations:** engineering labels and eight draft RW cases need independent/native
  review. Both splits have now been inspected; they are not an unseen research test set.
- **Learning/reproduction:** run the legacy evaluation command below; compare a query's
  relevant IDs with retrieved IDs. Retrieval overlap is not answer correctness.
- **Next:** expand independently reviewed institutional and native-language cases.

### Phase 2 — extraction and chunking: implemented and locally validated

- **Implementation/decision:** UTF-8 TXT/Markdown/CSV/JSON, DOCX ZIP/XML and optional
  pypdf extraction; 5 MiB file, 200 PDF page, one-million-character and 5,000-chunk
  limits. Fixed/token/paragraph/recursive/heading strategies preserve logical pages.
- **Files:** `rag/ingestion.py`, `rag/chunking.py`, `tests/test_rag_ingestion.py`,
  `requirements-rag.txt`, `scripts/check_rag_chunks.py`.
- **Evidence/security:** format, malformed/oversized input, XML entity refusal,
  overlap, page provenance, real two-page PDF, encryption and empty-PDF tests pass.
  Optional pypdf 6.21.4 was installed locally; no document was transmitted.
- **Limitations:** whitespace token estimates need actual model-token checks. No OCR,
  reliable DOCX print pagination, universal heading parser or isolated parser process.
  Upload activation stays off pending extraction-environment approval.
- **Learning/reproduction:** inspect `extract` and `chunk_pages`; run chunk sensitivity.
  Sizes 128/256/512/768 all produce six chunks and Recall@3 0.83 on these short sources.
- **Next:** validate long approved agriculture documents in a constrained parser worker.

### Phase 3 — persistence and embeddings: portable implementation validated; vector/model gates remain

- **Implementation/decision:** six knowledge tables for documents, versions, chunks,
  embeddings, jobs and evaluation metadata. JSON vectors support SQLite/PostgreSQL;
  optional exact pgvector distance casts preauthorized, model/dimension-filtered rows.
  Local CPU embeddings require explicit local snapshots/revisions, bounded batches,
  normalization, caching and model-token limits. No automatic downloads.
- **Files:** `db/knowledge.py`, `db/models.py`, `migrations/versions/20261117_30_knowledge.py`,
  `rag/store.py`, `rag/embeddings.py`, `rag/vectors.py`, `tests/test_rag_store.py`,
  `tests/test_rag_postgres.py`, `requirements-rag-models.txt`.
- **Evidence/security:** SQLite migration/schema/reversal tests pass. PostgreSQL 18.6 /
  PostGIS 3.6.2 fresh upgrade, zero schema differences, downgrade/re-upgrade, portable
  source lifecycle/ACL/vector/deletion tests pass. Temporary schema/fixtures roll back.
- **Limitations:** pgvector extension absent; its distance assertions skip. Native
  vector columns/HNSW, actual MiniLM/BGE-M3/multilingual-E5 comparisons and persistent
  vector selection in the HTTP path remain incomplete. The request path uses a
  bounded local encoder cache if explicitly configured. No production model is selected.
- **Learning/reproduction:** synthetic vectors test geometry/plumbing, not semantic
  quality. Run the dedicated PostgreSQL commands below only against disposable DBs.
- **Next:** provision a supported pgvector environment and reviewed local model snapshots.

### Phase 4 — retrieval and fusion: BM25 validated; real hybrid quality pending

- **Implementation/decision:** BM25, configurable top-k/threshold, metadata/ACL filtering,
  cosine ranking, RRF and bounded complete-chunk context. Lexical fallback remains.
- **Files:** `rag/retrieval.py`, `rag/embeddings.py`, `services/assistant.py`,
  `core/config.py`, `tests/test_rag_retrieval.py`, `bm25-results.json`.
- **Evidence/security:** synthetic geometry, rank fusion, no-evidence and candidate-scope
  tests pass. BM25 Recall@3 0.83, MRR 0.83, nDCG 0.826. With request guards, mode
  accuracy is 0.84375 and negative-mode accuracy 0.85714. Draft RW Recall@3 is 0.25.
- **Limitations:** actual semantic/hybrid comparisons, cross-encoder reranking, stemming,
  typo correction and synonym expansion are not validated/activated. Low RW performance
  is recorded, not hidden. Matching a passage can still be tangential to the question.
- **Learning/reproduction:** run both method commands and inspect per-language/split
  results. BM25 scores and cosine/RRF values are ranking signals, not confidence.
- **Next:** benchmark approved models before enabling semantic retrieval or reranking.

### Phase 5 — generation and context: constrained implementation validated with mocks

- **Implementation/decision:** provider interface, versioned extractive prompt,
  20-second provider timeouts, one 429/503 retry for OpenAI, token accounting,
  quotation/citation validation and safe fallback. Up to three prior user questions
  support limited follow-ups; model answers never become evidence or authorization.
- **Files:** `rag/providers.py`, `rag/prompts.py`, `rag/citations.py`, `rag/safety.py`,
  `services/assistant.py`, `knowledge/citation_evaluation.json`,
  `scripts/evaluate_citation_support.py`, `tests/test_rag_observability.py`.
- **Evidence/security:** mocked HTTP covers fixed endpoints, bounded retries, reported
  token type checks, invalid/uncited/forged answers and provider errors. Eight labeled
  claims show ID-only acceptance of 6/6 unsupported claims; extractive validation
  rejects 6/6 and accepts 2/2 supported quotations. No paid/model judge calls.
- **Limitations:** quotation provenance does not prove source truth, relevance or full
  context. Free paraphrases and actual provider health/acceptance remain unvalidated.
  No persistent conversation store or comprehensive PII detector is introduced.
- **Learning/reproduction:** run the citation audit; observe why a genuine ID cannot
  establish support for an arbitrary claim.
- **Next:** independently review sources and provider processing before any activation.

### Phase 6 — dashboard and source management: implemented; browser validation recorded below

- **Implementation/decision:** existing design system, plain React text rendering,
  language choice, bounded follow-ups, clear/copy/feedback, source previews and
  classifications/page references. Administrator source upload/review/approval,
  version preparation and removal use the same authenticated backend.
- **Files:** `api/routes/assistant.py`, `frontend/src/features/assistant/AssistantPage.tsx`,
  `KnowledgePanel.tsx`, their tests, `frontend/e2e/15-assistant.spec.ts`.
- **Evidence/security:** full frontend suite passed 67 tests. API tests cover auth,
  pending invisibility, upload-to-approval retrieval, removal, context bounds and
  cross-origin refusal. Untrusted source text renders without HTML execution.
- **Limitations:** management listing is capped at 200 versions and previews at 100
  chunks; pagination and a durable ingestion queue are not implemented. Jobs track
  successful extraction/indexing; pre-extraction failures return errors without rows.
- **Learning/reproduction:** synthetic browser scenario uploads, retries, reviews,
  approves, retrieves and removes a source; pending content must remain invisible.
- **Next:** administrator usability review with approved institutional sources.

### Phase 7 — language, security and observability: controls validated; native review pending

- **Implementation/decision:** explicit EN/RW choice and limited detection, request
  guards, pre-retrieval ACLs, 64 KiB streaming JSON bound, same-origin mutations,
  bounded file/text/context inputs and privacy-preserving counters/timing.
- **Files:** `rag/safety.py`, `rag/observability.py`, `core/metrics.py`, API/tests,
  `SECURITY.md`. `/metrics` retains administrator protection and exposes bounded
  assistant counters, timing totals and model revision hashes without prompt text.
- **Evidence/security:** privilege/scope/history/injection tests, unsafe output checks,
  unknown feedback-field refusal, body caps and metric cardinality tests pass.
  Estimated API cost remains `null`; reported token counts do not imply known prices.
- **Limitations:** no native-reviewed RW acceptance, comprehensive red team, distributed
  quota, durable feedback analytics or verified provider retention. French source
  metadata is possible, but a French conversational interface is not implemented.
- **Learning/reproduction:** compare scoped principals in store tests; inspect metrics
  to confirm that neither prompts nor user IDs become labels.
- **Next:** native review, independent authorization/security review and model evaluation.

### Phase 8 — documentation and release preparation: local review package; deployment pending

- **Implementation/decision:** eight requested educational guides, architecture diagram,
  annotated examples, mathematics, configuration, exercises, validation and roadmap.
  Demo startup forces ingestion/generation off; E2E alone enables ingestion in its
  disposable SQLite server with synthetic files.
- **Files:** all `docs/ai/*.md`, `README.md`, `docs/document-assistant.md`,
  `docs/roadmap.md`, `start-local.ps1`, backend test/E2E environment setup.
- **Evidence/security:** local checks and gaps are tabulated below. Existing uncommitted
  landing/login edits, sign-in regression, PDFs and application materials are preserved.
- **Limitations:** Docker CLI absent; no image build, hosted CI/staging or production
  migration/deployment. Dependency audits remain non-clean; current results are below.
- **Learning/reproduction:** use the guides and commands below with disposable data;
  production readiness requires independent operational and institutional evidence.
- **Next:** review these local commits; resolve the listed environment/native/source
  gates before separately authorized activation or deployment.

## Executed checks

| Check | Actual result |
| --- | --- |
| Initial baseline + extraction checks | 34 passed; a Windows temporary-path issue caused by an oversized pytest parameter ID was fixed in the test |
| SQLite lifecycle + migration checks | 11 passed; schema parity and downgrade/upgrade included |
| Initial complete backend suite | 417 passed, 1 skipped, 17 existing warnings, 324.14s |
| Complete backend suite after metrics/components | 422 passed, 2 PostgreSQL skips, 17 existing warnings, 200.87s |
| **Final complete backend suite on committed application code** | **424 passed, 2 expected dedicated PostgreSQL skips**, 17 existing Starlette/httpx/Alembic warnings, 127.89s; includes quotation and upload-retry fixes |
| Supplemental final RAG/operational tests after quotation safeguard | 57 passed, 2 expected DB skips, 14.81s |
| Final assistant/API checks after streaming body cap | 22 passed, 3.82s |
| Upload retry regression | 11 store/API tests passed, 9.52s; identical metadata/content returns the existing version even without a document ID |
| Full frontend unit suite (one worker, no competing heavy work) | 67 passed, 19 files, 151.59s. Earlier overlapping workloads triggered an existing scientific-evidence timeout; sequential rerun passed without changing those tests |
| Typecheck/lint/production build | Passed. Final Vite build 1m20s; existing font-resolution and Mapbox chunk-size warnings remain. Initial new test used unsupported Testing Library `exact`; corrected to an anchored name matcher |
| PostgreSQL/PostGIS fresh migrations and schema comparison | Passed, zero schema differences; downgrade one revision and re-upgrade passed |
| Dedicated PostgreSQL knowledge migration/ACL/portable vectors/deletion | 1 passed, 1 pgvector skip. Final rerun 1.80s. Pgvector extension is absent |
| Existing PostGIS spatial/scientific workflow rehearsal | Passed: synthetic spatial round trip, row lock, yield 75%, rainfall anomaly 50%, downtime 6h; fixtures rolled back. These are test values, not district measurements |
| Full Playwright regression | Final rerun: **32 passed**, zero retries, 3.7m, including five role setup checks, both language choices, feedback, upload retry, pending invisibility, approval, retrieval and removal. First run was 31 passed/1 failed (4.3m); the retry defect was fixed rather than weakening the scenario |
| Retrieval benchmark, chunk sensitivity and claim-support challenge | Executed locally; actual values above and in versioned JSON; zero provider calls |
| Actual embedding quality / real OpenAI or Ollama generation | Not executed; no weights/runtime/provider activation |
| Docker / hosted CI / deployment / live messaging | Not executed; Docker unavailable and no deployment/live activation authorized |
| Production frontend dependency audit | Executed `npm audit --omit=dev --json`: 3 findings, 1 high (Zod) and 2 moderate (React Router / React Router DOM). The suggested fixes are major-version migrations; no forced dependency rewrite was applied |
| Installed Python environment dependency audit | Executed isolated pip-audit 2.10.1 against `.venv/Lib/site-packages`: 9 advisory entries in 4 packages, representing 7 unique advisory IDs. Findings remain in certifi, opentelemetry-api, pyasn1 and pytest; see details below |
| Updated local demonstration platform | `/health` and `/ready` return 200; development bypass false; unsigned assistant and source-management requests return 401. Existing demo data preserved; demo-only migration advanced to `20261117_30`, generation/uploads remain off |

The first PostGIS workflow command correctly refused a database ending `_test`;
that pre-existing guard requires `_validation`. A separate disposable validation DB
was created and the check then passed. No guard or existing database was changed.

Local logs are ignored under `backend/.pytest-tmp/`: `rag-e2e-final-20261118.log`,
`rag-backend-final-20261118.log`, `local-rag-20261118.stdout.log` and
`local-rag-20261118.stderr.log`. The demo initially needed cold-start time before
health checks succeeded; the final checks above passed. The disposable PostgreSQL
cluster was stopped after validation. The normal existing PostgreSQL service and
application databases were not used. The E2E count includes the preserved, unstaged
sign-in regression from earlier work, which is intentionally outside these commits.

### Dependency audit limits and unresolved findings

Functional tests pass; dependency audits do not. `npm audit` suggests Zod 4.6.7 and
React Router DOM 7.18.5, both major migrations requiring a separate compatibility
review. The installed Python environment reports certifi 2026.7.22 (fix 2026.10.18),
opentelemetry-api 1.45.1 (fix 1.45.2), pyasn1 0.6.4 (fix 0.6.5), and pytest 8.4.2
(fix 9.0.3). The pytest fix is outside the current `<9` requirement. Some packages
may be environment/tooling dependencies; this installed-environment audit is not a
claim about every fresh CI/production resolution. Duplicate advisory IDs in the
upstream data are counted explicitly above. Optional pypdf 6.21.4 had no reported
findings in this run; that is not a general parser-safety certification.

Audit tooling was installed under an ignored, separate workspace virtual environment,
so auditing did not upgrade the tested application environment. Reports are ignored
at `backend/.pytest-tmp/rag-npm-audit-20261118.json` and
`backend/.pytest-tmp/rag-python-audit-20261118.json`. Dependency remediation and its
compatibility regression pass remain release work, alongside the model/native/vector
gates. No production-readiness claim is made while these findings remain open.

## Reproduction commands

From `backend`, using the repository virtual environment:

```powershell
../.venv/Scripts/python.exe -m pytest -q --basetemp=.pytest-tmp/rag-review -o cache_dir=.pytest-tmp/rag-cache --tb=short
../.venv/Scripts/python.exe scripts/evaluate_rag.py --method legacy --output ../docs/ai/review-legacy.json
../.venv/Scripts/python.exe scripts/evaluate_rag.py --method bm25 --output ../docs/ai/review-bm25.json
../.venv/Scripts/python.exe scripts/check_rag_chunks.py
../.venv/Scripts/python.exe scripts/evaluate_citation_support.py
```

Use ignored output paths for ad-hoc reports if they are not intended for review.
The frozen baseline and current BM25 report include exact dataset/corpus hashes.

From `frontend`:

```powershell
npm run typecheck
npm run lint
npm test -- --maxWorkers=1 --no-file-parallelism
npm run build
$env:PYTHON='../.venv/Scripts/python.exe'
npm run e2e
```

The PostgreSQL rehearsal used only a newly initialized workspace cluster under
`backend/.pytest-tmp/rag-postgis-20261118`, loopback port 55443, synthetic owner
`validation_owner`, databases `cs_ircfs_rag_20261118_test` and
`cs_ircfs_rag_20261118_validation`. Existing port 5432/application DBs were untouched.
Set `RAG_TEST_POSTGRES_URL` only for a dedicated database ending `_test`; this opts
into temporary-schema tests. The spatial workflow checker separately requires an
explicit local `_validation` database. The new cluster uses trust authentication
solely for disposable local validation and must never be used for hosting.

## Reviewable file groups and PR summary

- **Knowledge schema/lifecycle:** `backend/app/db/knowledge.py`, registration in
  `db/models.py`, migration `20261117_30_knowledge.py`, `rag/store.py`.
- **Retrieval/AI components:** every module in `backend/app/services/rag/` and
  `backend/app/services/assistant.py`; approved fixed corpus `platform.json` preserved.
- **API/configuration/metrics:** `backend/app/api/routes/assistant.py`,
  `backend/app/core/{config,metrics}.py`, `.env.example`, optional requirements files.
- **Evaluation/tools:** both evaluation JSON datasets, `scripts/evaluate_rag.py`,
  `evaluate_citation_support.py`, `check_rag_chunks.py`, frozen/current result JSON.
- **Tests/isolation:** `backend/tests/test_assistant.py`, every `test_rag_*.py`,
  `tests/conftest.py`, `scripts/run_e2e_server.py`, `start-local.ps1`, `.gitignore`.
- **Frontend:** both assistant components and tests, `frontend/e2e/15-assistant.spec.ts`.
- **Documentation:** README, roadmap, document-assistant guide and all eight AI guides
  plus this validation report. Personal/unrelated work is outside these commits.

PR summary: add approved knowledge ingestion and permissions to the staff assistant,
measure BM25 against a frozen benchmark, introduce optional local retrieval/provider
adapters, constrain generation to source quotations, and add contextual/cited UI and
privacy-preserving metrics. Keep activation gates explicit; this package supports
review of a locally tested foundation rather than declaring all production RAG
capabilities complete.

## Exact changed-file manifest

Compared with `8105ca6`; excludes unrelated unstaged work.

```text
.env.example
.gitignore
README.md
backend/app/api/routes/assistant.py
backend/app/core/config.py
backend/app/core/metrics.py
backend/app/db/knowledge.py
backend/app/db/models.py
backend/app/knowledge/citation_evaluation.json
backend/app/knowledge/evaluation.json
backend/app/services/assistant.py
backend/app/services/rag/__init__.py
backend/app/services/rag/chunking.py
backend/app/services/rag/citations.py
backend/app/services/rag/embeddings.py
backend/app/services/rag/evaluation.py
backend/app/services/rag/ingestion.py
backend/app/services/rag/observability.py
backend/app/services/rag/prompts.py
backend/app/services/rag/providers.py
backend/app/services/rag/retrieval.py
backend/app/services/rag/safety.py
backend/app/services/rag/store.py
backend/app/services/rag/vectors.py
backend/migrations/versions/20261117_30_knowledge.py
backend/requirements-rag-models.txt
backend/requirements-rag.txt
backend/scripts/check_rag_chunks.py
backend/scripts/evaluate_citation_support.py
backend/scripts/evaluate_rag.py
backend/scripts/run_e2e_server.py
backend/tests/conftest.py
backend/tests/test_assistant.py
backend/tests/test_rag_api.py
backend/tests/test_rag_evaluation.py
backend/tests/test_rag_ingestion.py
backend/tests/test_rag_observability.py
backend/tests/test_rag_postgres.py
backend/tests/test_rag_retrieval.py
backend/tests/test_rag_store.py
docs/ai/AI_ENGINEERING_GUIDE.md
docs/ai/DEPLOYMENT.md
docs/ai/EMBEDDINGS.md
docs/ai/PROMPT_ENGINEERING.md
docs/ai/RAG_ARCHITECTURE.md
docs/ai/RAG_EVALUATION.md
docs/ai/RETRIEVAL_PIPELINE.md
docs/ai/SECURITY.md
docs/ai/VALIDATION_2026-11-18.md
docs/ai/baseline-results.json
docs/ai/bm25-results.json
docs/ai/citation-support-results.json
docs/document-assistant.md
docs/roadmap.md
frontend/e2e/15-assistant.spec.ts
frontend/src/features/assistant/AssistantPage.test.tsx
frontend/src/features/assistant/AssistantPage.tsx
frontend/src/features/assistant/KnowledgePanel.test.tsx
frontend/src/features/assistant/KnowledgePanel.tsx
start-local.ps1
```
