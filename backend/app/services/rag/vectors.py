"""Persistent portable vectors; optional exact pgvector distance, no extension DDL."""
import json

from sqlalchemy import bindparam, select, text

from app.db.knowledge import KnowledgeEmbedding
from app.services.rag.embeddings import cosine, normalize
from app.services.rag.store import identifier


def index_chunks(db, chunks, provider):
    existing = {row.chunk_id: row for row in db.scalars(select(KnowledgeEmbedding).where(
        KnowledgeEmbedding.chunk_id.in_([chunk.id for chunk in chunks]), KnowledgeEmbedding.model == provider.model_id))}
    missing = [chunk for chunk in chunks if chunk.id not in existing]
    if missing:
        vectors = provider.encode([chunk.text for chunk in missing])
        if len(vectors) != len(missing):
            raise ValueError("Incorrect embedding count")
        normalized = [normalize(vector) for vector in vectors]
        dimensions = {len(row) for row in normalized} | {row.dimensions for row in existing.values()}
        if len(dimensions) != 1:
            raise ValueError("Inconsistent model dimensions; use a new immutable model revision")
        for chunk, vector in zip(missing, normalized):
            db.add(KnowledgeEmbedding(id=identifier(), chunk_id=chunk.id, model=provider.model_id, dimensions=len(vector), vector=vector))
    db.flush()
    return len(missing)


def search(db, allowed_chunk_ids, query, model, top_k=3, threshold=.4, pgvector=False):
    """Caller MUST supply only preauthorized approved chunk IDs. No raw question."""
    if not allowed_chunk_ids:
        return []
    if not 1 <= top_k <= 20 or len(allowed_chunk_ids) > 2000 or not -1 <= threshold <= 1:
        raise ValueError("Invalid vector search bounds")
    query = normalize(query)
    if pgvector:
        if db.bind.dialect.name != "postgresql":
            raise ValueError("pgvector requires PostgreSQL")
        if not db.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='vector')")):
            raise ValueError("pgvector extension not installed; operator action required")
        # Portable JSON is the source of truth. Cast only authorized, same-model,
        # same-dimension vectors in a MATERIALIZED CTE before computing distance.
        # Exact search is intentional for the bounded pilot; no HNSW claim.
        statement = text("WITH permitted AS MATERIALIZED (SELECT chunk_id, vector FROM knowledge_embeddings "
                         "WHERE chunk_id IN :ids AND model=:model AND dimensions=:dimensions) "
                         "SELECT chunk_id, 1 - (CAST(CAST(vector AS text) AS vector) <=> CAST(:query AS vector)) AS score "
                         "FROM permitted ORDER BY score DESC, chunk_id LIMIT :limit").bindparams(bindparam("ids", expanding=True))
        rows = db.execute(statement, {"ids": allowed_chunk_ids, "model": model, "dimensions": len(query), "query": json.dumps(query), "limit": top_k})
        return [(row.chunk_id, float(row.score)) for row in rows if row.score >= threshold]
    vectors = db.scalars(select(KnowledgeEmbedding).where(KnowledgeEmbedding.chunk_id.in_(allowed_chunk_ids),
        KnowledgeEmbedding.model == model, KnowledgeEmbedding.dimensions == len(query)))
    ranked = [(row.chunk_id, cosine(query, row.vector)) for row in vectors]
    return sorted([(key, score) for key, score in ranked if score >= threshold], key=lambda row: (-row[1], row[0]))[:top_k]
