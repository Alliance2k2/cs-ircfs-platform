"""Opt-in exact-distance test. Never installs extensions or modifies live data."""
import os
import importlib
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.core.security import Principal
from app.db.knowledge import KnowledgeChunk
from app.db.models import UserRole
from app.services.rag.store import ingest, approve, authorized_sources, remove
from app.services.rag.vectors import index_chunks, search
from sqlalchemy import select


@pytest.mark.skipif(not os.environ.get("RAG_TEST_POSTGRES_URL"), reason="Dedicated PostgreSQL/pgvector test URL not provided")
def test_pgvector_exact_distance_on_dedicated_database():
    engine = create_engine(os.environ["RAG_TEST_POSTGRES_URL"])
    if not engine.url.database or not engine.url.database.endswith("_test"):
        pytest.fail("RAG_TEST_POSTGRES_URL database must end in _test")
    with engine.connect() as conn:
        installed = conn.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')"))
        if not installed:
            pytest.skip("pgvector extension is unavailable in this PostgreSQL installation")
        assert conn.scalar(text("SELECT '[1,0]'::vector <=> '[1,0]'::vector")) == pytest.approx(0)
        assert conn.scalar(text("SELECT '[1,0]'::vector <=> '[0,1]'::vector")) == pytest.approx(1)
    engine.dispose()


@pytest.mark.skipif(not os.environ.get("RAG_TEST_POSTGRES_URL"), reason="Dedicated PostgreSQL/pgvector test URL not provided")
def test_knowledge_migration_acl_vectors_and_deletion_on_postgres():
    engine = create_engine(os.environ["RAG_TEST_POSTGRES_URL"])
    if not engine.url.database or not engine.url.database.endswith("_test"):
        pytest.fail("Dedicated disposable database ending _test required")
    revision = importlib.import_module("migrations.versions.20261117_30_knowledge")
    admin = Principal(name="synthetic", role=UserRole.administrator, account_id=1)
    class SyntheticEncoder:
        model_id = "synthetic-postgres@1"
        def encode(self, texts):
            return [[1.0, 0.0] for _ in texts]
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            has_vector = connection.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector')"))
            schema = "rag_" + uuid4().hex  # generated identifier, never client input
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            with Operations.context(MigrationContext.configure(connection)):
                revision.upgrade()
            db = Session(bind=connection)
            version, _ = ingest(db, filename="synthetic.txt", data=b"Synthetic pump inspection", title="Fixture pump", roles=["administrator"])
            assert authorized_sources(db, admin) == []
            approve(db, version.id, admin, "synthetic PostgreSQL validation")
            sources = authorized_sources(db, admin)
            chunks = list(db.scalars(select(KnowledgeChunk)))
            encoder = SyntheticEncoder()
            assert index_chunks(db, chunks, encoder) == 1
            assert index_chunks(db, chunks, encoder) == 0
            allowed = [source["id"] for source in sources]
            portable = search(db, allowed, [1, 0], encoder.model_id)
            assert portable[0][0] == allowed[0]
            assert portable[0][1] == pytest.approx(1)
            if has_vector:
                vector = search(db, allowed, [1, 0], encoder.model_id, pgvector=True)
                assert vector[0][0] == portable[0][0]
                assert vector[0][1] == pytest.approx(portable[0][1])
                assert search(db, [], [1, 0], encoder.model_id, pgvector=True) == []
            remove(db, version.document_id)
            assert authorized_sources(db, admin) == []
            assert search(db, allowed, [1, 0], encoder.model_id, pgvector=bool(has_vector)) == []
            db.close()
            with Operations.context(MigrationContext.configure(connection)):
                revision.downgrade()
                revision.upgrade()
        finally:
            transaction.rollback()  # schema and all synthetic content disappear
    engine.dispose()
