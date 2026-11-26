# CS Assistant local AI and document workspace — 20 November 2026

## Changes

Implemented a visibly different workspace with conversation rail, document picker,
composer attachment button, source selection and summary shortcut. Added an
authenticated local-model readiness check, llama.cpp provider and workspace-only
startup/download helpers. Added per-conversation document selection and server-side
rejection of unauthorized/pending/missing selections. Uploaded source generation is
allowed only for authorized, reviewed English content through local providers.

Actual API uploads now use a bounded disposable parser process with a stripped
environment. PDF/DOCX/TXT tests exercise this process. The parser has resource limits
and timeout cleanup; it is not a full filesystem/network sandbox. Upload activation
still requires explicit extraction-environment approval and document-level review.

## Local model provenance and configuration

- Hardware inspected: Intel i5-1334U, 8 GB physical RAM, integrated Intel graphics.
- Runtime: [official llama.cpp b12559 CPU release](https://github.com/ggml-org/llama.cpp/releases/tag/b12559), 24,876,565-byte ZIP.
  SHA-256 `2f3dcb3aea4f52bf734f52040d2a688bdd76c2f762ae200a159646b37d84e393`.
- Model: [official Qwen2.5-1.5B-Instruct GGUF](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF), revision
  `91cad51170dc346986eccefdc2dd33a9da36ead9`, Q4_K_M, 1,117,320,736 bytes.
  SHA-256 `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`.
- Both published hashes were verified before the runtime/model was executed/loaded.
- Loopback-only server, generated API key, web UI/MCP proxy disabled, four threads,
  4,096-token context, one slot. No OS installation, paid API or model-provider egress.
- The running local demo was started with `-Demo -LocalAI`. Readiness inspection
  returned `generation_ready=true`, `local_provider=true`, `uploads_enabled=false`.
- Model files, runtime, private access key and logs are ignored by Git; ignore checks passed.

## Actual checks

| Check | Result |
| --- | --- |
| Combined assistant/local parser/API/citation/management regression | 52 passed |
| Dedicated local/parser/selection checks | 7 passed after fixing distinct packaged-source identifiers |
| Chat, document picker and knowledge UI tests | 10 passed |
| Production build and TypeScript | Passed |
| ESLint | Passed |
| Standard Chrome desktop/mobile/approval workflow | 10 passed in 33.2 seconds, using disposable fixtures and generation disabled |
| Three real local-model questions | Two validated generated replies; one verified document fallback |
| Combined local-model + uploaded-document browser test | Prepared; execution rejected pending extraction-environment approval |

The real-model artifact is `local-ai-smoke-2026-11-20.json`. It uses packaged
engineering excerpts only. USSD-language reply validated in 2.85 seconds; SMS
delivery reply validated in 9.86 seconds; rainfall query fell back after 8.15 seconds.
These three smoke cases are not a statistically representative model-quality,
concurrency or performance benchmark. No claims of general AI accuracy are made.

An uncited but verbatim first-model reply initially failed citation checks. The
application now attributes only exact complete source quotations; tests reject
invented text, forged explicit citations and extra claims. No citation validation
was weakened to accommodate the small model.

Windows' venv interpreter launcher initially hit the single-process Job Object
limit. The tested two-process bound accommodates launcher/interpreter while keeping
aggregate memory/CPU/time bounds. Parser tests cover real synthetic PDF and DOCX,
text, malformed input, timeout cleanup and upload permission checks. The temporary
process receives no database/API credentials from the backend environment.

## Upload gate and automatic review

Automatic approval review rejected the `E2E_LOCAL_AI=true` upload browser command
because it enables ingestion before the owner's specified extraction approval.
The action has not been retried or bypassed. A specific approval request was sent
for this laptop's local demo environment and final combined test. Real demo uploads
remain disabled pending that response; no private file has been indexed.

## Remaining limits

- Local AI is source-grounded/extractive, not unrestricted general-purpose chat.
- On unsupported, busy, offline or invalid model output, verified excerpts remain
  available and are labeled as fallback. Three smoke cases do not establish reliability.
- A bounded parser is not a full OS sandbox. Production/public uploads need a
  constrained worker environment and separate review before activation.
- Native language acceptance, comprehensive secret/injection detection, source truth,
  long-document summarization quality and real semantic/pgvector/reranker evaluation
  remain outstanding. The new decoder does not satisfy the embedding benchmark gate.
- Chat history remains page-local and bounded; no persistent chat database or raw
  question/source logging was added. No deployment, main push or paid API activation.

Layout evidence: [desktop](../images/assistant-workspace-2026-11-20.png) and
[mobile](../images/assistant-workspace-mobile-2026-11-20.png). These standard-test
screenshots deliberately show AI disconnected; the running demo uses the real local
model whose readiness/smoke results are recorded above.
