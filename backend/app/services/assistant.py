"""Read-only document retrieval and opt-in generation. No participant database access."""
import hashlib
import json
import re
import logging
import time
from functools import lru_cache
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.services.rag.retrieval import bm25, context
from app.services.rag.safety import INJECTION, LIVE, PRIVATE_REQUEST, language_hint, rewrite
from app.services.rag.providers import OpenAIResponses, Ollama
from app.services.rag.citations import validate_extractive
from app.services.rag.prompts import VERSION
from app.services.rag.embeddings import local_provider, semantic
from app.services.rag.retrieval import fuse
from starlette.concurrency import run_in_threadpool
from app.services.rag.observability import record

logger = logging.getLogger(__name__)

STOP = set("how do does i the is a an can what for to and of in with my are on it use me please".split())
PERSONAL = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|(?:\+?\d[\s().-]*){9,}", re.I)
SECRET = re.compile(r"\b(?:sk-[\w-]{12,}|ghp_[\w]{12,}|AKIA[A-Z0-9]{16})|BEGIN .*PRIVATE KEY", re.I)


def tokens(value):
    return set(re.findall(r"[^\W_]{3,}", value.lower())) - STOP


@lru_cache(maxsize=1)
def documents():
    # Fixed packaged collection: never crawl the repository, uploads, databases or URLs.
    return json.loads((Path(__file__).resolve().parents[1] / "knowledge" / "platform.json").read_text(encoding="utf-8"))


def retrieve(question):
    terms = tokens(question)
    ranked = []
    for doc in documents():
        matched = terms & tokens(doc["title"] + " " + doc["text"])
        if not matched:
            continue
        score = len(matched) + 2 * len(terms & tokens(doc["title"]))
        ranked.append((score, doc))
    ranked.sort(key=lambda row: (-row[0], row[1]["id"]))
    return [dict(doc, revision=hashlib.sha256(doc["text"].encode()).hexdigest()[:12]) for _, doc in ranked[:3]]


def local_response(question, selected_sources=None):
    """Network-free baseline shared with the offline benchmark."""
    if PERSONAL.search(question) or SECRET.search(question):
        return {"answer": "Please remove personal information and credentials. Ask about platform procedures without private data.", "mode": "privacy_refusal", "sources": []}
    sources = retrieve(question) if selected_sources is None else selected_sources
    if not sources:
        return {"answer": "I could not find supporting platform documentation. Please ask a district administrator or provide a reviewed source.", "mode": "no_evidence", "sources": []}
    result = {"answer": "Relevant document excerpts:\n\n" + "\n\n".join(f"[{row['id']}] {row['text']}" for row in sources), "mode": "documents", "sources": sources}
    return result


def safe_local_response(question, *, sources=None, method="bm25", top_k=3, minimum=0.0, embedder=None, semantic_threshold=.4):
    if INJECTION.search(question) or PRIVATE_REQUEST.search(question):
        return {"answer": "I cannot follow instructions to bypass safeguards or reveal private information. Ask about approved procedures.", "mode": "privacy_refusal", "sources": []}
    if LIVE.search(question):
        return {"answer": "I have no authorized live operational data. Please use the appropriate staff reporting page.", "mode": "no_evidence", "sources": []}
    corpus = sources if sources is not None else [dict(doc, revision=hashlib.sha256(doc["text"].encode()).hexdigest()[:12], classification="engineering", language="en") for doc in documents()]
    if method == "legacy" and sources is None:
        selected = retrieve(question)[:top_k]
    else:
        selected = bm25(question, corpus, top_k, minimum)
        if embedder is not None and method in {"semantic", "hybrid"}:
            dense = semantic(question, corpus, embedder, top_k, semantic_threshold)
            selected = dense if method == "semantic" else fuse([bm25(question, corpus, min(20, top_k * 2), minimum), dense], top_k)
    return local_response(question, context(selected))


