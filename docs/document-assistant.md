# Staff document assistant

## Current extension — 18 November 2026

The assistant now supports BM25 retrieval, optional local semantic/hybrid adapters,
and approved knowledge versions alongside the six packaged engineering summaries.
Administrator management handles bounded PDF/DOCX/TXT/Markdown/CSV/JSON extraction,
pending review, explicit approval, new versions and removal. Roles and required
sector sets are checked before chunk text is selected. Source classifications and
PDF page references remain visible. Uploads are disabled by default pending an
approved extraction environment. No participant, grievance or personal-file crawling
is introduced.

The UI supports up to three recent user questions for simple follow-ups, an explicit
English/Kinyarwanda choice, copying, categorical feedback and clearing. Kinyarwanda
retrieval remains experimental; excerpts retain their source language and native
review is pending. Conversations remain browser-memory only.

Migration `20261117_30` adds dedicated knowledge tables. Default retrieval needs no
model or provider. Optional local embeddings require separately provisioned weights
and runtime; actual model quality has not been evaluated. PostgreSQL/PostGIS schema
and portable lifecycle validation passed; pgvector is absent locally, so its adapter
remains unverified. The JSON vector adapter is a pilot fallback, without HNSW.

External generation remains disabled. Its provider interface preserves OpenAI
Responses and adds optional loopback Ollama. Generated output must quote complete
verbatim sentences from cited excerpts; unsupported paraphrases fall back to source
excerpts. Managed sources and RW requests cannot be sent to either generator.
Citation provenance does not prove source truth or complete contextual coverage.

See [architecture and audit](ai/RAG_ARCHITECTURE.md), [beginner guide](ai/AI_ENGINEERING_GUIDE.md),
[configuration and deployment](ai/DEPLOYMENT.md), [evaluation](ai/RAG_EVALUATION.md)
and [current validation](ai/VALIDATION_2026-11-18.md). These supersede behavioral and
configuration descriptions in the historical baseline below.

## Historical 17 November baseline (`8105ca6`)

The following records the original pilot and its original validation counts.

The dashboard's **Document assistant** at `/app/assistant` answers questions about platform procedures. Access is limited to district officers, planners and administrators in both the UI and `POST /api/v1/assistant/ask`. Monitor/cooperative/public access is refused. Questions are limited to 1,200 characters and requests are rate-limited to 10/minute per client address by the existing limiter.

## What works in the first version

The collection is six engineering-reviewed procedure excerpts in `backend/app/knowledge/platform.json`: USSD onboarding/language, rainfall, scientific verification, delivery reconciliation, privacy and staging. These are summaries of the referenced repository documents, not district-approved agronomic guidance. Updating a source document does not automatically update an excerpt: review the excerpt in the same PR. Each returned excerpt has its source reference and a reproducible content revision hash.

Local lexical retrieval ranks overlapping question and document words, weighting titles. It returns at most three excerpts. This is a small, inspectable starting point, not semantic embeddings or an exhaustive knowledge base. Default answers quote the retrieved excerpts and explicitly identify themselves as document lookup. Unmatched questions return a no-evidence response. Matching text does not establish that every question can be answered by it.

Optional generation sends only the question and retrieved excerpts to the OpenAI Responses API. It has no tool calls, database queries, browsing or write actions. Instructions restrict answers to evidence; unknown/missing citation IDs, uncited answers, incomplete responses and provider failures fall back to excerpts. Citation-ID validation is **not semantic fact checking**: staff must inspect sources. Sources and questions are treated as untrusted content; prompt instructions are a defense, not a proof against every prompt injection.

The conversation is bounded to ten displayed exchanges in React memory, clears on navigation, and is not written to local storage or a chat table. Each question is independent; follow-up pronouns do not inherit conversation context. Responses render as plain text, with expandable source excerpts; generated HTML/Markdown is not executed.

## Privacy and operating limits

- The service never indexes participant tables, grievance records, `.env`, application materials, uploads or arbitrary repository files. Its only input collection is the fixed packaged JSON file.
- Sector-restricted staff receive the same general procedure collection; there are no area-specific records in this index. Future private-record retrieval must enforce role/sector scopes **before** retrieval.
- Basic phone/email and recognizable credential patterns are rejected before provider access. This is not comprehensive PII detection: names, unusual identifiers and arbitrary secrets may evade heuristics. Never enter personal data or credentials.
- External generation is off by default. When enabled, questions/excerpts leave the platform; the UI discloses this. `store: false` is requested, but is not a guarantee of zero provider retention. Review provider data processing, retention, spending and approved model access before enabling it.
- English only in this pilot. Existing dashboard navigation can fall back to English. Native-approved Kinyarwanda answers, agricultural advice, live totals, institutional baselines and participant case lookup are not implemented.
- No message sends, airtime, record changes, official approvals or deployments can be performed by this assistant.

## Configuration

The default requires no provider credentials, embeddings or new database migration. The existing container copies `backend/app`, including the packaged collection. Demo startup and browser/backend tests force generation off independently of `.env`.

After the owner approves external generation, configure outside Git:

