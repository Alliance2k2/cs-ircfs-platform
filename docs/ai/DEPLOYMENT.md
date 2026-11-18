# Deployment preparation (no deployment performed)

Keep the existing FastAPI/PostgreSQL/React deployment. This change needs migration
`20261117_30`; it adds knowledge tables without changing participant/report data or
installing extensions. Back up the intended database and validate staging first.

```powershell
cd backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe scripts/check_schema.py
```

These commands target your configured database. Do not run them against production
without its separate approved deployment procedure. SQLite migration regression
tests use disposable files and verify downgrade/upgrade/schema parity.

Default setup needs no extra model/parser dependencies. Optional trusted PDF
extraction uses `requirements-rag.txt` (pypdf); install it in a constrained worker
environment before enabling `ASSISTANT_INGESTION_ENABLED`. Text/DOCX parsing is
standard-library based. The current HTTP implementation runs extraction off the event
loop but does not provide process isolation or a hard parser CPU timeout. Do not
enable public uploads. Institutional sources require independent review references.

```dotenv
ASSISTANT_INGESTION_ENABLED=false
ASSISTANT_RETRIEVAL_MODE=bm25
ASSISTANT_TOP_K=3
ASSISTANT_MINIMUM_SCORE=0
ASSISTANT_GENERATION_ENABLED=false
ASSISTANT_PROVIDER=openai
ASSISTANT_EMBEDDING_PATH=
ASSISTANT_EMBEDDING_REVISION=
ASSISTANT_SEMANTIC_THRESHOLD=0.4
```

`legacy` permits baseline retrieval rollback; `semantic`/`hybrid` require separately
provisioned local models/runtime. Missing models safely fall back to BM25. Ordinary
Docker builds do not install model runtimes or weights. No local Ollama service was
started. External provider credentials, activation and billing stay unmodified.

The pgvector adapter requires an **already installed** extension. The migration does
not request extension privileges. The portable JSON vector representation and exact
cast search are a pilot fallback, not HNSW/native-index deployment. Provision a
disposable database ending `_test` and set `RAG_TEST_POSTGRES_URL` to run the opt-in
distance test. It must never point to production. Tests include portable lifecycle,
ACL, incremental vectors, deletion and migration rollback in an isolated schema;
pgvector comparison runs only when the extension is installed. Local PostgreSQL 18
migrations/schema/portable lifecycle passed on 18 November; pgvector was unavailable.
Native indexed storage remains a separate implementation/validation gate.

Operator checks: staff sign-in, monitor denial, source pending invisibility,
role/geography exclusions, version replacement, deletion synchronization, malformed
file refusal, generation off, feedback log access, UI safe rendering and rollback.
Monitor existing structured logs for retrieval mode/source count/latency,
provider failures/reported tokens and categorical feedback. The protected `/metrics`
endpoint adds bounded process-local assistant counters, latency totals and hashed
model-revision counts. No prompts, source contents or account IDs are collected.
Unknown API cost is `null`. There is no durable feedback dashboard, cost calculator,
distributed quota or model health monitor yet.

No production migrations, deployment, live messages, model downloads, real AI calls,
secret changes or paid services were authorized or performed during this work.
