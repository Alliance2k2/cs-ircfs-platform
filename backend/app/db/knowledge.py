"""Knowledge-only tables, deliberately separate from participant/report relations."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    classification: Mapped[str] = mapped_column(String(24))
    language: Mapped[str] = mapped_column(String(2))
    roles: Mapped[list] = mapped_column(JSON)
    sector_ids: Mapped[list] = mapped_column(JSON)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (CheckConstraint("classification IN ('engineering', 'institutional', 'demonstration')", name="ck_knowledge_classification"),)


class KnowledgeVersion(Base):
    __tablename__ = "knowledge_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"), index=True)
    digest: Mapped[str] = mapped_column(String(64))
    revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    approval_reference: Mapped[str] = mapped_column(String(200), default="")
    approved_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    __table_args__ = (UniqueConstraint("document_id", "digest", name="uq_knowledge_version_digest"),
                     UniqueConstraint("document_id", "revision", name="uq_knowledge_version_number"),
                     CheckConstraint("status IN ('pending', 'approved', 'superseded', 'rejected')", name="ck_knowledge_version_status"))


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("knowledge_versions.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    page: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("version_id", "ordinal", name="uq_knowledge_chunk_ordinal"),)


class KnowledgeEmbedding(Base):
    __tablename__ = "knowledge_embeddings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("knowledge_chunks.id"), index=True)
    model: Mapped[str] = mapped_column(String(200))
    dimensions: Mapped[int] = mapped_column(Integer)
    vector: Mapped[list] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("chunk_id", "model", name="uq_knowledge_embedding_model"),)


class KnowledgeJob(Base):
    __tablename__ = "knowledge_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("knowledge_versions.id"), index=True)
    status: Mapped[str] = mapped_column(String(16))
    chunk_count: Mapped[int] = mapped_column(Integer)
    detail: Mapped[str] = mapped_column(String(200), default="")


class KnowledgeEvaluation(Base):
    __tablename__ = "knowledge_evaluations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_hash: Mapped[str] = mapped_column(String(64))
    corpus_hash: Mapped[str] = mapped_column(String(64))
    retriever: Mapped[str] = mapped_column(String(200))
    metrics: Mapped[dict] = mapped_column(JSON)
