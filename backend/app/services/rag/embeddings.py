"""Optional CPU-only local embeddings; no downloads or remote-code execution."""
import hashlib
import math
from collections import OrderedDict
from typing import Protocol
from functools import lru_cache
from threading import Lock


class EmbeddingProvider(Protocol):
    model_id: str

    def encode(self, texts: list[str]) -> list[list[float]]: ...


def normalize(vector):
    values = [float(value) for value in vector]
    norm = math.sqrt(sum(value * value for value in values))
    if not values or len(values) > 8192 or not math.isfinite(norm) or norm == 0:
        raise ValueError("Invalid embedding")
    return [value / norm for value in values]


def cosine(left, right):
    if len(left) != len(right):
        raise ValueError("Embedding dimensions do not match; reindex the model")
    return sum(a * b for a, b in zip(normalize(left), normalize(right)))


class LocalEmbeddings:
    def __init__(self, path: str, revision: str, batch_size=8):
        if not path or not revision or not 1 <= batch_size <= 32:
            raise ValueError("Model path, immutable revision and bounded batch required")
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(path, revision=revision, device="cpu", trust_remote_code=False, local_files_only=True)
        self.model_id = f"{path}@{revision}"
        self.batch_size = batch_size
        self.cache = OrderedDict()
        self.lock = Lock()

    def encode(self, texts):
        if not self.lock.acquire(blocking=False):
            raise ValueError("Embedding worker busy; use lexical fallback")
        try:
            return self._encode(texts)
        finally:
            self.lock.release()

    def _encode(self, texts):
        if len(texts) > 2000 or any(len(text) > 16000 for text in texts):
            raise ValueError("Embedding input limit exceeded")
        if any(len(self.model.tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"]) > self.model.max_seq_length for text in texts):
            raise ValueError("Chunk exceeds model tokenizer limit; reindex with smaller chunks")
        hashes = [hashlib.sha256(text.encode()).hexdigest() for text in texts]
        missing = {digest: text for digest, text in zip(hashes, texts) if digest not in self.cache}
        if missing:
            values = self.model.encode(list(missing.values()), batch_size=self.batch_size, normalize_embeddings=True, show_progress_bar=False)
            if len(values) != len(missing):
                raise ValueError("Incorrect embedding count")
            for digest, vector in zip(missing, values):
                self.cache[digest] = normalize(vector)
        result = [list(self.cache[digest]) for digest in hashes]
        while len(self.cache) > 2048:
            self.cache.popitem(last=False)
        return result


_MODEL_LOCK = Lock()


@lru_cache(maxsize=1)
def _load_provider(path, revision):
    return LocalEmbeddings(path, revision)


def local_provider(path, revision):
    if not _MODEL_LOCK.acquire(blocking=False):
        raise ValueError("Embedding model is loading; use lexical fallback")
    try:
        return _load_provider(path, revision)
    finally:
        _MODEL_LOCK.release()


def semantic(question, sources, provider, top_k=3, threshold=.4):
    if not sources:
        return []
    vectors = provider.encode([question] + [row["text"] for row in sources])
    if len(vectors) != len(sources) + 1:
        raise ValueError("Provider returned wrong embedding count")
    ranked = [(cosine(vectors[0], vector), source) for vector, source in zip(vectors[1:], sources)]
    return [dict(source, retrieval_score=round(score, 6)) for score, source in sorted(ranked, key=lambda row: (-row[0], row[1]["id"])) if score >= threshold][:top_k]
