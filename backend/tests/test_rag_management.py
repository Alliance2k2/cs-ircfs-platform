import pytest
from sqlalchemy import delete, select

from app.core.security import Principal
from app.db.knowledge import KnowledgeChunk, KnowledgeEmbedding, KnowledgeJob
from app.db.models import UserRole
from app.services.rag.management import reindex
from app.services.rag.store import approve, authorized_sources, ingest

ADMIN = Principal(name="fixture", role=UserRole.administrator, account_id=1)


class Encoder:
    model_id = "synthetic-repair@1"

    def encode(self, texts):
        return [[1, 0] for _ in texts]


def source(db):
    version, _ = ingest(db, filename="x.txt", data=b"Synthetic repair procedure. Review the pump checklist.", title="Fixture")
    return version


def test_lexical_check_is_repeatable_and_does_not_approve(db):
    version = source(db)
    for _ in range(2):
        result = reindex(db, version.id)
        assert result["status"] == "indexed" and result["embeddings_added"] == 0
    assert version.status == "pending" and authorized_sources(db, ADMIN) == []
    assert not list(db.scalars(select(KnowledgeEmbedding)))


def test_failed_model_job_can_recover_without_partial_or_duplicate_embeddings(db):
    version = source(db)
    approve(db, version.id, ADMIN, "synthetic review")

    def unavailable():
        raise OSError("secret model filesystem details")

    failed = reindex(db, version.id, provider_factory=unavailable)
    assert failed["status"] == "failed" and "secret" not in failed["detail"]
    assert db.scalar(select(KnowledgeJob)).status == "failed"
    assert authorized_sources(db, ADMIN)  # Previous approved text remains usable.
    recovered = reindex(db, version.id, Encoder())
    assert recovered["embeddings_added"] == 1
    assert reindex(db, version.id, Encoder())["embeddings_added"] == 0
    assert db.scalar(select(KnowledgeJob)).status == "indexed"
    assert len(list(db.scalars(select(KnowledgeEmbedding)))) == 1


def test_missing_stored_text_is_reported_instead_of_claiming_success(db):
    version = source(db)
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.version_id == version.id))
    assert reindex(db, version.id)["status"] == "failed"
    with pytest.raises(ValueError, match="unavailable"):
        reindex(db, "missing")