```dotenv
ASSISTANT_GENERATION_ENABLED=true
ASSISTANT_MODEL=YOUR_APPROVED_MODEL
ASSISTANT_OPENAI_API_KEY=YOUR_SECRET_FROM_THE_PROVIDER
```

Do not paste real credentials into documentation or issue reports. An empty model/key causes safe excerpt fallback. Restart the application after approved configuration changes. The endpoint is fixed to `https://api.openai.com/v1/responses`, uses a 20-second timeout, sends no tools, and caps generated output at 800 tokens. Set provider-side spending limits before activation; application rate limiting is not a spending budget. Disable `ASSISTANT_GENERATION_ENABLED` to return to local mode.

The adapter follows the [official Responses API reference](https://developers.openai.com/api/reference/resources/responses/methods/create). All provider tests use synthetic credentials and mocked HTTP; no real generation, billing or provider retention behavior has been validated.

## Validation

Environment: Windows, repository Python 3.13.9, Node v24.20.0 and installed Chrome. Test databases are disposable SQLite; generation is mocked/off. No new dependency or database migration was introduced; schema head remains `20261113_29`.

| Executed check | Result |
| --- | --- |
| `cd backend; ../.venv/Scripts/python.exe -m pytest tests/test_assistant.py -q` with disposable temp/cache paths | Initial 12 passed, 23.86s; a credential-pattern case was then added |
| `cd backend; ../.venv/Scripts/python.exe -m pytest -q --basetemp=.pytest-tmp/assistant-full-20261117 -o cache_dir=.pytest-tmp/assistant-cache --tb=short` | 381 passed, 250.00s |
| Same complete suite with `--basetemp=.pytest-tmp/assistant-final-20261117` after refining phone detection | **381 passed**, 246.30s, 17 existing Starlette/httpx and Alembic deprecation warnings |
| `cd frontend; npm test -- --maxWorkers=1 --no-file-parallelism` | **63 passed**, 18 files, 222.07s; includes plain-text/XSS rendering and error recovery tests |
| `npm run typecheck`; `npm run lint`; `npm run build` | Final checks passed; Vite 1m 16s. An initial build caught a test-only `exact` option unsupported by Testing Library; corrected to an anchored accessible-name matcher |
| Complete `npm run e2e` with `PYTHON=../.venv/Scripts/python.exe` | **29 passed**, zero retries, 7.1 minutes, including cited retrieval, no-evidence handling and clearing the assistant conversation |
| Local demo restart and read-only checks | Health 200, development sign-in bypass false, unsigned assistant request 401. Assistant page opened in the browser. Existing demo records preserved; generation/telecom remain off |
| Docker/hosted/live generation | Not verified. Docker CLI unavailable; no feature publication, deployment or real provider call performed |

Ignored logs: `backend/.pytest-tmp/assistant-full-20261117.log`, `assistant-final-20261117.log`, `e2e-assistant-20261117.log`. Existing font-path and Mapbox chunk-size build notices remain. The working tree includes preserved earlier login changes; its full browser count includes that sign-in regression. Prior dependency-advisory and native/carrier gates remain open and were not re-audited as part of this feature.

## File-level change summary

| Files | Purpose |
| --- | --- |
| `backend/app/knowledge/platform.json` | Fixed engineering-reviewed procedure collection |
| `backend/app/services/assistant.py` | Lexical retrieval, source revisions, privacy heuristics, optional Responses generation and safe fallback |
| `backend/app/api/routes/assistant.py`, `backend/app/main.py` | Staff-only rate-limited API and registration |
| `backend/app/core/config.py`, `.env.example` | Off-by-default generation, masked key and explicit model configuration |
| `start-local.ps1`, `backend/scripts/run_e2e_server.py`, `backend/tests/conftest.py` | Force external generation off in demo/tests |
| `backend/tests/test_assistant.py` | Permissions, local/no-evidence behavior, privacy, question bounds and mocked provider/citation errors |
| `frontend/src/features/assistant/AssistantPage.tsx`, `AssistantPage.test.tsx` | Accessible question/history/source UI, clear/error states and rendering tests |
| `frontend/src/app/routing/AppRoutes.tsx`, `frontend/src/components/navigation/nav.ts`, `frontend/src/i18n/en.ts` | Staff route, lazy chunk, navigation/search and English fallback label |
| `frontend/e2e/15-assistant.spec.ts` | Real browser/API local retrieval, citations, no-evidence and clear workflow |
| `README.md`, `docs/roadmap.md`, this file | Feature scope, operations, evidence and remaining gates |

Existing dashboard/login changes, the prior sign-in regression, PDFs and application materials were preserved outside this feature's commit scope.

Implementation branch: `feature/document-assistant-20261117`, based on `7b7faea`. Local validation is complete for document lookup and mocked generation. Real provider acceptance, institutional approval, hosted CI and production readiness are not claimed. Nothing was pushed, merged or deployed.

## Next extension gates

1. Review this pilot with district staff and evaluate retrieval on a real question set, including irrelevant/adversarial queries.
2. Select approved documents, reviewers, model/provider processing and spending limits before enabling external AI. Obtain native review before adding Kinyarwanda.
3. Add semantic retrieval or scoped live APIs only after retrieval quality and authorization tests justify them. Never infer official baselines from generated text.