async def _respond(question, *, additional_sources=None, language="auto", history=None):
    started = time.perf_counter()
    # Check original and carried user questions independently before rewriting.
    questions = [*(history or []), question]
    for previous in questions:
        if PERSONAL.search(previous) or SECRET.search(previous) or INJECTION.search(previous) or PRIVATE_REQUEST.search(previous):
            return local_response(previous) if PERSONAL.search(previous) or SECRET.search(previous) else safe_local_response(previous)
    query = rewrite(question, history or [])
    sources = None
    if additional_sources:
        sources = [dict(doc, revision=hashlib.sha256(doc["text"].encode()).hexdigest()[:12], classification="engineering", language="en") for doc in documents()] + additional_sources
    settings = get_settings()
    method = getattr(settings, "assistant_retrieval_mode", "bm25")
    embedder = None
    embedding_notice = None
    if method in {"semantic", "hybrid"}:
        try:
            embedder = await run_in_threadpool(local_provider, settings.assistant_embedding_path, settings.assistant_embedding_revision)
        except (ImportError, OSError, ValueError, RuntimeError):
            embedding_notice = "Local embedding model unavailable. Showing keyword retrieval."
            record("embedding_failure")
            logger.info("assistant_embedding_unavailable")
    try:
        result = await run_in_threadpool(safe_local_response, query, sources=sources, method=method,
            top_k=getattr(settings, "assistant_top_k", 3), minimum=getattr(settings, "assistant_minimum_score", 0.0),
            embedder=embedder, semantic_threshold=getattr(settings, "assistant_semantic_threshold", .4))
    except (ValueError, RuntimeError, OSError):
        result = safe_local_response(query, sources=sources)
        embedding_notice = "Embedding retrieval failed. Showing keyword retrieval."
        record("embedding_failure")
        logger.info("assistant_embedding_failure")
    if embedding_notice:
        result["notice"] = embedding_notice
    result["language"] = language_hint(question) if language == "auto" else language
    if result["language"] == "rw":
        result["notice"] = "Kinyarwanda retrieval is experimental and pending native review. Source excerpts retain their original language."
    logger.info("assistant_retrieval mode=%s sources=%d latency_ms=%.2f", result["mode"], len(result["sources"]), (time.perf_counter() - started) * 1000)
    record("retrieval", duration_ms=(time.perf_counter() - started) * 1000)
    if result["mode"] != "documents":
        return result
    sources = result["sources"]
    if not settings.assistant_generation_enabled:
        return result
    if any(source.get("document_id") for source in sources) or result["language"] != "en":
        result["notice"] = "Generation is disabled for managed knowledge and unreviewed languages. Showing source excerpts."
        return result
    key = settings.assistant_openai_api_key.get_secret_value()
    provider_name = getattr(settings, "assistant_provider", "openai")
    if (provider_name == "openai" and not key) or not settings.assistant_model.strip() or provider_name not in {"openai", "ollama"}:
        result["notice"] = "AI generation is not configured. Showing source excerpts."
        return result
    try:
        provider = OpenAIResponses(settings.assistant_model, key) if provider_name == "openai" else Ollama(settings.assistant_model)
        generation_start = time.perf_counter()
        generated = await provider.generate(query, sources)
        record("generation", duration_ms=(time.perf_counter() - generation_start) * 1000, model=settings.assistant_model)
        if generated.input_tokens is not None:
            record("input_tokens", count=generated.input_tokens)
        if generated.output_tokens is not None:
            record("output_tokens", count=generated.output_tokens)
        answer = generated.text
        validate_extractive(answer, sources)
        if PERSONAL.search(answer) or SECRET.search(answer):
            raise ValueError("Private generated output")
        logger.info("assistant_generation provider=%s prompt=%s latency_ms=%.2f input_tokens=%s output_tokens=%s", provider_name, VERSION,
                    (time.perf_counter() - generation_start) * 1000, generated.input_tokens, generated.output_tokens)
        result.update(answer=answer, mode="generated")
        result["notice"] = "AI selected verbatim source quotations. Review the full excerpts for context."
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
        record("provider_failure")
        logger.info("assistant_provider_failure provider=%s", provider_name)
        # Never expose provider payloads, keys or prompts in logs/errors.
        result["notice"] = "AI generation was unavailable or could not be validated. Showing source excerpts."
    return result


async def respond(question, **kwargs):
    started = time.perf_counter()
    try:
        result = await _respond(question, **kwargs)
        record(result["mode"])
        return result
    except Exception:
        record("retrieval_failure")
        raise
    finally:
        record("total", duration_ms=(time.perf_counter() - started) * 1000)
