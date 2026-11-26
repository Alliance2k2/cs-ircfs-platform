# Embeddings and model evaluation gates

An encoder maps text to a vector `v = f(text)`. Similar directions can indicate
related meaning. L2 normalization gives `v / sqrt(sum(v_i²))`. Cosine similarity is
`sum(q_i*d_i) / (||q||*||d||)`; identical nonzero vectors score 1, orthogonal vectors 0.
`rag/embeddings.py` rejects zero, nonfinite and mismatched vectors. Dimensions come
from output, not a hardcoded 384/1024 assumption. Cosine is not a confidence score.

`EmbeddingProvider` permits a local implementation or synthetic test implementation.
`LocalEmbeddings` uses CPU, batches of eight, bounded inputs, normalized vectors,
hashed text-cache keys, a 2,048-entry in-memory cache, immutable-revision configuration,
no remote code and local-files-only loading. Tokenizer limits are checked before
encoding; oversized chunks require reindexing rather than silent truncation.
Concurrent requests to a busy encoder fall back to keywords.

`vectors.index_chunks` persists vectors keyed by chunk ID and model revision. New
model IDs produce separate rows; queries filter the exact model and dimensions.
It skips already indexed chunk/model pairs. Source deletion removes associated
vectors. The request path currently uses the bounded in-memory model cache; the
persistent adapter is not yet selected by the HTTP orchestration. Do not call it
an operational HNSW service.

The portable schema stores JSON arrays. An optional PostgreSQL adapter performs
**exact** pgvector distance by casting authorized vectors after filtering; it
checks extension availability and never installs extensions. Native vector-column
storage, HNSW and large-corpus retrieval are deferred until a real deployment and
dataset justify them. Local vector selection is capped at 2,000 candidates.

## Candidates, not production selections

The [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
describes a lightweight English sentence encoder. The
[BGE-M3 model card](https://huggingface.co/BAAI/bge-m3) describes multilingual
representations with longer inputs. Neither establishes Kinyarwanda quality here.
Multilingual E5 is another candidate, with model-specific query/document prefixes
that require their own adapter and evaluation before use.

No actual model weights, torch or sentence-transformers runtime were installed
during this validation. No English/RW semantic or hybrid quality metrics are claimed.
Synthetic two-dimensional fixture vectors validate plumbing only.

To evaluate later, provision reviewed model snapshots and the optional
`requirements-rag-models.txt` runtime in an isolated environment. Set a local
`ASSISTANT_EMBEDDING_PATH` and immutable `ASSISTANT_EMBEDDING_REVISION`, then choose
`ASSISTANT_RETRIEVAL_MODE=semantic` or `hybrid`. Missing runtime/weights and encoder
errors yield an explicit lexical fallback. Measure both languages, cross-language
retrieval, latency and memory before selecting a model or enabling the feature.
The [Sentence Transformers reference](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html)
documents local-only loading. The [pgvector reference](https://github.com/pgvector/pgvector)
documents cosine distance and index tradeoffs.
