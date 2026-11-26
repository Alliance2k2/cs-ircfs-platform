# Prompting, providers and citation limits

The versioned `rag/prompts.py` prompt `evidence-en-v3-extractive` asks for complete
verbatim English evidence sentences, each paragraph followed by its source citation.
It preserves qualifications/negation and requests an empty result if no supporting
sentence exists. Documents and user messages are untrusted data.
No tools, SQL, network browsing or operational actions are exposed to models.

The `Generator` protocol returns text and reported token counts. OpenAI Responses
uses a fixed HTTPS endpoint, `store:false`, a 20-second timeout and an 800-output-token
limit. Only 429/503 responses permit one retry; transport timeouts are not retried.
`store:false` is not a promise of zero provider retention. See the
[official OpenAI reference](https://developers.openai.com/api/reference/resources/responses/methods/create).
Ollama uses only loopback `127.0.0.1:11434`, no environment proxy or redirects,
non-streaming bounded generation and an already installed model. It never pulls
weights. Its adapter follows the [official chat reference](https://docs.ollama.com/api/chat).

Both providers stay behind `ASSISTANT_GENERATION_ENABLED=false` by default. Managed
documents and RW requests are denied generation even if this flag is enabled.
Provisioning keys, choosing paid models, approving external processing and live
provider health/acceptance require explicit operator authorization. No remote health
probe runs automatically. Model pricing is not hardcoded; actual cost is unknown
unless an approved billing integration supplies it.

`rag/citations.py` rejects unknown/missing IDs and uncited paragraphs, then verifies
that every generated paragraph contains complete verbatim sentences from its cited
source. Output privacy patterns and length limits are also checked. Invalid output
falls back to retrieved excerpts. The UI notice identifies AI-selected quotations.
Free paraphrases are deliberately refused until a support evaluator is validated.

The eight-case engineering challenge set contains two supported and six unsupported
claims, each annotated with actual source evidence. Structural ID checks accept all
six unsupported claims; extractive checks reject all six and accept both supported
quotations. Run `python scripts/evaluate_citation_support.py`. This is a small
deterministic provenance check, not a measured model hallucination rate. It cannot
prove source truth, complete coverage or appropriate context; misleading selective
quotation remains possible. There is no semantic verifier for arbitrary paraphrases.

History contains at most three earlier user questions, each <=1,200 characters.
Simple English follow-ups may carry the immediately preceding question into the
retrieval query. Prior generated answers are not evidence. Every carried question
passes the same privacy/injection guards. History has no ownership table or storage:
it is supplied from the current browser page, untrusted and never an ACL authority.
No persistent conversation is introduced, so there is no server retention/deletion
policy to falsely promise. Clear/navigation discards UI history.
