"""Bounded index repair over stored text only; never reparses or downloads files."""
from sqlalchemy import select

from app.db.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeJob, KnowledgeVersion
from app.services.rag.store import identifier


def reindex(db, version_id, provider=None, provider_factory=None):
    version = db.get(KnowledgeVersion, version_id)
    if version is None:
        raise ValueError("Version unavailable")
    document = db.scalar(select(KnowledgeDocument).where(
        KnowledgeDocument.id == version.document_id).with_for_update())
    if document is None or document.deleted:
        raise ValueError("Only available pending or approved versions can be reindexed")
    db.refresh(version, with_for_update=True)
    if version.status not in {"pending", "approved"}:
        raise ValueError("Only available pending or approved versions can be reindexed")
    job = db.scalar(select(KnowledgeJob).where(KnowledgeJob.version_id == version_id).with_for_update())
    if job is None:
        job = KnowledgeJob(id=identifier(), version_id=version_id, status="pending", chunk_count=0)
        db.add(job)
        db.flush()
    chunks = list(db.scalars(select(KnowledgeChunk).where(
        KnowledgeChunk.version_id == version_id).order_by(KnowledgeChunk.ordinal).limit(2001)))
    job.chunk_count = min(len(chunks), 2000)
    if not chunks or len(chunks) > 2000 or any(not chunk.text.strip() for chunk in chunks):
        job.status, job.detail = "failed", "Stored chunks missing, empty or over capacity; submit a reviewed new version when uploads are approved"
        db.flush()
        return {"status": "failed", "detail": job.detail, "chunk_count": job.chunk_count}
    try:
        # Preserve the previous index on model failures; callers may retry the same
        # version after provisioning an approved local snapshot. No partial vectors.
        with db.begin_nested():
            added = 0
            if provider_factory is not None:
                provider = provider_factory()
            if provider is not None:
                from app.services.rag.vectors import index_chunks
                added = index_chunks(db, chunks, provider)
    except (ValueError, RuntimeError, OSError, ImportError):
        job.status, job.detail = "failed", "Local embedding index failed; check the approved model and chunk limits, then retry"
        db.flush()
        return {"status": "failed", "detail": job.detail, "chunk_count": len(chunks)}
    job.status = "indexed"
    job.detail = "Stored chunks checked; lexical retrieval ready" if provider is None else "Stored chunks checked; local embeddings indexed"
    db.flush()
    return {"status": "indexed", "detail": job.detail, "chunk_count": len(chunks), "embeddings_added": added}
